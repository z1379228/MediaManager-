from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

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
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    # The presentation assertions do not exercise the modal dependency
    # dialog.  CI intentionally has no bundled runtime dependencies, so the
    # startup timer would otherwise enter the dialog's nested event loop and
    # prevent this test from reaching its window assertions.
    monkeypatch.setattr(
        "trusted_ui.main_window.show_dependency_dialog",
        Mock(),
    )
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    context.settings.initial_mod_setup_completed = True
    observed: dict[str, object] = {}

    def inspect_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
            and widget.isVisible()
        )
        tabs = window.findChild(QTabWidget)
        security_badge = next(
            label
            for label in window.findChildren(QLabel)
            if label.objectName() == "badge" and label.property("securityState")
        )
        observed.update(
            minimum=(window.minimumWidth(), window.minimumHeight()),
            tab_count=tabs.count(),
            first_tabs=tuple(tabs.tabText(index) for index in range(3)),
            surface=window.palette().color(QPalette.ColorRole.Window).name(),
            has_mod_manager=bool(window.findChildren(QTabWidget)),
            locale_count=len(window.language_group.actions()),
            security_text=security_badge.text(),
            security_accessible_name=security_badge.accessibleName(),
            security_accessible_description=security_badge.accessibleDescription(),
            security_tooltip=security_badge.toolTip(),
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
        assert observed["security_accessible_name"] == (
            f"安全狀態：{observed['security_text']}"
        )
        assert observed["security_accessible_description"]
        assert observed["security_accessible_description"] == observed["security_tooltip"]
    finally:
        context.lifecycle.shutdown()


def test_main_window_reverts_controls_when_settings_are_read_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    monkeypatch.setattr(
        "trusted_ui.main_window.show_dependency_dialog",
        Mock(),
    )
    app = QApplication.instance() or QApplication([])
    warning = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", warning)
    context = Bootstrap(portable=True).initialize(start_background=False)
    context.settings.initial_mod_setup_completed = True
    original_locale = context.settings.language
    original_plugin_locale = context.plugin_ui.locale
    original_scale = context.settings.ui_scale
    original_in_app = context.settings.in_app_download_notifications
    settings_path = Path(context.paths.settings) / "settings.json"
    original_document = json.dumps(
        {
            "schema_version": 99,
            "language": original_locale,
            "ui_scale": original_scale,
            "in_app_download_notifications": original_in_app,
        }
    )
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(original_document, encoding="utf-8")

    def exercise_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
            and widget.isVisible()
        )
        original_stylesheet = app.styleSheet()

        next(
            action
            for action in window.language_group.actions()
            if action.data() == "ja"
        ).trigger()
        next(
            action
            for action in window.ui_scale_group.actions()
            if action.data() == "large"
        ).trigger()
        window.in_app_notifications.trigger()
        app.processEvents()

        assert context.settings.language == original_locale
        assert context.plugin_ui.locale == original_plugin_locale
        assert context.settings.ui_scale == original_scale
        assert context.settings.in_app_download_notifications is original_in_app
        assert [
            action.data()
            for action in window.language_group.actions()
            if action.isChecked()
        ] == [original_locale]
        assert [
            action.data()
            for action in window.ui_scale_group.actions()
            if action.isChecked()
        ] == [original_scale]
        assert window.in_app_notifications.isChecked() is original_in_app
        assert app.styleSheet() == original_stylesheet
        assert settings_path.read_text(encoding="utf-8") == original_document
        assert warning.call_count == 3
        assert all("復原" in call.args[2] for call in warning.call_args_list)
        window.close()
        app.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec", exercise_then_exit)
    try:
        assert run_main_window(context) == 0
    finally:
        context.lifecycle.shutdown()
