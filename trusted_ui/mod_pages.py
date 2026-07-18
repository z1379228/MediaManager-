"""Renderer for safe, declarative MOD pages inside plugin management."""

from __future__ import annotations

from pathlib import Path

from core.localization import CORE_LOCALES
from core.settings import SettingsService, SettingsWriteBlockedError


def create_mod_pages_panel(context: object, parent: object = None) -> object:
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    controls = QHBoxLayout()
    locale_caption = QLabel("核心介面語言")
    locale_caption.setObjectName("modPageLocaleCaption")
    controls.addWidget(locale_caption)
    locale_selector = QComboBox()
    locale_selector.setObjectName("modPageLocaleSelector")
    locale_selector.setAccessibleName("核心與 MOD 共用介面語言")
    for locale in CORE_LOCALES:
        locale_selector.addItem(locale.display_name, locale.code)
    initial_locale = getattr(context.plugin_ui, "locale", "zh-TW")
    initial_index = locale_selector.findData(initial_locale)
    locale_selector.setCurrentIndex(initial_index if initial_index >= 0 else 0)
    controls.addWidget(locale_selector)
    controls.addStretch()
    refresh = QPushButton("重新整理")
    refresh.setObjectName("modPageRefresh")
    refresh.setAccessibleName("重新整理外部 MOD 介面")
    controls.addWidget(refresh)
    layout.addLayout(controls)
    locale_status = QLabel()
    locale_status.setObjectName("modPageLocaleStatus")
    locale_status.setWordWrap(True)
    layout.addWidget(locale_status)
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
                f"核心目前已保存 {locale_selector.currentText()} 作為共用介面語言；"
                "即使尚無外部 MOD，之後安裝的多語言 MOD 仍會套用此設定。"
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
        locale_selector.setEnabled(True)
        locale_status.setText(
            f"目前選用：{locale_selector.currentText()}。"
            "此設定由可信核心管理並傳給 MOD；尚未完成翻譯的文字不會偽裝成已翻譯。"
        )
        render(selector.currentIndex())

    def apply_locale() -> None:
        locale = str(locale_selector.currentData())
        previous_locale = getattr(context.plugin_ui, "locale", "zh-TW")
        settings = getattr(context, "settings", None)
        settings_root = getattr(getattr(context, "paths", None), "settings", None)
        if settings is not None and isinstance(settings_root, Path):
            try:
                saved = SettingsService(
                    settings_root / "settings.json"
                ).patch(language=locale)
            except OSError as error:
                locale_selector.blockSignals(True)
                try:
                    previous_index = locale_selector.findData(previous_locale)
                    locale_selector.setCurrentIndex(
                        previous_index if previous_index >= 0 else 0
                    )
                finally:
                    locale_selector.blockSignals(False)
                detail = (
                    "設定檔目前受安全保護，語言變更已復原。"
                    if isinstance(error, SettingsWriteBlockedError)
                    else "設定檔目前無法寫入，語言變更已復原。"
                )
                locale_status.setText(detail)
                QMessageBox.warning(
                    panel,
                    "無法儲存介面語言",
                    f"{detail}\n{error}",
                )
                return
            settings.language = saved.language
        context.plugin_ui.locale = locale
        refresh_pages()

    selector.currentIndexChanged.connect(render)
    locale_selector.currentIndexChanged.connect(apply_locale)
    refresh.clicked.connect(refresh_pages)
    panel.refresh_pages = refresh_pages
    refresh_pages()
    return panel
