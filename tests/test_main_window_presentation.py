from __future__ import annotations

from pathlib import Path

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.storage.paths import AppPaths
from trusted_ui.main_window import (
    CORE_LANGUAGE_LABELS,
    populate_core_language_menu,
    run_main_window,
    security_presentation,
)


def test_security_presentation_is_explicit_and_fail_closed() -> None:
    assert security_presentation("NORMAL", None) == (
        "已驗證",
        "normal",
        "核心與發布檔案驗證通過",
    )
    assert security_presentation("SAFE_MODE", "NotSigned") == (
        "安全模式",
        "safe",
        "NotSigned",
    )
    assert security_presentation("BLOCKED", "tampered") == (
        "已封鎖",
        "blocked",
        "tampered",
    )
    assert security_presentation("unexpected", None)[1] == "unknown"


def test_core_language_menu_exposes_only_four_locales(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QActionGroup
    from PySide6.QtWidgets import QApplication, QMenu

    app = QApplication.instance() or QApplication([])
    menu = QMenu()
    group = QActionGroup(menu)
    group.setExclusive(True)
    try:
        actions = populate_core_language_menu(menu, group, "ja")
        assert tuple((action.text(), action.data()) for action in actions) == (
            CORE_LANGUAGE_LABELS
        )
        assert [action.data() for action in actions if action.isChecked()] == ["ja"]
        assert all("可信核心" in action.toolTip() for action in actions)
    finally:
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_complete_main_window_builds_at_supported_minimum_size(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    observed: dict[str, object] = {}

    def inspect_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
        )
        tabs = window.findChild(QTabWidget)
        observed.update(
            minimum=(window.minimumWidth(), window.minimumHeight()),
            tab_count=tabs.count(),
            first_tabs=tuple(tabs.tabText(index) for index in range(3)),
            surface=window.palette().color(QPalette.ColorRole.Window).name(),
            has_mod_manager=bool(window.findChildren(QTabWidget)),
            locale_count=len(window.language_group.actions()),
        )
        window.close()
        app.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec", inspect_then_exit)
    try:
        assert run_main_window(context) == 0
        assert observed["minimum"] == (940, 620)
        assert observed["tab_count"] >= 4
        assert observed["first_tabs"][0].startswith("YouTube")
        assert observed["first_tabs"][1].startswith("Bilibili")
        assert observed["surface"] == "#0a0f1d"
        assert observed["has_mod_manager"]
        assert observed["locale_count"] == 4
    finally:
        context.lifecycle.shutdown()
