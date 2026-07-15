from __future__ import annotations

from types import SimpleNamespace

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from core.downloads.provider_registry import ProviderStatus
from trusted_ui.bilibili_workspace import (
    bilibili_host_label,
    bilibili_search_page_url,
    bilibili_url_kind_label,
    create_bilibili_workspace,
    is_official_bilibili_url,
    merge_bilibili_download_urls,
)


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
        "https://www.bilibili.com/video/BVexample\nhttps://evil.test",
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
        )
        workspace.show_results(0, response, "")
        assert workspace.table.rowCount() == 3
        assert "略過 1 筆" in workspace.status.text()

        uploader_index = workspace.up_filter.findData("UP 甲")
        assert uploader_index >= 0
        workspace.up_filter.setCurrentIndex(uploader_index)
        assert workspace.table.rowCount() == 2
        workspace.table_select_all()
        workspace.add_selected()

        assert added == [
            (
                "https://www.bilibili.com/video/BVone",
                "https://m.bilibili.com/video/BVthree",
            )
        ]
        assert "UP 主：UP 甲" in workspace.status.text()
    finally:
        workspace.shutdown()
        workspace.close()
        workspace.deleteLater()
        app.processEvents()
