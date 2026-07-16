from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
import trusted_ui.ani_gamer_offline as offline
from trusted_ui.ani_gamer_offline import (
    OfflineImportCancelled,
    create_episode_archive,
    import_local_media,
    verify_episode_archive,
)


def item(video_id: str, url: str, title: str) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url,
        title,
        "",
        None,
        "zh-TW",
        "anime",
        "https://p2.bahamut.com.tw/B/2KU/00/cover.jpg",
    )


SERIES = item(
    "114096",
    "https://ani.gamer.com.tw/animeRef.php?sn=114096",
    "測試作品：第一季",
)
EPISODE = item(
    "49944",
    "https://ani.gamer.com.tw/animeVideo.php?sn=49944",
    "第 1 集 / 開始",
)
PNG = b"\x89PNG\r\n\x1a\n" + b"safe-cover"


def test_selected_episode_archive_is_atomic_and_preserves_local_media(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path, SERIES, EPISODE, cover_png=PNG)

    assert archive.root.is_relative_to(tmp_path)
    assert archive.cover is not None
    assert archive.cover.read_bytes() == PNG
    document = json.loads(archive.metadata.read_text(encoding="utf-8"))
    assert document["kind"] == "ani-gamer-selected-episode"
    assert document["series"]["official_url"] == SERIES.url
    assert document["episode"]["official_url"] == EPISODE.url
    assert document["boundary"] == "public-metadata-cover-and-user-local-media-only"
    assert document["local_media"] is None
    assert not tuple(archive.root.glob("*.tmp"))

    local = tmp_path / "owned.mp4"
    local.write_bytes(b"owned-media")
    imported = import_local_media(archive.root, local)
    refreshed = create_episode_archive(tmp_path, SERIES, EPISODE)
    preserved = json.loads(refreshed.metadata.read_text(encoding="utf-8"))

    assert imported.local_media is not None
    assert imported.local_media.read_bytes() == b"owned-media"
    assert preserved["local_media"]["path"].startswith("media/")
    assert preserved["local_media"]["sha256"]

    verified = verify_episode_archive(archive.root)
    assert verified.valid
    assert verified.media_state == "ok"
    assert verified.actual_sha256 == preserved["local_media"]["sha256"]


def test_offline_archive_verification_reports_missing_and_tampered_media(
    tmp_path: Path,
) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    assert verify_episode_archive(archive.root).media_state == "not-linked"
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"original media")
    imported = import_local_media(archive.root, source)
    assert imported.local_media is not None

    imported.local_media.write_bytes(b"changed")
    mismatch = verify_episode_archive(archive.root)
    assert not mismatch.valid
    assert mismatch.media_state == "size-mismatch"

    imported.local_media.unlink()
    missing = verify_episode_archive(archive.root)
    assert not missing.valid
    assert missing.media_state == "missing"


def test_offline_archive_verification_can_be_cancelled(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    source = tmp_path / "episode.mkv"
    source.write_bytes(b"media")
    import_local_media(archive.root, source)

    with pytest.raises(offline.OfflineImportCancelled, match="cancelled"):
        verify_episode_archive(archive.root, cancelled=lambda: True)


def test_offline_archive_rejects_wrong_site_and_invalid_cover(tmp_path: Path) -> None:
    wrong = item("x", "https://www.youtube.com/watch?v=example", "wrong")

    with pytest.raises(ValueError, match="series URL"):
        create_episode_archive(tmp_path, wrong, EPISODE)
    with pytest.raises(ValueError, match="cover PNG"):
        create_episode_archive(tmp_path, SERIES, EPISODE, cover_png=b"not-png")


def test_local_media_import_rejects_links_types_limits_and_cleans_cancel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    unsupported = tmp_path / "script.exe"
    unsupported.write_bytes(b"unsafe")

    with pytest.raises(ValueError, match="type or size"):
        import_local_media(archive.root, unsupported)

    local = tmp_path / "owned.mkv"
    local.write_bytes(b"chunk")
    monkeypatch.setattr(offline, "MAX_LOCAL_MEDIA_BYTES", 1)
    with pytest.raises(ValueError, match="type or size"):
        import_local_media(archive.root, local)
    monkeypatch.setattr(offline, "MAX_LOCAL_MEDIA_BYTES", 64 * 1024**3)

    with pytest.raises(OfflineImportCancelled):
        import_local_media(archive.root, local, cancelled=lambda: True)
    assert not tuple(archive.root.rglob("*.part"))


def test_local_media_import_never_overwrites_existing_media(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    local = tmp_path / "owned.mp4"
    local.write_bytes(b"one")

    first = import_local_media(archive.root, local)
    local.write_bytes(b"two")
    second = import_local_media(archive.root, local)

    assert first.local_media is not None
    assert second.local_media is not None
    assert first.local_media != second.local_media
    assert first.local_media.read_bytes() == b"one"
    assert second.local_media.read_bytes() == b"two"
