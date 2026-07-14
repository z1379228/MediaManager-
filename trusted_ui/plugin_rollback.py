"""Trusted UI flow for selecting and rolling back a plugin version."""

from __future__ import annotations


def choose_and_rollback_plugin(context: object, parent: object, plugin_id: str) -> bool:
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    record = context.plugin_registry.get(plugin_id)
    if record is None or record.pending_action != "NONE":
        QMessageBox.information(parent, "版本回滾", "此插件目前無法回滾。")
        return False
    versions = context.plugin_rollback.list_versions(plugin_id)
    if not versions:
        QMessageBox.information(parent, "版本回滾", "目前沒有可用的備份版本。")
        return False
    version, accepted = QInputDialog.getItem(
        parent,
        "選擇回滾版本",
        f"目前版本：{record.installed_version}\n回滾至：",
        versions,
        0,
        False,
    )
    if not accepted:
        return False
    answer = QMessageBox.warning(
        parent,
        "確認版本回滾",
        f"{plugin_id}\n{record.installed_version} → {version}\n\n"
        "目前版本會移入 backups；回滾後插件維持停用。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer is not QMessageBox.StandardButton.Yes:
        return False
    result = context.plugin_rollback.rollback(
        plugin_id,
        version,
        context.security.mode,
    )
    if not result.rolled_back:
        QMessageBox.critical(parent, "版本回滾失敗", "\n".join(result.errors))
        return False
    context.audit.write(
        "plugin.rolled_back",
        plugin_id=plugin_id,
        previous_version=result.previous_version,
        version=result.version,
    )
    QMessageBox.information(
        parent,
        "版本回滾完成",
        f"{plugin_id} 已回滾至 {result.version}，目前為停用狀態。",
    )
    return True
