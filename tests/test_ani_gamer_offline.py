from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
import trusted_ui.ani_gamer_offline as offline
from trusted_ui.ani_gamer_offline import (
    ALLOWED_LOCAL_MEDIA_SUFFIXES,
    LocalMediaPlaybackCapability,
    OfflineImportCancelled,
    classify_local_media_playback_selection,
    classify_local_media_player_error,
    create_episode_archive,
    import_local_media,
    import_local_subtitles,
    local_media_playback_status_key,
    local_media_runtime_support,
    safe_local_media_display_name,
    validate_local_media_selection,
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
    assert document["cover_sha256"]
    assert document["manifest_schema"] == 1
    assert document["files"][0]["role"] == "cover"
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
    assert any(entry["role"] == "media" for entry in preserved["files"])

    verified = verify_episode_archive(archive.root)
    assert verified.valid
    assert verified.media_state == "ok"
    assert verified.actual_sha256 == preserved["local_media"]["sha256"]
    assert verified.cover_state == "ok"


def test_offline_archive_verification_reports_tampered_cover(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path, SERIES, EPISODE, cover_png=PNG)
    assert archive.cover is not None
    archive.cover.write_bytes(PNG + b"changed")

    verified = verify_episode_archive(archive.root)
    assert not verified.valid
    assert verified.cover_state == "hash-mismatch"


def test_offline_archive_rejects_tampered_file_manifest(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path, SERIES, EPISODE, cover_png=PNG)
    document = json.loads(archive.metadata.read_text(encoding="utf-8"))
    document["files"][0]["path"] = "../outside.png"
    archive.metadata.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="file manifest"):
        verify_episode_archive(archive.root)


def test_offline_archive_supports_bounded_safe_name_components(tmp_path: Path) -> None:
    archive = create_episode_archive(
        tmp_path,
        SERIES,
        EPISODE,
        name_prefix="Work/2026",
        name_suffix="  batch  ",
    )
    document = json.loads(archive.metadata.read_text(encoding="utf-8"))
    assert document["naming"] == {"prefix": "Work_2026", "suffix": "batch"}
    assert "Work_2026" in archive.root.name
    assert "batch" in archive.root.name


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


def test_player_media_selection_rejects_links_and_returns_resolved_files(
    tmp_path: Path,
) -> None:
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"local player media")

    selected = validate_local_media_selection([media])
    assert selected == (media.resolve(),)

    with pytest.raises(ValueError, match="missing or unsafe"):
        validate_local_media_selection([tmp_path / "missing.mp4"])
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not media", encoding="utf-8")
    with pytest.raises(ValueError, match="type or size"):
        validate_local_media_selection([unsupported])

    symlink = tmp_path / "linked.mp4"
    try:
        symlink.symlink_to(media)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="missing or unsafe"):
        validate_local_media_selection([symlink])


def test_local_player_runtime_support_is_separate_from_archive_allowlist(
    tmp_path: Path,
) -> None:
    support = local_media_runtime_support(
        {"AVI", "Matroska", "MPEG4", "Ogg", "Mpeg4Audio", "MP3", "FLAC", "Wave"},
        {"AAC", "FLAC", "MP3", "Wave"},
    )

    assert {".flac", ".mp3"} <= support.supported
    assert ".mp4" in support.unknown
    assert ".webm" in support.unsupported
    assert ".opus" in support.unsupported
    assert ".ogg" in support.unknown
    assert {".mpeg", ".mpg", ".ts"} <= support.unknown
    assert support.supported | support.unsupported | support.unknown == (
        ALLOWED_LOCAL_MEDIA_SUFFIXES
    )
    assert not (support.supported & support.unsupported)
    assert not (support.supported & support.unknown)
    assert not (support.unsupported & support.unknown)

    webm = tmp_path / "owned.webm"
    webm.write_bytes(b"user-owned media")
    queue = validate_local_media_selection([webm])
    assert queue == (webm.resolve(),)
    assert (
        classify_local_media_playback_selection(queue, support)
        is LocalMediaPlaybackCapability.UNSUPPORTED
    )


def test_local_player_runtime_support_allows_codec_specific_opus_only_when_known() -> None:
    unsupported = local_media_runtime_support({"Ogg"}, set())
    supported = local_media_runtime_support({"Ogg"}, {"Opus"})

    assert ".ogg" in unsupported.unknown
    assert ".ogg" in supported.unknown
    assert ".opus" in unsupported.unsupported
    assert ".opus" in supported.supported


def test_local_player_queue_uses_the_strictest_runtime_capability(tmp_path: Path) -> None:
    support = local_media_runtime_support(
        {"FLAC", "MPEG4"},
        {"FLAC", "AAC"},
    )
    supported = tmp_path / "supported.flac"
    unknown = tmp_path / "unknown.mp4"
    unsupported = tmp_path / "unsupported.webm"
    for path in (supported, unknown, unsupported):
        path.write_bytes(b"user-owned media")

    assert (
        classify_local_media_playback_selection((supported,), support)
        is LocalMediaPlaybackCapability.SUPPORTED
    )
    assert (
        classify_local_media_playback_selection((supported, unknown), support)
        is LocalMediaPlaybackCapability.UNKNOWN
    )
    assert (
        classify_local_media_playback_selection(
            (supported, unknown, unsupported),
            support,
        )
        is LocalMediaPlaybackCapability.UNSUPPORTED
    )


