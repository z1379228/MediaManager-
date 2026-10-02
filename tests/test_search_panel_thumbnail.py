from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import (
    FederatedSearchResult,
    SearchAdapterFailure,
)
from trusted_ui.search_panel import create_search_panel


class _Discovery:
    def statuses(self) -> tuple[object, ...]:
        return ()

    def is_enabled(self, provider_id: str) -> bool:
        return False

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        return None


@dataclass(frozen=True, slots=True)
class _Result:
    video_id: str
    thumbnail_url: str


@dataclass(slots=True)
class _Context:
    discovery: object


def test_stale_thumbnail_callback_cannot_repaint_current_results(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtWidgets import QApplication, QTableWidgetItem

    app = QApplication.instance() or QApplication([])
    panel = create_search_panel(_Context(_Discovery()))
    result = _Result("video-1", "https://i.ytimg.com/vi/video-1/mqdefault.jpg")
    panel.results = (result,)
    panel.results_generation = 3
    panel.table.setRowCount(1)
    cell = QTableWidgetItem("載入中")
    panel.table.setItem(0, 0, cell)
    pixmap = QPixmap(96, 54)
    pixmap.fill(QColor("#345678"))

    panel.show_thumbnail(2, 0, result, pixmap)
    assert cell.text() == "載入中"
    assert cell.icon().isNull()

    panel.generation = 99
    panel.show_thumbnail(3, 0, result, pixmap)
    assert cell.text() == ""
    assert not cell.icon().isNull()

    panel.shutdown()
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_federated_results_show_source_and_partial_failure(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    panel = create_search_panel(_Context(_Discovery()))
    item = DiscoveryItemV1(
        "video-1",
        "https://example.test/watch?v=video-1",
        "Example",
        "Artist",
        120,
        "zh-TW",
        "music",
        "",
    )
    result = FederatedSearchResult(
        (item,),
        (SearchAdapterFailure("offline-search", "temporary outage"),),
        ("youtube-search",),
    )

    panel.show_results(result, "")

    assert panel.table.item(0, 5).text() == "youtube-search"
    assert "1 個來源失敗" in panel.status.text()
    assert "offline-search: temporary outage" in panel.status.toolTip()
    assert panel.retry_failure_button.isVisibleTo(panel)
    assert panel.retry_failure_button.text() == "只重試失敗來源"

    panel.shutdown()
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_search_panel_only_requests_visible_thumbnail_window(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    panel = create_search_panel(_Context(_Discovery()))
    loaded: list[str] = []
    panel.thumbnail_loader.load = lambda url, _callback: loaded.append(url)
    results = tuple(
        DiscoveryItemV1(
            f"video-{index}",
            f"https://www.youtube.com/watch?v=video-{index}",
            f"Result {index}",
            "Artist",
            120,
            "zh-TW",
            "music",
            f"https://i.ytimg.com/vi/video-{index}/mqdefault.jpg",
        )
        for index in range(80)
    )

    try:
        panel.resize(900, 620)
        panel.show()
        app.processEvents()
        panel.show_results(results, "")
        app.processEvents()

        initial_count = len(loaded)
        assert 0 < initial_count < len(results)

        panel.table.verticalScrollBar().setValue(
            panel.table.verticalScrollBar().maximum()
        )
        app.processEvents()
        assert initial_count < len(loaded) < len(results)

        panel.thumbnail_loader.cancel_pending()
        assert panel.thumbnail_requests == set()
        panel.thumbnail_loader.resume()
        assert len(loaded) > initial_count
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_search_panel_batches_result_table_repaints(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    import trusted_ui.search_panel as search_panel

    app = QApplication.instance() or QApplication([])
    original = search_panel.suspended_table_updates
    update_states: list[bool] = []

    @contextmanager
    def observe_updates(table):
        with original(table):
            update_states.append(table.updatesEnabled())
            yield
        update_states.append(table.updatesEnabled())

    monkeypatch.setattr(search_panel, "suspended_table_updates", observe_updates)
    panel = search_panel.create_search_panel(_Context(_Discovery()))
    result = DiscoveryItemV1(
        "video-1",
        "https://www.youtube.com/watch?v=video-1",
        "Example",
        "Artist",
        120,
        "zh-TW",
        "music",
        "",
    )
    try:
        panel.show_results((result,), "")

        assert update_states == [False, True]
        assert panel.table.item(0, 1).text() == "Example"
        assert panel.table.rowHeight(0) == 66
        assert panel.table.updatesEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
