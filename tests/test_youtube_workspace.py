from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from core.downloads.provider_registry import ProviderStatus
from trusted_ui.download_panel import create_download_panel
from trusted_ui.youtube_workspace import (
    create_youtube_workspace,
    is_official_youtube_url,
    is_youtube_playlist_url,
    is_youtube_video_url,
    merge_download_urls,
    youtube_host_label,
    youtube_url_kind_label,
)


def _item(
    video_id: str,
    url: str,
    title: str,
    *,
    duration: int | None = 120,
) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url,
        title,
        "頻道",
        duration,
        "",
        "video",
        "",
    )


def _wait_until(app: object, predicate: object, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("timed out waiting for YouTube workspace")


def test_youtube_workspace_accepts_only_exact_official_https_hosts() -> None:
    accepted = {
        "https://youtube.com/watch?v=one": "YouTube",
        "https://www.youtube.com/watch?v=two": "YouTube",
        "https://m.youtube.com/watch?v=three": "YouTube 行動版",
        "https://music.youtube.com/watch?v=four": "YouTube Music",
        "https://youtu.be/five": "youtu.be",
        "https://www.youtube-nocookie.com/embed/six": "YouTube 隱私嵌入",
    }
    for url, label in accepted.items():
        assert is_official_youtube_url(url)
        assert youtube_host_label(url) == label

    for url in (
        "http://www.youtube.com/watch?v=one",
        "https://www.youtube.com.evil.test/watch?v=one",
        "https://user@music.youtube.com/watch?v=one",
        "https://youtu.be:443/one",
        "https://youtube.com",
        "https://www.youtube-nocookie.com/watch?v=one",
        "https://www.youtube.com/watch?v=one\nhttps://evil.test",
    ):
        assert not is_official_youtube_url(url)


def test_merge_download_urls_preserves_order_and_removes_duplicates() -> None:
    assert merge_download_urls(
        "https://example.test/one\nhttps://www.youtube.com/watch?v=two\n",
        (
            "https://www.youtube.com/watch?v=two",
            "https://music.youtube.com/watch?v=three",
        ),
    ) == (
        "https://example.test/one",
        "https://www.youtube.com/watch?v=two",
        "https://music.youtube.com/watch?v=three",
    )
    assert merge_download_urls("one\ntwo", ("three",), limit=2) == (
        "one",
        "two",
    )


def test_youtube_playlist_route_requires_exact_host_and_valid_list_id() -> None:
    assert is_youtube_playlist_url(
        "https://music.youtube.com/playlist?list=PL2yqXecZHhEYKaKiTSsfUhEeqeAm89wcp"
    )
    assert is_youtube_playlist_url(
        "https://www.youtube.com/watch?v=one&list=PL_example-123"
    )
    for url in (
        "https://music.youtube.com/playlist",
        "https://music.youtube.com/playlist?list=",
        "https://music.youtube.com/playlist?list=bad%20value",
        "https://music.youtube.com.evil.test/playlist?list=PL_example",
        "https://user@music.youtube.com/playlist?list=PL_example",
        "https://music.youtube.com:443/playlist?list=PL_example",
        "https://www.youtube.com/watch?v=one",
    ):
        assert not is_youtube_playlist_url(url)


def test_youtube_url_kind_keeps_video_and_playlist_context_distinct() -> None:
    single = "https://music.youtube.com/watch?v=one"
    playlist = "https://music.youtube.com/playlist?list=PL_example"
    context = "https://music.youtube.com/watch?v=one&list=PL_example"

    assert is_youtube_video_url(single)
    assert not is_youtube_playlist_url(single)
    assert not is_youtube_video_url(playlist)
    assert is_youtube_playlist_url(playlist)
    assert is_youtube_video_url(context)
    assert is_youtube_playlist_url(context)
    assert "單一 YouTube 影片" in youtube_url_kind_label(single)
    assert "播放清單中的單一" in youtube_url_kind_label(context)


def test_youtube_search_child_requires_main_mod(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    parent_state = {"enabled": False}
    context = SimpleNamespace(
        discovery=SimpleNamespace(
            statuses=lambda: (
                ProviderStatus("youtube-search", "YouTube Search", True),
            ),
            is_enabled=lambda provider_id: provider_id == "youtube-search",
        ),
        download_providers=SimpleNamespace(
            is_enabled=lambda provider_id: (
                provider_id == "youtube" and parent_state["enabled"]
            )
        ),
        events=None,
        audit=None,
    )
    workspace = create_youtube_workspace(context, lambda _urls: None)
    try:
        assert not workspace.enabled.isEnabled()
        assert "先啟用" in workspace.enabled.text()
        assert not workspace.search_button.isEnabled()

        parent_state["enabled"] = True
        workspace.refresh_availability()
        assert workspace.enabled.isEnabled()
        assert workspace.enabled.isChecked()
        assert workspace.search_button.isEnabled()
    finally:
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()


def test_download_workspace_routes_pure_youtube_playlist_before_analysis(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    class ImmediateThread:
        def __init__(self, *, target: object, **_options: object) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    app = QApplication.instance() or QApplication([])
    download_providers = Mock()
    download_providers.statuses.return_value = (
        ProviderStatus("youtube", "YouTube", True),
    )
    download_providers.is_enabled.side_effect = lambda provider_id: (
        provider_id == "youtube"
    )
    download_providers.provider_for.return_value = SimpleNamespace(
        provider_id="youtube"
    )
    download_providers.analyze.return_value = {
        "title": "單片",
        "uploader": "頻道",
        "duration": 10,
        "formats": [],
        "audio_languages": [],
        "subtitle_languages": [],
    }
    download_queue = Mock()
    download_queue.snapshots.return_value = ()
    discovery = Mock()
    discovery.statuses.return_value = (
        ProviderStatus("youtube-search", "YouTube Search", True),
    )
    discovery.is_enabled.side_effect = lambda provider_id: (
        provider_id == "youtube-search"
    )
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
        audit=None,
    )
    panel = create_download_panel(context)
    try:
        panel.timer.stop()
        assert panel.workspace_title.text() == "YouTube 下載工作區"
        prepare_playlist = Mock()
        panel.prepare_playlist = prepare_playlist
        panel.urls.setPlainText(
            "https://music.youtube.com/playlist?"
            "list=PL2yqXecZHhEYKaKiTSsfUhEeqeAm89wcp"
        )
        app.processEvents()
        assert "YouTube 播放清單" in panel.url_classification.text()
        assert panel.expand_playlist.isEnabled()
        assert not panel.read_info.isEnabled()
        assert not panel.media_preview_controls.audio_button.isEnabled()
        panel.analyze_first()

        prepare_playlist.assert_called_once_with()
        download_providers.analyze.assert_not_called()
        assert "播放清單" in panel.preview.text()

        monkeypatch.setattr(
            "trusted_ui.download_panel.threading.Thread", ImmediateThread
        )
        panel.urls.setPlainText("https://music.youtube.com/watch?v=single")
        app.processEvents()
        assert "單一 YouTube 影片" in panel.url_classification.text()
        assert not panel.expand_playlist.isEnabled()
        assert panel.read_info.isEnabled()
        assert panel.media_preview_controls.audio_button.isEnabled()
        assert not panel.media_preview_controls.video_button.isEnabled()
        panel.analyze_first()

        prepare_playlist.assert_called_once_with()
        download_providers.analyze.assert_called_once_with(
            "https://music.youtube.com/watch?v=single"
        )
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_youtube_workspace_uses_one_source_and_only_prefills_selected_urls(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    calls: list[dict[str, object]] = []
    added: list[tuple[str, ...]] = []
    items = (
        _item(
            "one",
            "https://www.youtube.com/watch?v=one",
            "第一首",
        ),
        _item(
            "two",
            "https://music.youtube.com/watch?v=two",
            "第二首",
            duration=3661,
        ),
    )

    def federated_search(query: str, **options: object) -> FederatedSearchResult:
        calls.append({"query": query, **options})
        if options.get("cursor"):
            return FederatedSearchResult(
                (
                    items[1],
                    _item(
                        "three",
                        "https://www.youtube.com/watch?v=three",
                        "第三首",
                    ),
                ),
                (),
                ("youtube-search", "youtube-search"),
            )
        return FederatedSearchResult(
            items,
            (),
            ("youtube-search", "youtube-search"),
            (("youtube-search", "next-token"),),
        )

    discovery = SimpleNamespace(
        statuses=lambda: (
            ProviderStatus("youtube-search", "YouTube Search", True),
        ),
        is_enabled=lambda provider_id: provider_id
        in {"youtube-search", "youtube-player"},
        federated_search=federated_search,
        video_preview_provider=Mock,
    )
    download_providers = SimpleNamespace(
        is_enabled=lambda provider_id: provider_id == "youtube",
        provider_for=Mock,
    )
    context = SimpleNamespace(
        discovery=discovery,
        download_providers=download_providers,
        events=None,
        audit=None,
    )
    workspace = create_youtube_workspace(context, added.append)
    try:
        assert workspace.body.isHidden()
        assert workspace.table.selectionMode().name == "ExtendedSelection"
        workspace.toggle_button.setChecked(True)
        workspace.query.setText("幻月環")
        workspace.search()
        _wait_until(app, lambda: not workspace.busy)

        assert calls == [
            {
                "query": "幻月環",
                "provider_ids": ("youtube-search",),
                "limit": 24,
                "content_type": "all",
                "cursor": "",
            }
        ]
        assert workspace.table.rowCount() == 2
        assert workspace.more_button.isEnabled()
        workspace.table.selectRow(0)
        workspace.load_more()
        _wait_until(app, lambda: not workspace.busy)
        assert workspace.table.rowCount() == 3
        assert not workspace.more_button.isEnabled()
        assert calls[1]["cursor"] == "next-token"
        assert workspace.selected_urls() == (items[0].url,)
        assert workspace.table.item(0, 4).text() == "YouTube"
        assert workspace.table.item(1, 3).text() == "1:01:01"
        assert workspace.table.item(1, 4).text() == "YouTube Music"

        workspace.table.selectRow(0)
        assert workspace.preview_controls.audio_button.isEnabled()
        assert workspace.preview_controls.video_button.isEnabled()
        workspace.table.selectionModel().select(
            workspace.table.model().index(1, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        workspace.add_selected()

        assert added == [tuple(item.url for item in items)]
        assert "確認格式" in workspace.status.text()

        workspace.query.setText("https://youtu.be/direct")
        workspace.search()
        assert added[-1] == ("https://youtu.be/direct",)
        assert len(calls) == 2
    finally:
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()


def test_youtube_workspace_cancel_discards_late_results(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    started = threading.Event()
    release = threading.Event()

    def federated_search(*_args: object, **_kwargs: object) -> FederatedSearchResult:
        started.set()
        release.wait(1.0)
        return FederatedSearchResult(
            (
                _item(
                    "late",
                    "https://www.youtube.com/watch?v=late",
                    "不應顯示",
                ),
            ),
            (),
            ("youtube-search",),
        )

    discovery = SimpleNamespace(
        statuses=lambda: (
            ProviderStatus("youtube-search", "YouTube Search", True),
        ),
        is_enabled=lambda provider_id: provider_id == "youtube-search",
        federated_search=federated_search,
    )
    context = SimpleNamespace(
        discovery=discovery,
        download_providers=SimpleNamespace(
            is_enabled=lambda provider_id: provider_id == "youtube"
        ),
        events=None,
        audit=None,
    )
    workspace = create_youtube_workspace(context, lambda _urls: None)
    try:
        workspace.query.setText("取消測試")
        workspace.search()
        assert started.wait(1.0)
        workspace.cancel_search()
        assert "取消" in workspace.status.text()
        release.set()
        _wait_until(app, lambda: not workspace.busy)
        assert workspace.table.rowCount() == 0
        assert workspace.results == ()
        assert workspace.status.text() == "YouTube 搜尋已取消。"
    finally:
        release.set()
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()


def test_youtube_workspace_cancel_load_more_preserves_existing_results(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    started = threading.Event()
    release = threading.Event()

    def federated_search(*_args: object, **_kwargs: object) -> FederatedSearchResult:
        started.set()
        release.wait(1.0)
        return FederatedSearchResult(
            (
                _item(
                    "late",
                    "https://www.youtube.com/watch?v=late",
                    "不應附加",
                ),
            ),
            (),
            ("youtube-search",),
        )

    discovery = SimpleNamespace(
        statuses=lambda: (
            ProviderStatus("youtube-search", "YouTube Search", True),
        ),
        is_enabled=lambda provider_id: provider_id == "youtube-search",
        federated_search=federated_search,
    )
    context = SimpleNamespace(
        discovery=discovery,
        download_providers=SimpleNamespace(
            is_enabled=lambda provider_id: provider_id == "youtube"
        ),
        events=None,
        audit=None,
    )
    workspace = create_youtube_workspace(context, lambda _urls: None)
    existing = _item(
        "existing",
        "https://www.youtube.com/watch?v=existing",
        "保留結果",
    )
    try:
        workspace.results = (existing,)
        workspace.last_query = "續頁取消測試"
        workspace.next_cursor = "next-token"
        workspace.populate_results()
        workspace.load_more()
        assert started.wait(1.0)
        workspace.cancel_search()
        release.set()
        _wait_until(app, lambda: not workspace.busy)

        assert workspace.results == (existing,)
        assert workspace.table.rowCount() == 1
        assert workspace.next_cursor == "next-token"
        assert workspace.status.text() == "已取消載入更多；原搜尋結果仍保留。"
    finally:
        release.set()
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()
