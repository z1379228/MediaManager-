from __future__ import annotations

from pathlib import Path

import pytest

from trusted_ui.app_icon import app_icon_path


def test_application_icon_assets_are_loadable(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    png_path = app_icon_path()
    assert png_path is not None
    assert png_path.name == "app-icon.png"

    root = Path(__file__).resolve().parents[1]
    for path in (png_path, root / "assets" / "app-icon.ico"):
        icon = QIcon(str(path))
        assert not icon.isNull()
        for size in (16, 32, 64, 256):
            pixmap = icon.pixmap(size, size)
            assert not pixmap.isNull()
            assert pixmap.width() == size
            assert pixmap.height() == size

    app.processEvents()


def test_pyinstaller_spec_embeds_runtime_and_executable_icons() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "MediaManager.spec").read_text(encoding="utf-8")

    assert "('trusted_ui/assets/app-icon.png', 'trusted_ui/assets')" in spec
    assert "icon='assets/app-icon.ico'" in spec
