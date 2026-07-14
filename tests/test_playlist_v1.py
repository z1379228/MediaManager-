from __future__ import annotations

from pathlib import Path

import pytest

from contracts.playlist_v1 import PlaylistContractError, PlaylistEntryV1
from core.downloads.playlist_batch import build_playlist_requests
from trusted_ui.playlist_dialog import filtered_playlist_entries


def entry(
    entry_id: str = "abc",
    *,
    title: str = "Example Song",
    artist: str = "Example Artist",
    available: bool = True,
) -> PlaylistEntryV1:
    return PlaylistEntryV1(
        entry_id=entry_id,
        url=f"https://www.youtube.com/watch?v={entry_id}" if available else "",
        title=title,
        artist=artist,
        duration=120,
        position=1,
        available=available,
        unavailable_reason="" if available else "private",
    )


def test_playlist_entry_requires_url_only_when_available() -> None:
    assert entry(available=False).unavailable_reason == "private"
    with pytest.raises(ValueError, match="URL"):
        PlaylistEntryV1("abc", "", "Title", "", None, 1, True)


def test_playlist_contract_rejects_coerced_provider_types() -> None:
    raw = {
        "entry_id": "abc",
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "Title",
        "artist": "",
        "duration": 60,
        "position": True,
        "available": True,
        "unavailable_reason": "",
    }
    with pytest.raises(PlaylistContractError, match="state fields"):
        PlaylistEntryV1.from_dict(raw)


def test_playlist_batch_keeps_media_options_and_metadata(tmp_path: Path) -> None:
    requests = build_playlist_requests(
        (entry("one"), entry("two", title="Second")),
        output_dir=tmp_path,
        priority=5,
        format_preset="video-720",
        subtitle_mode="selected",
        subtitle_languages=("zh-TW", "en"),
        timed_comment_mode="ass",
        container_preset="mkv",
    )
    assert [request.source_video_id for request in requests] == ["one", "two"]
    assert all(request.source_category == "playlist" for request in requests)
    assert all(request.format_preset == "video-720" for request in requests)
    assert all(request.subtitle_languages == ("zh-TW", "en") for request in requests)
    assert all(request.timed_comment_mode == "ass" for request in requests)
    assert all(request.container_preset == "mkv" for request in requests)


def test_playlist_batch_rejects_unavailable_or_duplicate_entries(
    tmp_path: Path,
) -> None:
    options = {
        "output_dir": tmp_path,
        "priority": 0,
        "format_preset": "best",
        "subtitle_mode": "none",
        "subtitle_languages": (),
    }
    with pytest.raises(ValueError, match="unavailable"):
        build_playlist_requests((entry(available=False),), **options)
    with pytest.raises(ValueError, match="duplicate"):
        build_playlist_requests((entry(), entry()), **options)


def test_playlist_filter_matches_title_or_artist() -> None:
    entries = (
        entry("one", title="中文歌曲", artist="歌手"),
        entry("two", title="Work Music", artist="Composer"),
    )
    assert filtered_playlist_entries(entries, "中文") == (entries[0],)
    assert filtered_playlist_entries(entries, "composer") == (entries[1],)


def test_playlist_dialog_renders_entries_offscreen(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QDialog

    from trusted_ui.playlist_dialog import show_playlist_dialog

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        QDialog,
        "exec",
        lambda _dialog: QDialog.DialogCode.Rejected,
    )
    assert show_playlist_dialog((entry(), entry("private", available=False))) is None
    app.processEvents()
