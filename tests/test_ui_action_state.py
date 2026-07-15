from __future__ import annotations

from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.bootstrap.bootstrap import Bootstrap
from core.discovery.adapters import FederatedSearchResult, SearchAdapterFailure
from core.downloads.models import DownloadRequest, DownloadTask
from core.downloads.provider_registry import ProviderStatus
from core.storage.paths import AppPaths
from trusted_ui.download_panel import create_download_panel
from trusted_ui.main_window import apply_download_prefill, configure_workspace_tabs
from trusted_ui.search_panel import create_search_panel, search_source_for_url


def test_search_source_is_inferred_only_from_exact_official_hosts() -> None:
    assert (
        search_source_for_url("https://www.youtube.com/watch?v=example")
        == "youtube-search"
    )
    assert (
        search_source_for_url("https://music.youtube.com/watch?v=example")
        == "youtube-search"
    )
    assert (
        search_source_for_url("https://www.bilibili.com/video/BV1example123")
        == "bilibili-search"
    )
    assert (
        search_source_for_url("https://ani.gamer.com.tw/animeRef.php?sn=123")
        == "ani-gamer-search"
    )
    assert search_source_for_url("https://www.youtube.com.evil.test/watch?v=x") == ""
    assert search_source_for_url("https://music.youtube.com.evil.test/watch?v=x") == ""
    assert search_source_for_url("https://user@www.bilibili.com/video/x") == ""
    assert search_source_for_url("http://ani.gamer.com.tw/animeRef.php?sn=123") == ""


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


def test_download_prefill_opens_full_site_setup_and_rejects_unsafe_urls() -> None:
    panel = Mock()
    panel.urls = Mock()
    panel.preview = Mock()
    panel.update_site_options = Mock()
    panel.site_family = "bilibili"
    tabs = Mock()

    assert apply_download_prefill(
        panel,
        tabs,
        {
            "url": "https://www.bilibili.com/video/BV1example123",
            "provider_id": "bilibili",
            "title": "分段影片",
        },
    )
    panel.urls.setPlainText.assert_called_once_with(
        "https://www.bilibili.com/video/BV1example123"
    )
    panel.update_site_options.assert_called_once_with()
    panel.apply_search_result_metadata.assert_called_once()
    assert "分段、字幕與網站專屬選項" in panel.preview.setText.call_args.args[0]
    tabs.setCurrentWidget.assert_called_once_with(panel)
    panel.urls.setFocus.assert_called_once_with()

    panel.reset_mock()
    panel.site_family = "youtube"
    assert not apply_download_prefill(
        panel,
        tabs,
        {
            "url": "https://www.bilibili.com/video/BV1example123",
            "provider_id": "bilibili",
        },
    )
    panel.urls.setPlainText.assert_not_called()

    panel.reset_mock()
    assert not apply_download_prefill(
        panel,
        tabs,
        {"url": "https://user@example.com/video\nhttps://evil.test"},
    )
    panel.urls.setPlainText.assert_not_called()


def test_youtube_search_result_can_be_added_as_single_download(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication, QMessageBox, QTabWidget

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        QMessageBox,
        "question",
        Mock(return_value=QMessageBox.StandardButton.Yes),
    )
    context = Bootstrap(portable=True).initialize(start_background=False)
    panel = create_download_panel(context, site_family="youtube")
    panel.timer.stop()
    tabs = QTabWidget()
    tabs.addTab(panel, "YouTube")
    payload = {
        "url": "https://www.youtube.com/watch?v=example",
        "provider_id": "youtube",
        "video_id": "example",
        "title": "Search result",
        "artist": "Uploader",
        "duration": 125,
        "language": "zh-TW",
        "category": "music",
        "thumbnail_url": "https://i.ytimg.com/vi/example/mqdefault.jpg",
    }
    try:
        assert apply_download_prefill(panel, tabs, payload)
        assert panel.analyzed_url == payload["url"]
        assert panel.analyzed_info["title"] == "Search result"
        assert panel.add_download.isEnabled()

        panel.add_batch()

        tasks = context.download_queue.snapshots()
        assert len(tasks) == 1
        request = tasks[0].request
        assert request.url == payload["url"]
        assert request.source_video_id == "example"
        assert request.source_title == "Search result"
        assert request.source_artist == "Uploader"
        assert request.source_language == "zh-TW"
        assert request.source_category == "music"
    finally:
        panel.close()
        tabs.close()
        app.processEvents()
        context.lifecycle.shutdown()


