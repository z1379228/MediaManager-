from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from threading import Event

import pytest

from core.library import ArtworkCache, DuplicateScanCancelled, LibraryService
from core.media_library import scan_media


@pytest.fixture
def library(tmp_path: Path):
    service = LibraryService(tmp_path / "data" / "library.sqlite3", tmp_path / "art")
    yield service
    service.close()


def test_scan_is_bounded_and_does_not_follow_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    for index in range(4):
        (root / f"{index}.mp3").write_bytes(str(index).encode())
    assert len(scan_media(root, limit=2)) == 2
    with pytest.raises(ValueError):
        scan_media(root, limit=0)

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden.mp3").write_bytes(b"hidden")
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this Windows account")
    assert "hidden.mp3" not in {item.name for item in scan_media(root)}


def test_existing_library_schema_adds_full_hash_cache_column(tmp_path: Path) -> None:
    database = tmp_path / "data" / "library.sqlite3"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE items (
                item_id TEXT PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                media_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified REAL NOT NULL,
                available INTEGER NOT NULL DEFAULT 1,
                fingerprint TEXT,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                play_count INTEGER NOT NULL DEFAULT 0,
                last_played REAL,
                artwork_path TEXT
            )
            """
        )

    service = LibraryService(database, tmp_path / "art")
    try:
        columns = {
            row[1]
            for row in service._connection.execute("PRAGMA table_info(items)")
        }
        assert "content_sha256" in columns
    finally:
        service.close()


def test_library_preserves_metadata_when_file_becomes_unavailable(
    library: LibraryService, tmp_path: Path
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    song = root / "song.flac"
    song.write_bytes(b"audio")
    item = library.scan(root)[0]
    library.update_metadata(item.item_id, title="Local title", artist="Artist", tags=("work", "BGM"))
    library.record_play(item.item_id, played_at=123.0)

    song.unlink()
    assert library.scan(root) == ()
    retained = library.get(item.item_id)
    assert not retained.available
    assert retained.title == "Local title"
    assert retained.artist == "Artist"
    assert retained.tags == ("work", "BGM")
    assert retained.play_count == 1
    assert retained.last_played == 123.0


def test_unchanged_rescan_avoids_per_item_database_writes(
    library: LibraryService,
    tmp_path: Path,
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    first = root / "first.mp3"
    second = root / "second.flac"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    library.scan(root)
    statements: list[str] = []
    library._connection.set_trace_callback(statements.append)

    rescanned = library.scan(root)

    library._connection.set_trace_callback(None)
    assert {item.name for item in rescanned} == {"first.mp3", "second.flac"}
    item_writes = tuple(
        statement
        for statement in statements
        if statement.startswith(("INSERT INTO items", "UPDATE items"))
    )
    assert item_writes == ()


def test_duplicate_review_confirms_partial_candidates_with_full_sha256(
    library: LibraryService, tmp_path: Path
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    content = b"same-data" * 100
    (root / "a.mp3").write_bytes(content)
    (root / "b.mp3").write_bytes(content)
    (root / "different.mp3").write_bytes(b"different" + content[:-9])
    library.scan(root)
    groups = library.duplicate_groups()
    assert len(groups) == 1
    assert {item.name for item in groups[0].items} == {"a.mp3", "b.mp3"}
    assert groups[0].sha256 == hashlib.sha256(content).hexdigest()
    assert all(path.exists() for path in (root / "a.mp3", root / "b.mp3"))


def test_full_hash_rejects_same_size_and_same_edge_false_positive(
    library: LibraryService,
    tmp_path: Path,
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    edge = b"e" * (1024 * 1024)
    first = edge + b"a" * (1024 * 1024) + edge
    second = edge + b"b" * (1024 * 1024) + edge
    (root / "a.mp3").write_bytes(first)
    (root / "b.mp3").write_bytes(first)
    (root / "partial-collision.mp3").write_bytes(second)
    library.scan(root)

    groups = library.duplicate_groups()

    assert len(groups) == 1
    assert {item.name for item in groups[0].items} == {"a.mp3", "b.mp3"}


def test_duplicate_review_invalidates_hashes_changed_since_last_scan(
    library: LibraryService,
    tmp_path: Path,
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    content = b"same-data" * 100
    first = root / "a.mp3"
    second = root / "b.mp3"
    first.write_bytes(content)
    second.write_bytes(content)
    library.scan(root)
    assert len(library.duplicate_groups()) == 1

    # Keep the indexed size but change the content and timestamp without asking
    # the user to run another library scan first.
    second.write_bytes(b"other-dat" * 100)
    original = library.search()[1]
    second.touch()
    if second.stat().st_mtime == original.modified:
        second.touch()
        stat = second.stat()
        second_time = stat.st_mtime + 1.0
        os.utime(second, (second_time, second_time))

    assert library.duplicate_groups() == ()
    refreshed = next(item for item in library.search() if item.path == second)
    assert refreshed.modified == second.stat().st_mtime
    assert refreshed.fingerprint is not None
    assert refreshed.content_sha256 is None


def test_duplicate_confirmation_is_cancellable(
    library: LibraryService,
    tmp_path: Path,
) -> None:
    root = tmp_path / "music"
    root.mkdir()
    content = b"same" * (1024 * 1024)
    (root / "a.mp3").write_bytes(content)
    (root / "b.mp3").write_bytes(content)
    library.scan(root)
    cancel = Event()
    progress: list[tuple[int, int]] = []

    def observe(completed: int, total: int) -> None:
        progress.append((completed, total))
        cancel.set()

    with pytest.raises(DuplicateScanCancelled):
        library.duplicate_groups(cancel_event=cancel, progress=observe)

    assert progress


def test_static_and_smart_playlists_round_trip(
    library: LibraryService, tmp_path: Path
) -> None:
    root = tmp_path / "media"
    root.mkdir()
    (root / "one.mp3").write_bytes(b"one")
    (root / "two.mp4").write_bytes(b"two")
    items = library.scan(root)
    audio = next(item for item in items if item.media_type == "音訊")
    library.update_metadata(audio.item_id, tags=("focus",))

    playlist_id = library.create_playlist("Mix", [item.item_id for item in items])
    exported = library.export_playlist(playlist_id, tmp_path / "mix.json")
    document = json.loads(exported.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    preview = library.preview_playlist_import(exported)
    assert preview.name == "Mix"
    assert not preview.missing
    imported_id = library.apply_playlist_import(preview)
    assert len(library.playlist_items(imported_id)) == 2

    smart_id = library.create_playlist(
        "Focus audio", query={"media_type": "音訊", "tags": ["focus"]}
    )
    assert [item.item_id for item in library.playlist_items(smart_id)] == [audio.item_id]


def test_playlist_import_reports_missing_and_duplicates(
    library: LibraryService, tmp_path: Path
) -> None:
    root = tmp_path / "media"
    root.mkdir()
    existing = root / "one.mp3"
    existing.write_bytes(b"one")
    library.scan(root)
    playlist = tmp_path / "list.m3u8"
    playlist.write_text(
        f"#EXTM3U\n{existing}\n{existing}\n{root / 'missing.mp3'}\n",
        encoding="utf-8",
    )
    preview = library.preview_playlist_import(playlist)
    assert preview.duplicates == (existing.resolve(),)
    assert preview.missing == ((root / "missing.mp3").resolve(),)


def test_move_preview_prevents_overwrite_and_rolls_back_database_failure(
    library: LibraryService, tmp_path: Path
) -> None:
    root = tmp_path / "media"
    root.mkdir()
    source = root / "source.mp3"
    source.write_bytes(b"source")
    item = library.scan(root)[0]
    occupied = root / "occupied.mp3"
    occupied.write_bytes(b"occupied")
    with pytest.raises(FileExistsError):
        library.preview_move(item.item_id, occupied)

    target = root / "renamed.mp3"
    plan = library.preview_move(item.item_id, target)
    library._connection.execute(
        "CREATE TRIGGER fail_move BEFORE UPDATE OF path ON items "
        "BEGIN SELECT RAISE(ABORT, 'test rollback'); END"
    )
    with pytest.raises(Exception, match="test rollback"):
        library.apply_move(plan)
    assert source.exists()
    assert not target.exists()
    assert library.get(item.item_id).path == source.resolve()


def test_artwork_cache_is_bounded_and_rejects_non_images(tmp_path: Path) -> None:
    cache = ArtworkCache(tmp_path / "art", max_bytes=9, max_source_bytes=8)
    first = tmp_path / "first.png"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"12345")
    second.write_bytes(b"67890")
    first_cached = cache.store(first)
    second_cached = cache.store(second)
    assert second_cached.exists()
    assert not first_cached.exists()
    text = tmp_path / "not-image.txt"
    text.write_bytes(b"x")
    with pytest.raises(ValueError):
        cache.store(text)
