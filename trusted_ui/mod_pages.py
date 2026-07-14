"""Renderer for safe, declarative MOD pages inside plugin management."""

from __future__ import annotations


def create_mod_pages_panel(context: object, parent: object = None) -> object:
    from PySide6.QtWidgets import (
        QComboBox,
        QLabel,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    selector = QComboBox()
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
    pages = context.plugin_ui.list_pages()
    selector.setVisible(bool(pages))
    for plugin_id, page in pages:
        selector.addItem(f"{page.title} — {plugin_id}", (plugin_id, page))

    def render(index: int) -> None:
        while body_layout.count():
            item = body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        data = selector.itemData(index)
        if data is None:
            heading = QLabel("尚無外部 MOD 介面")
            heading.setObjectName("sectionTitle")
            detail = QLabel(
                "這裡只呈現已安裝、已啟用且驗證通過的外部 MOD ui.json。"
                "內建 YouTube、Bilibili 與其他功能請到「內建 MOD 狀態」管理。"
            )
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

    selector.currentIndexChanged.connect(render)
    render(selector.currentIndex())
    return panel
