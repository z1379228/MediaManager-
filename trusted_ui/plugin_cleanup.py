"""Trusted UI flow for permanently deleting removed plugins or backups."""

from __future__ import annotations


def choose_and_purge_plugin(context: object, parent: object, plugin_id: str) -> bool:
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    record = context.plugin_registry.get(plugin_id)
    if record is None:
        QMessageBox.information(parent, "永久清理", "找不到插件紀錄。")
        return False

    choices: list[str] = []
    purge_removed = record.pending_action == "REMOVE"
    if purge_removed:
        choices.append("永久刪除已移除插件及其全部備份")
    versions = context.plugin_rollback.list_versions(plugin_id)
    choices.extend(f"永久刪除備份版本 {version}" for version in versions)
    if not choices:
        QMessageBox.information(parent, "永久清理", "沒有可清理的項目。")
        return False

    choice, accepted = QInputDialog.getItem(
        parent, "永久清理", f"選擇要清理的項目：\n{plugin_id}", choices, 0, False
    )
    if not accepted:
        return False
    answer = QMessageBox.warning(
        parent,
        "確認永久清理",
        f"{plugin_id}\n{choice}\n\n此操作無法復原。確定要繼續嗎？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer is not QMessageBox.StandardButton.Yes:
        return False

    if purge_removed and choice == choices[0]:
        result = context.plugin_cleanup.purge_removed_plugin(plugin_id)
        event = "plugin.purged"
        details = {"plugin_id": plugin_id, "version": record.installed_version}
    else:
        version = choice.removeprefix("永久刪除備份版本 ")
        result = context.plugin_cleanup.purge_backup(plugin_id, version)
        event = "plugin.backup_purged"
        details = {"plugin_id": plugin_id, "version": version}
    if not result.purged:
        QMessageBox.critical(parent, "永久清理失敗", "\n".join(result.errors))
        return False
    context.audit.write(event, **details, warnings=result.warnings)
    if result.warnings:
        QMessageBox.warning(parent, "清理尚待完成", "\n".join(result.warnings))
    else:
        QMessageBox.information(parent, "永久清理完成", choice)
    return True
