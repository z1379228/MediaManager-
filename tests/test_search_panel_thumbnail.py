from __future__ import annotations

from dataclasses import dataclass

import pytest

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
