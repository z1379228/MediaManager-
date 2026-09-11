from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
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
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QLabel,
        QMainWindow,
        QTabWidget,
    )

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
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
            and widget.settings_root == Path(context.paths.settings)
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
            idle_text=window.idle_status.text(),
            close_behavior=window.close_behavior_select.currentData(),
            close_behavior_accessible=(
                window.close_behavior_select.accessibleName()
            ),
            lazy_core_initial=tuple(window.core_workspace_manager.panels),
            lazy_optional_initial=tuple(window.optional_workspace_manager.panels),
            lazy_placeholder_count=len(
                window.findChildren(QFrame, "lazyWorkspacePlaceholder")
            ),
        )
        tabs.setCurrentIndex(1)
        app.processEvents()
        bilibili_panel = window.core_workspace_manager.panels["bilibili"]
        observed["lazy_core_after_select"] = tuple(
            window.core_workspace_manager.panels
        )
        tabs.setCurrentIndex(0)
        tabs.setCurrentIndex(1)
        app.processEvents()
        observed["lazy_panel_retained"] = (
            window.core_workspace_manager.panels["bilibili"] is bilibili_panel
        )
        navigator_menu = window.workspace_navigator.menu()
        navigator_menu.aboutToShow.emit()
        observed["navigator_accessible"] = (
            window.workspace_navigator.accessibleName()
        )
        observed["navigator_groups"] = tuple(
            action.text() for action in navigator_menu.actions()
        )
        search_group = next(
            action.menu()
            for action in navigator_menu.actions()
            if action.text() == "搜尋與媒體"
        )
        library_action = next(
            action
            for action in search_group.actions()
            if action.text() == "本機媒體庫"
        )
        library_action.trigger()
        app.processEvents()
        observed["navigator_selected"] = tabs.currentWidget().property(
            "workspaceId"
        )
        window.close_behavior_select.setCurrentIndex(1)
        app.processEvents()
        observed["saved_close_behavior"] = context.settings.close_behavior
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
        assert observed["idle_text"] == "使用中"
        assert observed["close_behavior"] == "minimize-to-tray"
        assert observed["close_behavior_accessible"] == "關閉按鈕行為"
        assert observed["lazy_core_initial"] == ()
        assert observed["lazy_optional_initial"] == ()
        assert observed["lazy_placeholder_count"] >= 3
        assert observed["lazy_core_after_select"] == ("bilibili",)
        assert observed["lazy_panel_retained"] is True
        assert observed["navigator_accessible"] == "切換工作區"
        assert observed["navigator_groups"][:2] == ("下載", "搜尋與媒體")
        assert observed["navigator_selected"] == "library"
        assert observed["saved_close_behavior"] == "exit"
    finally:
        context.lifecycle.shutdown()


