"""Trusted-publisher management panel for the trusted UI."""

from __future__ import annotations

from core.security.publisher_manager import public_key_fingerprint


def create_publisher_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class PublisherPanel(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            layout = QVBoxLayout(self)
            self.table = QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(["發布者 ID", "公鑰指紋", "狀態"])
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch
            )
            layout.addWidget(self.table)
            actions = QHBoxLayout()
            add = QPushButton("加入發布者")
            add.clicked.connect(self.add)
            toggle = QPushButton("啟用／停用信任")
            toggle.clicked.connect(self.toggle)
            actions.addWidget(add)
            actions.addWidget(toggle)
            actions.addStretch()
            layout.addLayout(actions)
            self.refresh()

        def refresh(self) -> None:
            publishers = context.trust_store.list_all()
            self.table.setRowCount(len(publishers))
            for row, publisher in enumerate(publishers):
                identifier = QTableWidgetItem(publisher.publisher_id)
                identifier.setData(Qt.ItemDataRole.UserRole, publisher.publisher_id)
                self.table.setItem(row, 0, identifier)
                self.table.setItem(
                    row,
                    1,
                    QTableWidgetItem(public_key_fingerprint(publisher.public_key)),
                )
                self.table.setItem(
                    row,
                    2,
                    QTableWidgetItem("已信任" if publisher.enabled else "已停用"),
                )

        def selected_id(self) -> str | None:
            row = self.table.currentRow()
            item = self.table.item(row, 0) if row >= 0 else None
            return item.data(Qt.ItemDataRole.UserRole) if item else None

        def add(self) -> None:
            publisher_id, accepted = QInputDialog.getText(
                self, "加入發布者", "發布者 ID："
            )
            if not accepted or not publisher_id.strip():
                return
            public_key, accepted = QInputDialog.getMultiLineText(
                self,
                "Ed25519 公鑰",
                "貼上 Base64 公鑰（可含 ed25519: 前綴）：",
            )
            if not accepted or not public_key.strip():
                return
            fingerprint = public_key_fingerprint(public_key.strip())
            answer = QMessageBox.warning(
                self,
                "確認信任發布者",
                f"發布者：{publisher_id.strip()}\n公鑰指紋：{fingerprint}\n\n"
                "請透過可靠管道核對以上資料。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer is not QMessageBox.StandardButton.Yes:
                return
            result = context.publisher_manager.add(
                publisher_id.strip(),
                public_key.strip(),
                context.security.mode,
            )
            if not result.successful or result.publisher is None:
                QMessageBox.critical(self, "無法加入發布者", "\n".join(result.errors))
                return
            context.audit.write(
                "publisher.trusted",
                publisher_id=result.publisher.publisher_id,
                fingerprint=fingerprint,
            )
            self.refresh()

        def toggle(self) -> None:
            publisher_id = self.selected_id()
            publishers = {
                item.publisher_id: item for item in context.trust_store.list_all()
            }
            publisher = publishers.get(publisher_id)
            if publisher is None:
                QMessageBox.information(self, "發布者管理", "請先選擇發布者。")
                return
            result = context.publisher_manager.set_enabled(
                publisher.publisher_id,
                not publisher.enabled,
                context.security.mode,
            )
            if not result.successful:
                QMessageBox.critical(
                    self,
                    "無法更新發布者信任",
                    "\n".join(result.errors),
                )
                return
            context.audit.write(
                "publisher.enabled_changed",
                publisher_id=publisher.publisher_id,
                enabled=not publisher.enabled,
            )
            self.refresh()

    return PublisherPanel()
