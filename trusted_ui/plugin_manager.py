"""Minimal trusted shell for plugin administration panels."""

from __future__ import annotations

from trusted_ui.builtin_mod_panel import create_builtin_mod_panel
from trusted_ui.mod_pages import create_mod_pages_panel
from trusted_ui.offline_update_panel import create_offline_update_panel
from trusted_ui.plugin_panel import create_plugin_panel
from trusted_ui.publisher_panel import create_publisher_panel
from trusted_ui.site_mod_catalog import create_site_mod_catalog_panel


def show_plugin_manager(context: object, parent: object) -> None:
    create_plugin_manager_dialog(context, parent).exec()


def create_plugin_manager_dialog(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTabWidget, QVBoxLayout

    dialog = QDialog(parent)
    dialog.setWindowTitle("插件管理")
    dialog.resize(980, 600)
    page = QVBoxLayout(dialog)
    intro = QLabel(
        "內建 MOD 可直接管理；外部 MOD 必須先安裝並通過簽章與信任驗證。"
    )
    intro.setWordWrap(True)
    page.addWidget(intro)
    tabs = QTabWidget()
    tabs.setObjectName("pluginManagerTabs")
    tabs.addTab(create_plugin_panel(context, dialog), "外部 MOD")
    tabs.addTab(create_builtin_mod_panel(context, dialog), "內建 MOD 狀態")
    tabs.addTab(create_site_mod_catalog_panel(dialog), "網站 MOD 備選")
    tabs.addTab(create_publisher_panel(context, dialog), "發布者信任")
    tabs.addTab(create_mod_pages_panel(context, dialog), "外部 MOD 介面")
    tabs.addTab(create_offline_update_panel(context, dialog), "離線更新")
    page.addWidget(tabs, 1)
    mod_pages = tabs.widget(4)
    tabs.currentChanged.connect(
        lambda index: mod_pages.refresh_pages()
        if tabs.widget(index) is mod_pages
        else None
    )
    if not context.plugin_registry.list_all():
        tabs.setCurrentIndex(1)
    close = QPushButton("關閉")
    close.clicked.connect(dialog.accept)
    page.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
    return dialog
