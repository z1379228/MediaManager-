from __future__ import annotations

import os
from types import SimpleNamespace
from threading import Event
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget

from contracts.discovery_v1 import DiscoveryItemV1
from core.bootstrap.bootstrap import Bootstrap
from core.storage.paths import AppPaths
from trusted_ui.library_panel import (
    apply_musicbrainz_metadata,
    create_library_panel,
    musicbrainz_tags,
)


def test_musicbrainz_tag_replacement_preserves_unrelated_local_tags() -> None:
    recording_id = "026FA041-3917-4C73-9079-ED16E36F20F8"

    assert musicbrainz_tags(
        ("focus", "musicbrainz:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "BGM"),
        recording_id,
    ) == (
        "focus",
        "BGM",
        "musicbrainz:026fa041-3917-4c73-9079-ed16e36f20f8",
    )

    for invalid in ("", "not-an-id", "a" * 36):
        with pytest.raises(ValueError):
            musicbrainz_tags((), invalid)


def test_musicbrainz_metadata_updates_only_local_database(
    tmp_path, monkeypatch
) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    media_root = tmp_path / "music"
    media_root.mkdir()
    source = media_root / "song.flac"
    original = b"local-media-bytes"
    source.write_bytes(original)
    item = context.library.scan(media_root)[0]
    context.library.update_metadata(
        item.item_id,
        title="Local title",
        artist="Local artist",
        tags=("focus",),
    )
    candidate = DiscoveryItemV1.from_dict(
        {
            "video_id": "026fa041-3917-4c73-9079-ed16e36f20f8",
            "url": (
                "https://musicbrainz.org/recording/"
                "026fa041-3917-4c73-9079-ed16e36f20f8"
            ),
            "title": "Matched title",
            "artist": "Matched artist",
            "duration": 178,
            "language": "",
            "category": "music",
            "thumbnail_url": "",
        }
    )
    try:
        updated = apply_musicbrainz_metadata(
            context.library,
            item.item_id,
            candidate,
        )

        assert updated.title == "Matched title"
        assert updated.artist == "Matched artist"
        assert updated.tags == (
            "focus",
            "musicbrainz:026fa041-3917-4c73-9079-ed16e36f20f8",
        )
        assert source.read_bytes() == original
        assert source.name == "song.flac"
    finally:
        context.lifecycle.shutdown()


def test_library_panel_is_clean_and_uses_persistent_service(
    tmp_path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    panel = create_library_panel(context)

    buttons = {button.text(): button for button in panel.findChildren(QPushButton)}
    assert "選擇媒體資料夾" in buttons
    assert "管理" in buttons
    assert len(panel.findChildren(QTableWidget)) == 1
    assert buttons["管理"].menu() is not None
    assert "完整確認重複檔案…" in {
        action.text() for action in buttons["管理"].menu().actions()
    }
    assert "從 MusicBrainz 查詢中繼資料…" in {
        action.text() for action in buttons["管理"].menu().actions()
    }

    panel.shutdown()
    panel.deleteLater()
    app.processEvents()
    context.lifecycle.shutdown()


def test_duplicate_verification_runs_off_gui_thread_and_reports_progress(
    tmp_path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    started = Event()
    release = Event()

    def verify(*, cancel_event, progress):
        started.set()
        progress(1, 2)
        release.wait(timeout=2)
        assert not cancel_event.is_set()
        progress(2, 2)
        return ()

    monkeypatch.setattr(context.library, "duplicate_groups", verify)
    panel = create_library_panel(context)
    try:
        started_at = time.monotonic()
        panel.duplicates_action.trigger()
        app.processEvents()

        assert started.wait(timeout=1)
        assert time.monotonic() - started_at < 0.5
        assert panel.duplicate_card.isVisibleTo(panel)
        assert not panel.duplicates_action.isEnabled()

        release.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not panel.duplicates_action.isEnabled():
            app.processEvents()
            time.sleep(0.01)

        assert panel.duplicates_action.isEnabled()
        assert "沒有內容相同" in panel.duplicate_status.text()
    finally:
        release.set()
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_musicbrainz_lookup_runs_off_gui_thread_and_can_stop_waiting(
    tmp_path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    started = Event()
    release = Event()

    def search_metadata(*_args, **_kwargs):
        started.set()
        release.wait(timeout=2)
        return ()

    monkeypatch.setattr(context.discovery, "search", search_metadata)
    panel = create_library_panel(context)
    try:
        started_at = time.monotonic()
        panel.start_musicbrainz_lookup(
            SimpleNamespace(item_id="local-item"),
            "Song Artist",
        )
        app.processEvents()

        assert started.wait(timeout=1)
        assert time.monotonic() - started_at < 0.5
        assert panel.musicbrainz_card.isVisibleTo(panel)
        assert not panel.musicbrainz_action.isEnabled()

        panel.cancel_musicbrainz.click()
        app.processEvents()
        assert "正在停止等待" in panel.musicbrainz_status.text()

        release.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not panel.musicbrainz_action.isEnabled():
            app.processEvents()
            time.sleep(0.01)

        assert panel.musicbrainz_action.isEnabled()
        assert "結果不會套用" in panel.musicbrainz_status.text()
    finally:
        release.set()
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
