"""Trusted UI flow for inspecting and installing one MOD package."""

from __future__ import annotations

from pathlib import Path


def choose_and_install_plugin(context: object, parent: object) -> bool:
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    package, _ = QFileDialog.getOpenFileName(
        parent,
        "選擇插件套件",
        str(context.paths.plugin_packages),
        "MediaManager 插件 (*.modpkg)",
    )
    if not package:
        return False
    verification = context.plugin_installer.package_verifier.verify(package)
    manifest = verification.manifest
    if not verification.valid or manifest is None:
        QMessageBox.critical(
            parent,
            "插件驗證失敗",
            "\n".join(verification.errors) or "無法讀取插件資訊。",
        )
        return False
    if context.trust_store.get(manifest.publisher) is None:
        QMessageBox.critical(
            parent,
            "發布者不受信任",
            f"請先在「受信任發布者」加入並啟用 {manifest.publisher}。",
        )
        return False
    permissions = "\n".join(f"• {item}" for item in manifest.permissions)
    permissions = permissions or "（不要求額外權限）"
    answer = QMessageBox.question(
        parent,
        "確認安裝插件",
        f"名稱：{manifest.name}\n版本：{manifest.version}\n"
        f"插件 ID：{manifest.id}\n發布者：{manifest.publisher}\n\n"
        f"要求權限：\n{permissions}\n\n"
        "套件簽章會在正式寫入前再次驗證，安裝後預設停用。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer is not QMessageBox.StandardButton.Yes:
        return False
    result = context.plugin_installer.install(
        Path(package),
        approved_permissions=manifest.permissions,
        security_mode=context.security.mode,
    )
    if not result.installed:
        QMessageBox.critical(
            parent,
            "插件安裝失敗",
            "\n".join(result.errors) or "安裝程序未完成。",
        )
        return False
    context.audit.write(
        "plugin.installed",
        plugin_id=manifest.id,
        version=manifest.version,
        publisher_id=manifest.publisher,
        approved_permissions=manifest.permissions,
    )
    QMessageBox.information(
        parent,
        "插件已安裝",
        f"{manifest.name} {manifest.version} 已安裝，目前為停用狀態。",
    )
    return True
