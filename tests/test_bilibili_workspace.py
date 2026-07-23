from __future__ import annotations

from types import SimpleNamespace

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.playlist_v1 import PlaylistEntryV1
from core.discovery.adapters import FederatedSearchResult
from core.downloads.provider_registry import ProviderStatus
from trusted_ui.bilibili_workspace import (
    bilibili_host_label,
    bilibili_search_page_url,
    bilibili_url_kind_label,
    create_bilibili_workspace,
    filter_bilibili_playlist_entries,
    is_official_bilibili_url,
    merge_bilibili_download_urls,
)


def _playlist_entry(title: str, artist: str, entry_id: str) -> PlaylistEntryV1:
    return PlaylistEntryV1(
        entry_id=entry_id,
        url=f"https://www.bilibili.com/video/{entry_id}",
        title=title,
        artist=artist,
        duration=60,
        position=1,
        thumbnail_url="",
        available=True,
        unavailable_reason="",
    )


def test_bilibili_playlist_filter_matches_title_uploader_or_part_id() -> None:
    entries = (
        _playlist_entry("主題曲", "UP One", "BVone-p1"),
        _playlist_entry("製作花絮", "UP Two", "BVtwo-p2"),
    )

    assert filter_bilibili_playlist_entries(entries, "主題") == entries[:1]
    assert filter_bilibili_playlist_entries(entries, "up two") == entries[1:]
    assert filter_bilibili_playlist_entries(entries, "p2") == entries[1:]
    assert filter_bilibili_playlist_entries(entries, "") == entries


def _item(video_id: str, url: str, title: str, uploader: str) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url,
        title,
        uploader,
        125,
        "zh-TW",
        "video",
        "",
    )


def test_bilibili_workspace_accepts_only_exact_official_https_routes() -> None:
    accepted = {
        "https://www.bilibili.com/video/BVexample": "Bilibili",
        "https://m.bilibili.com/video/BVmobile": "Bilibili 行動版",
        "https://space.bilibili.com/12345/video": "UP 主空間",
        "https://www.bilibili.com/bangumi/play/ep123": "Bilibili",
        "https://b23.tv/example": "b23.tv",
        "https://www.bilibili.tv/en/video/2041863208": "Bilibili 國際版",
        "https://bilibili.tv/en/play/1018660/11515462": "Bilibili 國際版",
    }
    for url, label in accepted.items():
        assert is_official_bilibili_url(url)
        assert bilibili_host_label(url) == label

    for url in (
        "http://www.bilibili.com/video/BVexample",
        "https://www.bilibili.com.evil.test/video/BVexample",
        "https://user@www.bilibili.com/video/BVexample",
        "https://www.bilibili.com:443/video/BVexample",
        "https://www.bilibili.com/",
        "https://search.bilibili.com/all?keyword=example",
        "https://www.bilibili.com/video/BVexample\nhttps://evil.test",
        "https://www.biliintl.com/en/video/2041863208",
    ):
        assert not is_official_bilibili_url(url)


def test_bilibili_kind_and_merge_keep_creator_and_video_distinct() -> None:
    video = "https://www.bilibili.com/video/BVexample"
    creator = "https://space.bilibili.com/12345/video"

    assert "影片" in bilibili_url_kind_label(video)
    assert "UP 主影片清單" in bilibili_url_kind_label(creator)
    assert merge_bilibili_download_urls(
        f"{video}\nhttps://evil.test/video",
        (creator, video, "https://www.youtube.com/watch?v=wrong"),
    ) == (video, creator)
    assert bilibili_search_page_url(" Blender  動畫 ") == (
        "https://search.bilibili.com/all?keyword=Blender+%E5%8B%95%E7%95%AB"
    )


def test_bilibili_workspace_filters_one_source_and_batches_selected_uploader(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    parent_state = {"enabled": False}
    added: list[tuple[str, ...]] = []
    calls: list[dict[str, object]] = []

    class ImmediateThread:
        def __init__(self, *, target, **_kwargs) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(
        "trusted_ui.bilibili_workspace.threading.Thread", ImmediateThread
    )
    items = (
        _item(
            "one",
            "https://www.bilibili.com/video/BVone",
            "第一段",
            "UP 甲",
        ),
        _item(
            "two",
            "https://www.bilibili.com/video/BVtwo",
            "第二段",
            "UP 乙",
        ),
        _item(
            "three",
            "https://m.bilibili.com/video/BVthree",
            "第三段",
            "UP 甲",
        ),
        _item(
            "wrong",
            "https://www.youtube.com/watch?v=wrong",
            "錯誤來源",
            "UP 甲",
        ),
    )
    discovery = SimpleNamespace(
        statuses=lambda: (
            ProviderStatus("bilibili-search", "Bilibili Search", True),
        ),
        is_enabled=lambda provider_id: provider_id == "bilibili-search",
        federated_search=lambda query, **options: (
            calls.append({"query": query, **options})
            or FederatedSearchResult(
                (
                    items[0],
                    _item(
                        "four",
                        "https://www.bilibili.com/video/BVfour",
                        "第四段",
                        "UP 甲",
                    ),
                ),
                (),
                ("bilibili-search", "bilibili-search"),
            )
        ),
    )
    context = SimpleNamespace(
        discovery=discovery,
        download_providers=SimpleNamespace(
            is_enabled=lambda provider_id: (
                provider_id == "bilibili" and parent_state["enabled"]
            )
        ),
        events=None,
        audit=None,
    )
    workspace = create_bilibili_workspace(context, added.append)
    try:
        assert not workspace.enabled.isEnabled()
        assert "先啟用" in workspace.enabled.text()

        parent_state["enabled"] = True
        workspace.refresh_availability()
        assert workspace.enabled.isEnabled()
        assert workspace.enabled.isChecked()

        response = FederatedSearchResult(
            items,
            (),
            ("bilibili-search",) * len(items),
            (("bilibili-search", "next-token"),),
        )
        workspace.show_results(0, response, "")
        assert workspace.table.rowCount() == 3
        assert "略過 1 筆" in workspace.status.text()
        workspace.last_query = "動畫"
        assert workspace.more_button.isEnabled()
        workspace.table.selectRow(0)
        workspace.load_more()
        assert calls == [
            {
                "query": "動畫",
                "provider_ids": ("bilibili-search",),
                "limit": 50,
                "content_type": "all",
                "cursor": "next-token",
            }
        ]
        assert workspace.table.rowCount() == 4
        assert not workspace.more_button.isEnabled()
        assert workspace.selected_urls() == (items[0].url,)

        uploader_index = workspace.up_filter.findData("UP 甲")
        assert uploader_index >= 0
        workspace.up_filter.setCurrentIndex(uploader_index)
        assert workspace.table.rowCount() == 3
        workspace.table_select_all()
        workspace.add_selected()

        assert added == [
            (
                "https://www.bilibili.com/video/BVone",
                "https://m.bilibili.com/video/BVthree",
                "https://www.bilibili.com/video/BVfour",
            )
        ]
        assert "UP 主：UP 甲" in workspace.status.text()
    finally:
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()
