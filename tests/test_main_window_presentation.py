from __future__ import annotations

import pytest

from trusted_ui.main_window import (
    CORE_LANGUAGE_LABELS,
    populate_core_language_menu,
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
