from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.playlist_v1 import PlaylistEntryV1
from core.downloads.playlist_transfer import (
    export_playlist_entries,
    import_playlist_entries,
)


def entry(entry_id: str, position: int) -> PlaylistEntryV1:
    return PlaylistEntryV1(
        entry_id=entry_id,
        url=f"https://example.com/watch/{entry_id}",
        title=f"Track {position}",
        artist="Artist",
        duration=180.0,
        position=position,
        available=True,
        thumbnail_url="https://i.ytimg.com/vi/example/mqdefault.jpg",
    )


def test_playlist_ids_round_trip_with_metadata(tmp_path: Path) -> None:
    target = tmp_path / "playlist.json"
    entries = (entry("track-a", 1), entry("track-b", 2))
    assert export_playlist_entries(target, entries) == 2
    assert import_playlist_entries(target) == entries


def test_playlist_import_rejects_unknown_fields_and_duplicate_ids(
    tmp_path: Path,
) -> None:
    target = tmp_path / "playlist.json"
    export_playlist_entries(target, (entry("track-a", 1),))
    raw = json.loads(target.read_text(encoding="utf-8"))
    raw["unknown"] = True
    target.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        import_playlist_entries(target)

    export_playlist_entries(target, (entry("track-a", 1),))
    raw = json.loads(target.read_text(encoding="utf-8"))
    raw["entries"].append(raw["entries"][0])
    target.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        import_playlist_entries(target)


def test_playlist_export_is_atomic_on_invalid_input(tmp_path: Path) -> None:
    target = tmp_path / "playlist.json"
    target.write_text("original", encoding="utf-8")
    duplicate = entry("track-a", 1)
    with pytest.raises(ValueError, match="duplicate"):
        export_playlist_entries(target, (duplicate, duplicate))
    assert target.read_text(encoding="utf-8") == "original"
