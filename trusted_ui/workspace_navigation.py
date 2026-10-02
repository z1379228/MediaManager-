"""Low-overhead categorized navigation for crowded workspace tabs."""

from __future__ import annotations


WORKSPACE_GROUPS = (
    (
        "下載",
        frozenset(
            {
                "youtube",
                "bilibili",
                "facebook",
                "mega",
                "direct-http",
            }
        ),
    ),
    ("搜尋與媒體", frozenset({"search", "library", "podcast-import"})),
    (
        "工具",
        frozenset({"media-convert", "gopeed-transfer", "speech-to-text"}),
    ),
    ("自動化", frozenset({"automation"})),
    ("官方工具", frozenset({"instagram", "threads", "twitter"})),
)
OTHER_WORKSPACE_GROUP = "其他"


def workspace_group(workspace_id: object) -> str:
    """Return a stable shallow group without trusting a third-party label."""

    normalized = workspace_id.strip() if isinstance(workspace_id, str) else ""
    for label, members in WORKSPACE_GROUPS:
        if normalized in members:
            return label
    return OTHER_WORKSPACE_GROUP


def _select_workspace(tabs: object, widget: object) -> None:
    index = tabs.indexOf(widget)
    if index >= 0:
        tabs.setCurrentIndex(index)


def install_workspace_navigation(tabs: object) -> object:
    """Install an on-demand menu while preserving tabs and lazy workspaces."""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMenu, QToolButton

    navigator = QToolButton(tabs)
    navigator.setObjectName("workspaceNavigator")
    navigator.setText("工作區")
    navigator.setAccessibleName("切換工作區")
    navigator.setToolTip("依功能分類顯示所有工作區；既有分頁與快捷鍵仍可使用")
    navigator.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    menu = QMenu(navigator)
    menu.setAccessibleName("全部工作區")
    navigator.setMenu(menu)

    def rebuild_menu() -> None:
        menu.clear()
        # PySide ownership for QMenu.addMenu(str) can release the submenu wrapper
        # after this callback returns. Keep explicit parented references for the
        # lifetime of the rebuilt menu.
        menu.workspace_submenus = []
        grouped: dict[str, list[tuple[object, str, str]]] = {}
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            workspace_id = widget.property("workspaceId")
            if not isinstance(workspace_id, str) or not workspace_id:
                workspace_id = getattr(widget, "site_family", "")
            label = tabs.tabText(index).strip() or str(workspace_id) or "未命名工作區"
            grouped.setdefault(workspace_group(workspace_id), []).append(
                (widget, label, tabs.tabToolTip(index))
            )

        group_order = tuple(label for label, _members in WORKSPACE_GROUPS) + (
            OTHER_WORKSPACE_GROUP,
        )
        current = tabs.currentWidget()
        for group_label in group_order:
            entries = grouped.get(group_label)
            if not entries:
                continue
            submenu = QMenu(group_label, menu)
            menu.addMenu(submenu)
            menu.workspace_submenus.append(submenu)
            submenu.setAccessibleName(f"{group_label}工作區")
            for widget, label, tooltip in entries:
                action = submenu.addAction(label)
                action.setCheckable(True)
                action.setChecked(widget is current)
                if tooltip:
                    action.setToolTip(tooltip)
                action.triggered.connect(
                    lambda _checked=False, target=widget: _select_workspace(
                        tabs,
                        target,
                    )
                )

    menu.aboutToShow.connect(rebuild_menu)
    tabs.setCornerWidget(navigator, Qt.Corner.TopRightCorner)
    return navigator