@pytest.mark.parametrize(
    "suffix",
    (".avi", ".m4a", ".m4v", ".mkv", ".mov", ".mp4", ".ogg", ".wav", ".webm"),
)
def test_variable_codec_containers_remain_unknown_when_runtime_supports_them(
    suffix: str,
) -> None:
    support = local_media_runtime_support(
        {
            "AVI",
            "Mpeg4Audio",
            "MPEG4",
            "Matroska",
            "QuickTime",
            "Ogg",
            "Wave",
            "WebM",
        },
        {"AAC", "FLAC", "MP3", "Opus", "Wave"},
    )

    assert suffix in support.unknown


@pytest.mark.parametrize(
    ("capability", "state_name", "expected"),
    (
        (
            LocalMediaPlaybackCapability.SUPPORTED,
            "LoadingState",
            "offline_media_loading",
        ),
        (
            LocalMediaPlaybackCapability.UNKNOWN,
            "LoadingState",
            "offline_media_playing_unknown",
        ),
        (
            LocalMediaPlaybackCapability.SUPPORTED,
            "PlayingState",
            "offline_media_playing",
        ),
        (
            LocalMediaPlaybackCapability.UNKNOWN,
            "PlayingState",
            "offline_media_playing",
        ),
    ),
)
def test_local_player_status_confirms_playback_only_after_playing_state(
    capability: LocalMediaPlaybackCapability,
    state_name: str,
    expected: str,
) -> None:
    assert local_media_playback_status_key(capability, state_name) == expected


def test_local_player_display_name_is_bounded_plain_text_without_bidi_controls() -> None:
    value = Path("folder") / "<b>episode<b>\n\u202egnp.exe.mp4"

    assert safe_local_media_display_name(value) == "<b>episode<b>  gnp.exe.mp4"
    assert safe_local_media_display_name(value, limit=10) == "<b>episode"
    assert safe_local_media_display_name(object()) == "local-media"
    with pytest.raises(ValueError, match="positive"):
        safe_local_media_display_name(value, limit=0)


@pytest.mark.parametrize(
    ("error_name", "invalid_media", "expected"),
    (
        ("FormatError", False, "unsupported-codec-or-corrupt-media"),
        ("ResourceError", False, "missing-or-unreadable-media"),
        ("AccessDeniedError", False, "media-access-denied"),
        ("NetworkError", False, "unexpected-local-backend-network-error"),
        ("NoError", True, "invalid-media"),
        ("NoError", False, "playback-failed"),
        ("UnknownFutureError", False, "playback-failed"),
    ),
)
def test_local_player_error_classification_is_stable(
    error_name: str,
    invalid_media: bool,
    expected: str,
) -> None:
    assert (
        classify_local_media_player_error(
            error_name,
            invalid_media=invalid_media,
        )
        == expected
    )


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


def test_local_subtitle_import_is_hashed_and_verified_with_media(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"owned video")
    imported_media = import_local_media(archive.root, media)
    assert imported_media.local_media is not None

    traditional = tmp_path / "zh-TW.ass"
    traditional.write_text("[Script Info]\nTitle: test\n", encoding="utf-8")
    english = tmp_path / "en.srt"
    english.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    imported = import_local_subtitles(archive.root, [traditional, english])
    document = json.loads(archive.metadata.read_text(encoding="utf-8"))
    assert len(imported.local_subtitles) == 2
    assert all(path.parent.name == "subtitles" for path in imported.local_subtitles)
    assert all(path.is_file() for path in imported.local_subtitles)
    assert len(document["local_subtitles"]) == 2
    assert all(entry["sha256"] for entry in document["local_subtitles"])

    verified = verify_episode_archive(archive.root)
    assert verified.valid
    assert verified.media_state == "ok"
    assert verified.subtitle_state == "ok"
    assert len(verified.subtitle_paths) == 2


def test_local_subtitle_verification_reports_tampering(tmp_path: Path) -> None:
    archive = create_episode_archive(tmp_path / "output", SERIES, EPISODE)
    subtitle = tmp_path / "zh-TW.vtt"
    subtitle.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\n字幕\n", encoding="utf-8")
    imported = import_local_subtitles(archive.root, [subtitle])
    payload = imported.local_subtitles[0].read_bytes()
    imported.local_subtitles[0].write_bytes(payload[:-1] + b"X")

    verified = verify_episode_archive(archive.root)
    assert not verified.valid
    assert verified.media_state == "not-linked"
    assert verified.subtitle_state == "hash-mismatch"
