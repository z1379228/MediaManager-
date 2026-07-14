"""Trusted UI flow for updating one installed plugin."""

from __future__ import annotations

from pathlib import Path

from core.version import is_newer_plugin_version


def choose_and_update_plugin(context: object, parent: object, plugin_id: str) -> bool:
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    record = context.plugin_registry.get(plugin_id)
    if record is None or record.pending_action != "NONE":
        QMessageBox.information(parent, "插件更新", "此插件目前無法更新。")
        return False
    package, _ = QFileDialog.getOpenFileName(
        parent,
        "選擇插件更新套件",
        str(context.paths.plugin_packages),
        "MediaManager 插件 (*.modpkg)",
    )
    if not package:
        return False
    prepared = context.plugin_installer.prepare(Path(package), context.security.mode)
    manifest = prepared.manifest
    if not prepared.valid or manifest is None:
        QMessageBox.critical(
            parent,
            "更新套件驗證失敗",
            "\n".join(prepared.errors),
        )
        return False
    if manifest.id != record.plugin_id or manifest.publisher != record.publisher_id:
        QMessageBox.critical(parent, "更新套件不符", "插件 ID 或發布者不一致。")
        return False
    if not is_newer_plugin_version(manifest.version, record.installed_version):
        QMessageBox.critical(parent, "更新版本無效", "更新版本必須高於目前版本。")
        return False
    added_permissions = tuple(
        item for item in manifest.permissions if item not in record.approved_permissions
    )
    permission_text = "\n".join(f"• {item}" for item in manifest.permissions)
    permission_text = permission_text or "（不要求額外權限）"
    added_text = "\n".join(f"• {item}" for item in added_permissions)
    added_text = added_text or "（沒有新增權限）"
    answer = QMessageBox.question(
        parent,
        "確認更新插件",
        f"插件：{record.plugin_id}\n"
        f"版本：{record.installed_version} → {manifest.version}\n\n"
        f"更新後權限：\n{permission_text}\n\n新增權限：\n{added_text}\n\n"
        "目前版本會保留在 backups，更新後插件維持停用。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer is not QMessageBox.StandardButton.Yes:
        return False
    result = context.plugin_updater.update(
        Path(package),
        plugin_id,
        approved_permissions=manifest.permissions,
        security_mode=context.security.mode,
    )
    if not result.updated:
        QMessageBox.critical(parent, "插件更新失敗", "\n".join(result.errors))
        return False
    context.audit.write(
        "plugin.updated",
        plugin_id=plugin_id,
        previous_version=result.previous_version,
        version=result.version,
        approved_permissions=manifest.permissions,
    )
    QMessageBox.information(
        parent,
        "插件已更新",
        f"{plugin_id} 已更新至 {result.version}，目前為停用狀態。",
    )
    return True