def test_empty_workspace_actions_are_disabled(tmp_path, monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    search_panel = None
    youtube_panel = None
    bilibili_panel = None
    try:
        search_panel = create_search_panel(context)
        youtube_source = search_panel.search_source.findData("youtube-search")
        ani_gamer_source = search_panel.search_source.findData("ani-gamer-search")
        assert youtube_source >= 0
        assert ani_gamer_source >= 0
        assert search_panel.search_source.itemText(youtube_source).startswith(
            "YouTube 搜尋"
        )
        assert search_panel.search_source.itemText(ani_gamer_source).startswith(
            "動畫瘋官方搜尋"
        )
        assert search_panel.search_source.findData("bilibili-search") < 0
        assert "Bilibili 搜尋需先啟用 Bilibili 主 MOD" in (
            search_panel.search_source_summary.text()
        )
        search_buttons = {
            button.text(): button for button in search_panel.findChildren(QPushButton)
        }
        for label in (
            "尋找替代影片",
            "隨機相似",
            "前往下載設定",
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

        youtube_panel = create_download_panel(context, site_family="youtube")
        bilibili_panel = create_download_panel(context, site_family="bilibili")
        youtube_panel.timer.stop()
        bilibili_panel.timer.stop()
        youtube_controls = {
            control.text() for control in youtube_panel.findChildren(QCheckBox)
        }
        assert "Bilibili" not in youtube_controls
        assert "其他網站 Beta" not in youtube_controls
        assert youtube_panel.danmaku_xml.isHidden()
        assert youtube_panel.format_preset.currentData() == "best"
        assert youtube_panel.subtitle_mode.currentData() == "none"
        assert youtube_panel.subtitle_languages.isHidden()
        youtube_panel.subtitle_mode.setCurrentIndex(1)
        app.processEvents()
        assert not youtube_panel.subtitle_languages.isHidden()
        youtube_panel.subtitle_mode.setCurrentIndex(0)

        bilibili_panel.enabled.setChecked(True)
        app.processEvents()
        bilibili_source = search_panel.search_source.findData("bilibili-search")
        assert bilibili_source >= 0
        assert search_panel.search_source.itemText(bilibili_source).startswith(
            "Bilibili 搜尋"
        )
        bilibili_panel.urls.setPlainText(
            "https://www.bilibili.com/video/BVexample"
        )
        app.processEvents()
        assert not bilibili_panel.danmaku_xml.isHidden()
        bilibili_panel.danmaku_xml.setChecked(True)
        assert not bilibili_panel.danmaku_ass.isHidden()
        assert bilibili_panel.danmaku_mkv.isHidden()
        assert bilibili_panel.selected_media_options() == ("none", ())
        assert bilibili_panel.selected_timed_comment_options() == (
            "source",
            "auto",
        )
        bilibili_panel.danmaku_ass.setChecked(True)
        assert not bilibili_panel.danmaku_mkv.isHidden()
        bilibili_panel.danmaku_mkv.setChecked(True)
        assert bilibili_panel.selected_timed_comment_options() == ("ass", "mkv")
        bilibili_panel.format_preset.setCurrentIndex(
            bilibili_panel.format_preset.findData("audio-m4a")
        )
        app.processEvents()
        assert bilibili_panel.danmaku_ass.isHidden()
        assert bilibili_panel.danmaku_mkv.isHidden()
        assert bilibili_panel.selected_timed_comment_options() == (
            "source",
            "auto",
        )
        bilibili_panel.urls.appendPlainText(
            "https://www.youtube.com/watch?v=example"
        )
        app.processEvents()
        assert bilibili_panel.danmaku_xml.isHidden()
        assert not bilibili_panel.danmaku_xml.isChecked()
        assert not bilibili_panel.add_download.isEnabled()
        download_buttons = {
            button.text(): button for button in youtube_panel.findChildren(QPushButton)
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
        for panel in (youtube_panel, bilibili_panel):
            if panel is not None:
                panel.close()
                panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_facebook_and_mega_workspaces_enable_and_route_independently(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    facebook_panel = create_download_panel(context, site_family="facebook")
    mega_panel = create_download_panel(context, site_family="mega")
    facebook_panel.timer.stop()
    mega_panel.timer.stop()
    try:
        assert not facebook_panel.enabled.isChecked()
        assert not mega_panel.enabled.isChecked()
        assert facebook_panel.workspace_title.text() == "Facebook 下載工作區"
        assert mega_panel.workspace_title.text() == "MEGA 下載工作區"
        assert facebook_panel.thumbnail_preview.pixmap() is not None
        assert mega_panel.thumbnail_preview.pixmap() is not None

        facebook_panel.enabled.setChecked(True)
        mega_panel.enabled.setChecked(True)
        app.processEvents()
        assert context.download_providers.is_enabled("facebook")
        assert context.download_providers.is_enabled("mega")

        facebook_url = "https://www.facebook.com/reel/123456"
        facebook_panel.urls.setPlainText(facebook_url)
        app.processEvents()
        assert facebook_panel.read_info.isEnabled()
        assert facebook_panel.add_download.isEnabled()
        assert context.download_providers.provider_for(facebook_url).provider_id == (
            "facebook"
        )

        mega_file = "https://mega.nz/file/AbCdEf12#abcdefghijklmnop"
        mega_panel.urls.setPlainText(mega_file)
        app.processEvents()
        assert mega_panel.read_info.isEnabled()
        assert mega_panel.add_download.isEnabled()
        assert mega_panel.format_preset.count() == 1
        assert mega_panel.format_preset.currentData() == "best"
        assert mega_panel.subtitle_mode.count() == 1
        assert context.download_providers.provider_for(mega_file).provider_id == "mega"

        mega_panel.urls.setPlainText(
            "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop"
        )
        app.processEvents()
        assert mega_panel.read_info.isEnabled()
        assert not mega_panel.add_download.isEnabled()

        facebook_panel.urls.setPlainText(mega_file)
        app.processEvents()
        assert not facebook_panel.add_download.isEnabled()
    finally:
        facebook_panel.close()
        mega_panel.close()
        facebook_panel.deleteLater()
        mega_panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_core_language_event_updates_built_in_site_mod_ui(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    youtube_panel = create_download_panel(context, site_family="youtube")
    bilibili_panel = create_download_panel(context, site_family="bilibili")
    search_panel = create_search_panel(context)
    youtube_panel.timer.stop()
    bilibili_panel.timer.stop()
    try:
        assert youtube_panel.workspace_title.text() == "YouTube 下載工作區"
        assert bilibili_panel.workspace_title.text() == "Bilibili 下載工作區"

        context.settings.language = "en"
        context.events.publish("ui.language.changed", {"locale": "en"})
        app.processEvents()

        assert youtube_panel.workspace_title.text() == "YouTube Download Workspace"
        assert youtube_panel.enabled.text() == "Enable YouTube main MOD"
        assert youtube_panel.urls_label.text() == "YouTube video / playlist URLs"
        assert bilibili_panel.workspace_title.text() == (
            "Bilibili Download Workspace"
        )
        assert search_panel.enabled.text() == "YouTube Search"
        assert search_panel.bilibili_search_enabled.text() == "Bilibili Search"
    finally:
        search_panel.shutdown()
        search_panel.close()
        youtube_panel.close()
        bilibili_panel.close()
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


def test_youtube_workspace_rejects_meta_and_spoofed_urls(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication([])
    information = Mock(return_value=QMessageBox.StandardButton.Ok)
    warning = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", information)
    monkeypatch.setattr(QMessageBox, "warning", warning)
    download_providers = Mock()
    download_providers.statuses.return_value = (
        ProviderStatus("youtube", "YouTube", True),
        ProviderStatus("generic-ytdlp", "其他網站 Beta", False),
        ProviderStatus("bilibili", "Bilibili", False),
    )
    download_providers.is_enabled.side_effect = lambda provider_id: (
        provider_id == "youtube"
    )
    download_providers.provider_for.side_effect = RuntimeError(
        "no enabled MOD supports this URL"
    )
    download_queue = Mock()
    download_queue.snapshots.return_value = ()
    discovery = Mock()
    discovery.statuses.return_value = ()
    discovery.is_enabled.return_value = False
    context = SimpleNamespace(
        download_providers=download_providers,
        download_queue=download_queue,
        discovery=discovery,
        settings=SimpleNamespace(download_workers=1),
        paths=SimpleNamespace(
            downloads=Path("Downloads"),
            settings=Path("settings"),
        ),
        events=None,
    )
    panel = None
    try:
        panel = create_download_panel(context)
        panel.timer.stop()
        assert panel.official_bridge_notice.isHidden()

        panel.urls.setPlainText("https://www.facebook.com/watch/?v=123456")
        app.processEvents()

        assert panel.official_bridge_notice.isHidden()
        assert not panel.add_download.isEnabled()
        assert "只接受 YouTube" in panel.preview.text()

        panel.add_batch()
        information.assert_called_once()
        assert "只接受 YouTube" in information.call_args.args[2]

        panel.urls.setPlainText(
            "https://www.facebook.com.evil.example/watch/?v=123456"
        )
        app.processEvents()
        assert panel.official_bridge_notice.isHidden()
        assert not panel.add_download.isEnabled()
    finally:
        if panel is not None:
            panel.close()
            panel.deleteLater()
        app.processEvents()


def test_site_search_mods_toggle_independently_and_never_use_youtube_actions(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication([])
    information = Mock(return_value=QMessageBox.StandardButton.Ok)
    warning = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", information)
    monkeypatch.setattr(QMessageBox, "warning", warning)
    context = Bootstrap(portable=True).initialize()
    context.download_providers.set_enabled("bilibili", True)
    panel = None
    try:
        panel = create_search_panel(context)
        assert panel.search_source.findData("youtube-search") >= 0
        assert panel.search_source.findData("bilibili-search") >= 0
        assert panel.search_source.findData("ani-gamer-search") >= 0
        assert "一次查一個網站" in panel.search_source_summary.text()
        assert context.discovery.is_enabled("youtube-search")
        assert not context.discovery.is_enabled("bilibili-search")
        assert not context.discovery.is_enabled("ani-gamer-search")

        bilibili_index = panel.search_source.findData("bilibili-search")
        assert bilibili_index >= 0
        panel.search_source.setCurrentIndex(bilibili_index)
        panel.query.setText("test query")
        routed_sources: list[tuple[str, ...] | None] = []

        def federated_search(
            _query, *, provider_ids, limit, content_type, cursor
        ):
            routed_sources.append(provider_ids)
            assert limit == 20
            assert content_type == "all"
            assert cursor == ""
            return FederatedSearchResult((), (), ())

        monkeypatch.setattr(context.discovery, "federated_search", federated_search)
        panel.search()
        assert routed_sources == []
        assert information.call_count == 1

        class ImmediateThread:
            def __init__(self, *, target, daemon):
                assert daemon
                self.target = target

            def start(self) -> None:
                self.target()

        monkeypatch.setattr(threading, "Thread", ImmediateThread)
        panel.bilibili_search_enabled.setChecked(True)
        panel.search()
        assert routed_sources == [("bilibili-search",)]
        information.reset_mock()

        panel.enabled.setChecked(False)
        panel.ani_gamer_search_enabled.setChecked(True)
        app.processEvents()
        assert not context.discovery.is_enabled("youtube-search")
        assert context.discovery.is_enabled("bilibili-search")
        assert context.discovery.is_enabled("ani-gamer-search")

        bilibili_index = panel.search_source.findData("bilibili-search")
        assert bilibili_index >= 0
        panel.search_source.setCurrentIndex(bilibili_index)

        panel.recovery_enabled.setChecked(True)
        panel.similar_enabled.setChecked(True)
        panel.video_enabled.setChecked(True)
        result = DiscoveryItemV1.from_dict(
            {
                "video_id": "BV1example123",
                "url": "https://www.bilibili.com/video/BV1example123",
                "title": "Bilibili result",
                "artist": "Uploader",
                "duration": 120,
                "language": "",
                "category": "video",
                "thumbnail_url": "",
            }
        )
        panel.show_results(
            FederatedSearchResult(
                (result,),
                (),
                ("bilibili-search",),
                (("bilibili-search", "opaque-next-page"),),
            ),
            "",
        )
        panel.table.selectRow(0)
        app.processEvents()

        assert panel.selected_result_source() == "bilibili-search"
        assert panel.next_search_cursor == "opaque-next-page"
        assert panel.next_page_button.isEnabled()
        assert panel.table.item(0, 5).text() == "Bilibili 搜尋"
        assert panel.download_button.isEnabled()

        context.download_providers.set_enabled("bilibili", True)
        panel.update_action_state()
        assert panel.download_button.isEnabled()
        assert panel.download_button.text() == "前往下載設定"
        assert "Bilibili 下載工作區" in panel.download_button.toolTip()
        assert "YouTube 下載工作區" not in panel.download_button.toolTip()
        assert not panel.preview_button.isEnabled()
        assert not panel.video_button.isEnabled()
        assert not panel.recovery_button.isEnabled()
        assert not panel.similar_button.isEnabled()
        assert panel.open_button.isEnabled()

        prefills: list[object] = []
        context.events.subscribe("download.prefill", prefills.append)
        queue_add = Mock()
        monkeypatch.setattr(context.download_queue, "add", queue_add)
        panel.download_selected()
        queue_add.assert_not_called()
        assert prefills == [
            {
                "url": result.url,
                "provider_id": "bilibili",
                "video_id": result.video_id,
                "title": result.title,
                "artist": result.artist,
                "duration": result.duration,
                "language": result.language,
                "category": result.category,
                "thumbnail_url": result.thumbnail_url,
            }
        ]
        assert panel.status.text() == (
            "已帶入 Bilibili 下載工作區；請確認網站專屬選項。"
        )

        panel.show_results(
            FederatedSearchResult(
                (),
                (
                    SearchAdapterFailure(
                        "bilibili-search",
                        "provider exited without a result",
                        "error",
                    ),
                ),
                (),
            ),
            "",
        )
        assert not panel.failure_button.isHidden()
        assert "1 個來源失敗" in panel.status.text()
        panel.failure_button.click()
        warning.assert_called_once()
        assert "Bilibili 搜尋" in warning.call_args.args[2]
        assert "provider exited without a result" in warning.call_args.args[2]

        ani_index = panel.search_source.findData("ani-gamer-search")
        assert ani_index >= 0
        panel.search_source.setCurrentIndex(ani_index)
        app.processEvents()
        assert panel.next_search_cursor == ""
        assert not panel.next_page_button.isEnabled()

        replacement = Mock()
        similar = Mock()
        video_provider = Mock()
        monkeypatch.setattr(context.discovery, "replacement_candidates", replacement)
        monkeypatch.setattr(context.discovery, "similar_candidates", similar)
        monkeypatch.setattr(context.discovery, "video_preview_provider", video_provider)
        panel.find_replacement()
        panel.find_similar()
        panel.prepare_video_preview()

        replacement.assert_not_called()
        similar.assert_not_called()
        video_provider.assert_not_called()
        # Recovery and similar actions explain why they are YouTube-only.
        # Video preview is already disabled for this source and exits quietly.
        assert information.call_count == 2
        assert panel.busy_action == ""

        panel.query.setText("anime")
        panel.search()
        assert routed_sources == [
            ("bilibili-search",),
            ("ani-gamer-search",),
        ]
        ani_result = DiscoveryItemV1.from_dict(
            {
                "video_id": "ani-123",
                "url": "https://ani.gamer.com.tw/animeRef.php?sn=123",
                "title": "AniGamer result",
                "artist": "巴哈姆特動畫瘋",
                "duration": None,
                "language": "",
                "category": "video",
                "thumbnail_url": "",
            }
        )
        panel.show_results(
            FederatedSearchResult(
                (ani_result,), (), ("ani-gamer-search",)
            ),
            "",
        )
        panel.table.selectRow(0)
        app.processEvents()
        assert panel.selected_result_source() == "ani-gamer-search"
        assert panel.table.item(0, 5).text() == "動畫瘋官方搜尋"
        assert not panel.download_button.isEnabled()
        assert not panel.preview_button.isEnabled()
        assert panel.open_button.isEnabled()

        previous_information_calls = information.call_count
        panel.download_selected()
        queue_add.assert_not_called()
        assert information.call_count == previous_information_calls + 1
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
        assert provider_ids == ("youtube-search",)
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