def test_clean_main_window_startup_defers_multimedia_import(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    script = textwrap.dedent(
        """
        import sys
        from pathlib import Path

        from core.bootstrap.bootstrap import Bootstrap
        from core.storage.paths import AppPaths
        from PySide6.QtWidgets import QApplication, QMainWindow

        root = Path(sys.argv[1])
        paths = AppPaths.discover(portable=True, app_root=root)
        AppPaths.discover = lambda **_: paths
        app = QApplication.instance() or QApplication([])
        context = Bootstrap(portable=True).initialize(start_background=False)

        import trusted_ui.main_window as main_window

        deferred_modules = {
            "trusted_ui.automation_panel",
            "trusted_ui.conversion_panel",
            "trusted_ui.direct_http_workspace",
            "trusted_ui.library_panel",
            "trusted_ui.mega_workspace",
            "trusted_ui.official_social_workspace",
            "trusted_ui.search_panel",
            "trusted_ui.transcription_panel",
            "trusted_ui.transfer_panel",
        }
        assert "PySide6.QtMultimedia" not in sys.modules
        assert deferred_modules.isdisjoint(sys.modules)

        def inspect_then_exit(_app):
            app.processEvents()
            assert "PySide6.QtMultimedia" not in sys.modules
            assert deferred_modules.isdisjoint(sys.modules)
            window = next(
                widget
                for widget in app.topLevelWidgets()
                if isinstance(widget, QMainWindow)
                and widget.accessibleName() == "MediaManager 主視窗"
            )
            window.request_full_exit()
            app.processEvents()
            return 0

        QApplication.exec = inspect_then_exit
        try:
            assert main_window.run_main_window(context) == 0
            assert "PySide6.QtMultimedia" not in sys.modules
            assert deferred_modules.isdisjoint(sys.modules)
        finally:
            context.lifecycle.shutdown()
        """
    )
    env = os.environ.copy()
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "QT_QPA_PLATFORM": "offscreen",
        }
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_background_idle_stops_ui_polling_and_restores_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMainWindow

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    observed: dict[str, object] = {}

    def exercise_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
            and widget.settings_root == Path(context.paths.settings)
            and widget.isVisible()
        )
        active_timers = tuple(
            timer
            for timer in window.findChildren(QTimer)
            if timer.isActive() and not timer.isSingleShot()
        )
        assert active_timers
        monkeypatch.setattr(window, "ensure_system_tray", lambda: object())

        window.close()
        app.processEvents()
        observed["idle_text"] = window.idle_status.text()
        observed["hidden"] = window.isHidden()
        observed["timers_stopped"] = all(
            not timer.isActive() for timer in active_timers
        )

        window.restore_from_background()
        app.processEvents()
        observed["restored"] = window.isVisible()
        observed["timers_restarted"] = all(
            timer.isActive() for timer in active_timers
        )

        window.showMinimized()
        window.showNormal()
        app.processEvents()
        observed["fast_restore_active"] = not window.idle_resources.idle
        observed["fast_restore_timers"] = all(
            timer.isActive() for timer in active_timers
        )
        window.request_full_exit()
        app.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec", exercise_then_exit)
    try:
        assert run_main_window(context) == 0
        assert observed == {
            "idle_text": "背景待機",
            "hidden": True,
            "timers_stopped": True,
            "restored": True,
            "timers_restarted": True,
            "fast_restore_active": True,
            "fast_restore_timers": True,
        }
    finally:
        context.lifecycle.shutdown()


def test_startup_opens_main_window_without_modal_prompts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QDialog, QMainWindow

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    assert context.settings.initial_mod_setup_completed is False
    modal_titles: list[str] = []

    def record_modal(dialog: QDialog) -> int:
        modal_titles.append(dialog.windowTitle())
        return 0

    def inspect_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
            and widget.settings_root == Path(context.paths.settings)
            and widget.isVisible()
        )
        monkeypatch.setattr(window, "ensure_system_tray", lambda: None)
        window.close()
        app.processEvents()
        assert window._shutdown_started
        assert app.quitOnLastWindowClosed()
        return 0

    monkeypatch.setattr(QDialog, "exec", record_modal)
    monkeypatch.setattr(QApplication, "exec", inspect_then_exit)
    try:
        assert run_main_window(context) == 0
        assert modal_titles == []
        assert context.settings.initial_mod_setup_completed is False
    finally:
        context.lifecycle.shutdown()


def test_browser_handoff_opens_visible_target_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QMainWindow

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
            and widget.settings_root == Path(context.paths.settings)
        )
        panel = window.site_download_panels["youtube"]
        observed["visible"] = window.isVisible()
        observed["idle"] = window.idle_resources.idle
        observed["url"] = panel.urls.toPlainText()
        observed["focus"] = panel.urls.hasFocus()
        window.request_full_exit()
        app.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec", inspect_then_exit)
    try:
        assert (
            run_main_window(
                context,
                start_minimized=True,
                initial_prefill={
                    "url": "https://www.youtube.com/watch?v=example",
                    "title": "Browser share",
                    "provider_id": "browser-handoff",
                },
            )
            == 0
        )
        assert observed == {
            "visible": True,
            "idle": False,
            "url": "https://www.youtube.com/watch?v=example",
            "focus": True,
        }
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
            and widget.settings_root == Path(context.paths.settings)
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
        window.request_full_exit()
        app.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec", exercise_then_exit)
    try:
        assert run_main_window(context) == 0
    finally:
        context.lifecycle.shutdown()
