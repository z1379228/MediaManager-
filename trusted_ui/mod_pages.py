"""Renderer for safe, declarative MOD pages inside plugin management."""

from __future__ import annotations

from pathlib import Path

from core.settings import SettingsService


def create_mod_pages_panel(context: object, parent: object = None) -> object:
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    controls = QHBoxLayout()
    locale_selector = QComboBox()
    locale_selector.setObjectName("modPageLocaleSelector")
    locale_selector.setAccessibleName("外部 MOD 介面語言")
    for label, locale in (
        ("English", "en"),
        ("日本語", "ja"),
        ("简体中文", "zh-CN"),
        ("繁體中文", "zh-TW"),
    ):
        locale_selector.addItem(label, locale)
    initial_locale = getattr(context.plugin_ui, "locale", "zh-TW")
    initial_index = locale_selector.findData(initial_locale)
    locale_selector.setCurrentIndex(initial_index if initial_index >= 0 else 3)
    controls.addWidget(locale_selector)
    controls.addStretch()
    refresh = QPushButton("重新整理")
    refresh.setObjectName("modPageRefresh")
    refresh.setAccessibleName("重新整理外部 MOD 介面")
    controls.addWidget(refresh)
    layout.addLayout(controls)
    selector = QComboBox()
    selector.setObjectName("modPageSelector")
    selector.setAccessibleName("外部 MOD 介面選擇")
    layout.addWidget(selector)
    scroll = QScrollArea()
    scroll.setObjectName("modPageScroll")
    scroll.setAccessibleName("外部 MOD 介面內容")
    scroll.setWidgetResizable(True)
    body = QWidget()
    body.setObjectName("modPageBody")
    body_layout = QVBoxLayout(body)
    scroll.setWidget(body)
    layout.addWidget(scroll, 1)
    def render(index: int) -> None:
        while body_layout.count():
            item = body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        data = selector.itemData(index)
        if data is None:
            heading = QLabel("尚無外部 MOD 介面")
            heading.setObjectName("sectionTitle")
            detail_text = (
                "這裡只呈現已安裝、已啟用且驗證通過的外部 MOD ui.json。"
                "內建 YouTube、Bilibili 與其他功能請到「內建 MOD 狀態」管理。"
            )
            security = getattr(context, "security", None)
            if str(getattr(security, "mode", "")) != "NORMAL":
                detail_text += (
                    "目前不是 NORMAL 安全模式，外部可執行 MOD 不能啟用；"
                    "這是安全阻擋，不是介面載入失敗。"
                )
            detail = QLabel(detail_text)
            detail.setObjectName("sectionSubtitle")
            detail.setWordWrap(True)
            body_layout.addWidget(heading)
            body_layout.addWidget(detail)
            body_layout.addStretch()
            return
        _, page = data
        for block in page.blocks:
            label = QLabel(block.text)
            label.setWordWrap(True)
            if block.type == "heading":
                font = label.font()
                font.setBold(True)
                font.setPointSize(font.pointSize() + 2)
                label.setFont(font)
            elif block.type == "status":
                label.setObjectName("modStatus")
            body_layout.addWidget(label)
        body_layout.addStretch()

    def refresh_pages() -> None:
        current = selector.currentData()
        previous_plugin = current[0] if current else ""
        locale = str(locale_selector.currentData())
        pages = context.plugin_ui.list_pages(locale=locale)
        selector.blockSignals(True)
        selector.clear()
        selected_index = 0
        for index, (plugin_id, page) in enumerate(pages):
            selector.addItem(f"{page.title} — {plugin_id}", (plugin_id, page))
            if plugin_id == previous_plugin:
                selected_index = index
        selector.setVisible(bool(pages))
        selector.setCurrentIndex(selected_index if pages else -1)
        selector.blockSignals(False)
        locale_selector.setEnabled(any(page.available_locales for _, page in pages))
        render(selector.currentIndex())

    def apply_locale() -> None:
        locale = str(locale_selector.currentData())
        context.plugin_ui.locale = locale
        settings = getattr(context, "settings", None)
        settings_root = getattr(getattr(context, "paths", None), "settings", None)
        if settings is not None and isinstance(settings_root, Path):
            settings.language = locale
            SettingsService(settings_root / "settings.json").save(settings)
        refresh_pages()

    selector.currentIndexChanged.connect(render)
    locale_selector.currentIndexChanged.connect(apply_locale)
    refresh.clicked.connect(refresh_pages)
    panel.refresh_pages = refresh_pages
    refresh_pages()
    return panel
