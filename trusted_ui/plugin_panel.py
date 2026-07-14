"""Installed-plugin management panel for the trusted UI."""

from __future__ import annotations

from trusted_ui.plugin_cleanup import choose_and_purge_plugin
from trusted_ui.plugin_installer import choose_and_install_plugin
from trusted_ui.plugin_rollback import choose_and_rollback_plugin
from trusted_ui.plugin_updater import choose_and_update_plugin


def create_plugin_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class PluginPanel(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            layout = QVBoxLayout(self)
            self.empty = QLabel(
                "尚未安裝外部 MOD。可使用「安裝 .modpkg」加入已簽章套件；"
                "在目前 SAFE_MODE 下，外部可執行 MOD 仍不能啟用。"
            )
            self.empty.setObjectName("sectionSubtitle")
            self.empty.setWordWrap(True)
            layout.addWidget(self.empty)
            self.table = QTableWidget(0, 4)
            self.table.setHorizontalHeaderLabels(["插件 ID", "版本", "發布者", "狀態"])
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch
            )
            layout.addWidget(self.table)
            actions = QHBoxLayout()
            for label, callback in (
                ("安裝 .modpkg", self.install),
                ("更新 .modpkg", self.update),
                ("回復版本", self.rollback),
                ("啟用 / 停用", self.toggle),
                ("移除 / 還原", self.maintain),
                ("永久清理", self.cleanup),
            ):
                button = QPushButton(label)
                button.clicked.connect(callback)
                actions.addWidget(button)
            actions.addStretch()
            refresh = QPushButton("重新整理")
            refresh.clicked.connect(self.refresh)
            actions.addWidget(refresh)
            layout.addLayout(actions)
            self.refresh()

        def refresh(self) -> None:
            records = context.plugin_registry.list_all()
            self.empty.setVisible(not records)
            self.table.setRowCount(len(records))
            for row, record in enumerate(records):
                identifier = QTableWidgetItem(record.plugin_id)
                identifier.setData(Qt.ItemDataRole.UserRole, record.plugin_id)
                self.table.setItem(row, 0, identifier)
                self.table.setItem(row, 1, QTableWidgetItem(record.installed_version))
                self.table.setItem(row, 2, QTableWidgetItem(record.publisher_id))
                if record.pending_action == "REMOVE":
                    status = "已移除（可還原）"
                else:
                    status = "已啟用" if record.enabled else "已停用"
                self.table.setItem(row, 3, QTableWidgetItem(status))

        def selected_id(self) -> str | None:
            row = self.table.currentRow()
            item = self.table.item(row, 0) if row >= 0 else None
            return item.data(Qt.ItemDataRole.UserRole) if item else None

        def selected_record(self) -> object | None:
            plugin_id = self.selected_id()
            return context.plugin_registry.get(plugin_id) if plugin_id else None

        def install(self) -> None:
            if choose_and_install_plugin(context, self):
                self.refresh()

        def update(self) -> None:
            self._run_selected("插件更新", choose_and_update_plugin)

        def rollback(self) -> None:
            self._run_selected("回復版本", choose_and_rollback_plugin)

        def cleanup(self) -> None:
            self._run_selected("永久清理", choose_and_purge_plugin)

        def _run_selected(self, title: str, operation: object) -> None:
            plugin_id = self.selected_id()
            if not plugin_id:
                QMessageBox.information(self, title, "請先選擇插件。")
                return
            if operation(context, self, plugin_id):
                self.refresh()

        def toggle(self) -> None:
            record = self.selected_record()
            if record is None:
                QMessageBox.information(self, "插件狀態", "請先選擇插件。")
                return
            if record.pending_action == "REMOVE":
                QMessageBox.information(self, "插件狀態", "請先還原插件再變更狀態。")
                return
            result = context.plugin_manager.set_enabled(
                record.plugin_id, not record.enabled, context.security.mode
            )
            if not result.successful:
                QMessageBox.critical(self, "無法變更插件狀態", "\n".join(result.errors))
                return
            context.audit.write(
                "plugin.enabled_changed",
                plugin_id=record.plugin_id,
                enabled=not record.enabled,
            )
            self.refresh()

        def maintain(self) -> None:
            record = self.selected_record()
            if record is None:
                QMessageBox.information(self, "插件維護", "請先選擇插件。")
                return
            restoring = record.pending_action == "REMOVE"
            action = "還原" if restoring else "移除"
            detail = (
                "插件將回到已安裝區，但仍保持停用。"
                if restoring
                else "插件將移至隔離區並保持可還原，不會永久刪除。"
            )
            answer = QMessageBox.question(
                self,
                f"確認{action}插件",
                f"{action} {record.plugin_id} {record.installed_version}？\n\n{detail}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer is not QMessageBox.StandardButton.Yes:
                return
            operation = (
                context.plugin_maintenance.restore
                if restoring
                else context.plugin_maintenance.remove
            )
            result = operation(record.plugin_id, context.security.mode)
            if not result.successful:
                QMessageBox.critical(self, f"無法{action}插件", "\n".join(result.errors))
                return
            context.audit.write(
                "plugin.restored" if restoring else "plugin.removed",
                plugin_id=record.plugin_id,
                version=record.installed_version,
            )
            self.refresh()

    return PluginPanel()
