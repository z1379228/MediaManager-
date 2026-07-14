from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget

from core.bootstrap.bootstrap import Bootstrap
from core.storage.paths import AppPaths
from trusted_ui.library_panel import create_library_panel


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
    assert "檢視重複檔案" in {
        action.text() for action in buttons["管理"].menu().actions()
    }

    panel.deleteLater()
    app.processEvents()
    context.lifecycle.shutdown()
