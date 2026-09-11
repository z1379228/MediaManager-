from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

from trusted_ui.workspace_navigation import (
    install_workspace_navigation,
    workspace_group,
)


def test_workspace_groups_are_shallow_and_stable() -> None:
    assert workspace_group("youtube") == "下載"
    assert workspace_group("library") == "搜尋與媒體"
    assert workspace_group("media-convert") == "工具"
    assert workspace_group("automation") == "自動化"
    assert workspace_group("instagram") == "官方工具"
    assert workspace_group("future-mod") == "其他"


def test_workspace_navigation_lists_tabs_by_group_and_switches() -> None:
    app = QApplication.instance() or QApplication([])
    tabs = QTabWidget()
    entries = (
        ("youtube", "YouTube 下載工作區"),
        ("library", "本機媒體庫"),
        ("media-convert", "格式工廠"),
        ("automation", "Automation"),
        ("instagram", "Instagram 官方工具"),
    )
    panels = {}
    for workspace_id, label in entries:
        panel = QWidget()
        panel.setProperty("workspaceId", workspace_id)
        panels[workspace_id] = panel
        tabs.addTab(panel, label)

    navigator = install_workspace_navigation(tabs)
    menu = navigator.menu()
    assert menu is not None
    menu.aboutToShow.emit()

    groups = {action.text(): action.menu() for action in menu.actions()}
    assert tuple(groups) == (
        "下載",
        "搜尋與媒體",
        "工具",
        "自動化",
        "官方工具",
    )
    tool_action = groups["工具"].actions()[0]
    assert tool_action.text() == "格式工廠"
    assert tool_action.isCheckable()

    tool_action.trigger()
    app.processEvents()
    assert tabs.currentWidget() is panels["media-convert"]
    tabs.deleteLater()
    app.processEvents()


def test_workspace_navigation_keeps_unknown_tabs_reachable() -> None:
    app = QApplication.instance() or QApplication([])
    tabs = QTabWidget()
    panel = QWidget()
    panel.setProperty("workspaceId", "third-party-example")
    tabs.addTab(panel, "第三方工作區")

    navigator = install_workspace_navigation(tabs)
    menu = navigator.menu()
    assert menu is not None
    menu.aboutToShow.emit()

    assert [action.text() for action in menu.actions()] == ["其他"]
    assert [action.text() for action in menu.actions()[0].menu().actions()] == [
        "第三方工作區"
    ]
    tabs.deleteLater()
    app.processEvents()
