from __future__ import annotations

from pathlib import Path
import threading
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.bootstrap.bootstrap import Bootstrap
from core.downloads.models import DownloadRequest, DownloadTask
from core.storage.paths import AppPaths
from trusted_ui.download_panel import create_download_panel
from trusted_ui.main_window import configure_workspace_tabs
from trusted_ui.search_panel import create_search_panel


def test_workspace_tab_bar_disables_native_base_line(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QTabWidget

    app = QApplication.instance() or QApplication([])
    tabs = QTabWidget()
    try:
        configure_workspace_tabs(tabs)
        assert tabs.objectName() == "workspaceTabs"
        assert tabs.documentMode()
        assert not tabs.tabBar().drawBase()
    finally:
        tabs.close()
        tabs.deleteLater()
        app.processEvents()


def test_empty_workspace_actions_are_disabled(tmp_path, monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication, QPushButton

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    search_panel = None
    download_panel = None
    try:
        search_panel = create_search_panel(context)
        search_buttons = {
            button.text(): button for button in search_panel.findChildren(QPushButton)
        }
        for label in (
            "尋找替代影片",
            "隨機相似",
            "加入下載佇列",
            "在瀏覽器開啟",
            "停止試聽",
        ):
            assert not search_buttons[label].isEnabled()
        context.discovery.record_history("search", "作業用 BGM")
        search_panel.populate_history_menu()
        history_labels = [
            action.text() for action in search_panel.history_menu.actions()
        ]
        assert history_labels[0].startswith("1 次搜尋 · 0 次選取")
        assert "作業用 BGM" in history_labels

        download_panel = create_download_panel(context)
        download_panel.timer.stop()
        assert not download_panel.generic_enabled.isChecked()
        assert not download_panel.bilibili_enabled.isChecked()
        assert download_panel.danmaku_xml.isHidden()
        assert download_panel.format_preset.currentData() == "best"
        assert download_panel.subtitle_mode.currentData() == "none"
        assert download_panel.subtitle_languages.isHidden()
        download_panel.subtitle_mode.setCurrentIndex(1)
        app.processEvents()
        assert not download_panel.subtitle_languages.isHidden()
        download_panel.subtitle_mode.setCurrentIndex(0)

        download_panel.bilibili_enabled.setChecked(True)
        download_panel.urls.setPlainText(
            "https://www.bilibili.com/video/BVexample"
        )
        app.processEvents()
        assert not download_panel.danmaku_xml.isHidden()
        download_panel.danmaku_xml.setChecked(True)
        assert not download_panel.danmaku_ass.isHidden()
        assert download_panel.danmaku_mkv.isHidden()
        assert download_panel.selected_media_options() == ("none", ())
        assert download_panel.selected_timed_comment_options() == (
            "source",
            "auto",
        )
        download_panel.danmaku_ass.setChecked(True)
        assert not download_panel.danmaku_mkv.isHidden()
        download_panel.danmaku_mkv.setChecked(True)
        assert download_panel.selected_timed_comment_options() == ("ass", "mkv")
        download_panel.format_preset.setCurrentIndex(
            download_panel.format_preset.findData("audio-m4a")
        )
        app.processEvents()
        assert download_panel.danmaku_ass.isHidden()
        assert download_panel.danmaku_mkv.isHidden()
        assert download_panel.selected_timed_comment_options() == (
            "source",
            "auto",
        )
        download_panel.urls.appendPlainText(
            "https://www.youtube.com/watch?v=example"
        )
        app.processEvents()
        assert download_panel.danmaku_xml.isHidden()
        assert not download_panel.danmaku_xml.isChecked()
        assert download_panel.danmaku_ass.isHidden()
        assert download_panel.danmaku_mkv.isHidden()
        download_buttons = {
            button.text(): button for button in download_panel.findChildren(QPushButton)
        }
        for label in (
            "重試",
            "失敗項目找替代",
            "取消任務",
            "清除已結束紀錄",
        ):
            assert not download_buttons[label].isEnabled()
    finally:
        if search_panel is not None:
            search_panel.close()
            search_panel.deleteLater()
        if download_panel is not None:
            download_panel.close()
            download_panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_video_player_mod_is_opt_in_and_cleans_up_on_disable(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    panel = None
    try:
        panel = create_search_panel(context)
        assert not context.discovery.is_enabled("youtube-player")
        assert panel.video_button.isHidden()

        panel.video_enabled.setChecked(True)
        app.processEvents()
        assert context.discovery.is_enabled("youtube-player")
        assert not panel.video_button.isHidden()

        item = DiscoveryItemV1.from_dict(
            {
                "video_id": "example",
                "url": "https://www.youtube.com/watch?v=example",
                "title": "Example",
                "artist": "Artist",
                "duration": 120,
                "language": "zh-TW",
                "category": "music",
                "thumbnail_url": "",
            }
        )
        panel.show_results((item,), "")
        panel.table.selectRow(0)
        app.processEvents()
        assert panel.video_button.isEnabled()

        player = Mock()
        dialog = Mock()
        provider = Mock()
        preview_path = Path(tmp_path) / "preview.mp4"
        panel.video_player = player
        panel.video_dialog = dialog
        panel.video_preview_provider = provider
        panel.video_preview_path = preview_path
        panel.video_enabled.setChecked(False)
        app.processEvents()

        assert not context.discovery.is_enabled("youtube-player")
        assert panel.video_button.isHidden()
        player.stop.assert_called_once_with()
        player.setSource.assert_called_once()
        dialog.close.assert_called_once_with()
        provider.cleanup_video_preview.assert_called_once_with(preview_path)
    finally:
        if panel is not None:
            panel.close()
            panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_search_panel_blocks_duplicate_async_actions_and_shutdown_cleans_preview(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication([])
    information = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", information)
    context = Bootstrap(portable=True).initialize()
    panel = create_search_panel(context)
    started = threading.Event()
    release = threading.Event()
    calls = 0

    def search(_query, *, provider_ids, limit, content_type, cursor):
        nonlocal calls
        calls += 1
        assert provider_ids is None
        assert cursor == ""
        assert content_type == "music"
        started.set()
        release.wait(2)
        from core.discovery.adapters import FederatedSearchResult

        return FederatedSearchResult((), (), ())

    monkeypatch.setattr(context.discovery, "federated_search", search)
    provider = Mock()
    preview_path = tmp_path / "preview.mp3"
    try:
        panel.query.setText("example")
        panel.search_scope.setCurrentIndex(
            panel.search_scope.findData("music")
        )
        panel.search()
        assert started.wait(2)
        panel.search()
        panel.preview_provider = provider
        panel.preview_path = preview_path

        panel.shutdown()

        assert calls == 1
        information.assert_not_called()
        provider.cleanup_audio_preview.assert_called_once_with(preview_path)
    finally:
        release.set()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_audio_preview_can_stop_and_rejects_late_result(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    from trusted_ui.search_panel import _PreviewResponse

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    panel = create_search_panel(context)
    player = Mock()
    provider = Mock()
    preview_path = Path(tmp_path) / "preview.mp3"
    try:
        panel.audio_player = player
        panel.preview_provider = provider
        panel.preview_path = preview_path
        panel.update_action_state()
        assert panel.stop_preview_button.isEnabled()

        panel.stop_audio_preview()

        player.stop.assert_called_once_with()
        player.setSource.assert_called_once()
        provider.cleanup_audio_preview.assert_called_once_with(preview_path)
        assert panel.preview_provider is None
        assert panel.preview_path is None
        assert not panel.stop_preview_button.isEnabled()
        assert panel.status.text() == "試聽已停止，暫存音訊已清除。"

        panel.busy_action = "preview"
        panel.generation = 7
        panel.update_action_state()
        assert panel.stop_preview_button.isEnabled()
        panel.stop_audio_preview()
        assert panel.generation == 8
        assert panel.busy_action == ""

        late_provider = Mock()
        late_path = Path(tmp_path) / "late.mp3"
        panel.show_audio_preview(
            _PreviewResponse(7, late_provider, late_path), ""
        )
        late_provider.cleanup_audio_preview.assert_called_once_with(late_path)
        player.play.assert_not_called()
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_disabling_generic_provider_cancels_only_its_tasks(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    context.download_providers.set_enabled("generic-ytdlp", True)
    panel = create_download_panel(context)
    panel.timer.stop()
    youtube = DownloadTask(
        "youtube-task",
        DownloadRequest("https://www.youtube.com/watch?v=example", tmp_path),
    )
    generic = DownloadTask(
        "generic-task",
        DownloadRequest("https://vimeo.com/123", tmp_path),
    )
    cancelled: list[str] = []
    monkeypatch.setattr(
        context.download_queue,
        "snapshots",
        lambda: (youtube, generic),
    )
    monkeypatch.setattr(
        context.download_queue,
        "cancel",
        lambda task_id: cancelled.append(task_id) or True,
    )
    try:
        panel.toggle_download_provider("generic-ytdlp", False)

        assert cancelled == ["generic-task"]
        assert context.download_providers.is_enabled("youtube")
        assert not context.download_providers.is_enabled("generic-ytdlp")
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
