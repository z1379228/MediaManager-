import pytest
from types import SimpleNamespace

from trusted_ui.table_refresh import (
    suspended_table_updates,
    task_table_interval,
    visible_rows_signature,
)


def test_visible_rows_signature_is_stable_and_tracks_visible_values() -> None:
    assert visible_rows_signature((("a", 1),)) == (("a", "1"),)
    assert visible_rows_signature((("a", 2),)) != visible_rows_signature((("a", 1),))


def test_task_table_interval_adapts_to_activity_and_visibility() -> None:
    assert task_table_interval(active=True, visible=True) == 500
    assert task_table_interval(active=False, visible=True) == 1500
    assert task_table_interval(active=True, visible=False) == 2500
    assert task_table_interval(active=False, visible=False) == 10_000


def test_table_refresh_suspends_only_intermediate_repaints(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QTableWidget

    app = QApplication.instance() or QApplication([])
    table = QTableWidget(1, 1)
    try:
        with suspended_table_updates(table):
            assert not table.updatesEnabled()

        assert table.updatesEnabled()
    finally:
        table.deleteLater()
        app.processEvents()


def test_gopeed_table_skips_equal_snapshots_and_reuses_cells(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from trusted_ui.transfer_panel import create_transfer_panel

    class Bridge:
        config = SimpleNamespace(endpoint="http://127.0.0.1:9999")

        def __init__(self) -> None:
            self.tasks = [
                {
                    "id": "task-1",
                    "name": "Example",
                    "status": "running",
                    "progress": "25%",
                }
            ]

        def list_tasks(self) -> tuple[dict[str, str], ...]:
            return tuple(self.tasks)

    app = QApplication.instance() or QApplication([])
    bridge = Bridge()
    panel = create_transfer_panel(
        SimpleNamespace(gopeed=bridge, p2p_transfer=object())
    )
    try:
        panel.refresh_tasks.click()
        first = panel.task_table.item(0, 3)
        panel.refresh_tasks.click()
        assert panel.task_table.item(0, 3) is first

        bridge.tasks[0]["progress"] = "50%"
        panel.refresh_tasks.click()
        updated = panel.task_table.item(0, 3)
        assert updated is not first
        assert updated.text() == "50%"
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
