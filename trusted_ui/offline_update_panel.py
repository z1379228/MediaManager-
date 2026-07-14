"""Explicit, signed offline update workflow."""

from __future__ import annotations

from pathlib import Path

from core.version import CORE_VERSION


def create_offline_update_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QFileDialog,
        QLabel,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    panel = QWidget(parent)
    page = QVBoxLayout(panel)
    page.setContentsMargins(12, 12, 12, 12)
    page.setSpacing(10)
    intro = QLabel(
        "離線更新包只會在完整簽章、版本範圍與所有 SHA-256 驗證通過後，"
        "交易式建立 Version/<major>.<minor>。目前版本不會被直接覆寫。"
    )
    intro.setWordWrap(True)
    intro.setObjectName("sectionSubtitle")
    page.addWidget(intro)
    status = QLabel(f"目前核心：{CORE_VERSION}")
    status.setObjectName("dependencySummary")
    page.addWidget(status)
    choose = QPushButton("選擇已簽章的 .mmupdate…")
    choose.setObjectName("primary")
    configured = bool(
        context.offline_updates.public_key and context.offline_updates.key_id
    )
    choose.setEnabled(configured)
    if not configured:
        choose.setToolTip("此開發版本未配置正式發行公鑰，因此不可安裝更新包")
        status.setText(
            f"目前核心：{CORE_VERSION} · SAFE_MODE 開發版沒有正式發行公鑰"
        )
    page.addWidget(choose, alignment=Qt.AlignmentFlag.AlignLeft)
    page.addStretch()

    def select_update() -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            panel,
            "選擇離線更新包",
            "",
            "MediaManager 離線更新 (*.mmupdate)",
        )
        if not filename:
            return
        result = context.offline_updates.verify(
            Path(filename), current_version=CORE_VERSION
        )
        if not result.valid or result.manifest is None:
            QMessageBox.warning(
                panel,
                "離線更新驗證失敗",
                "\n".join(result.errors) or "更新包無效",
            )
            return
        manifest = result.manifest
        answer = QMessageBox.question(
            panel,
            "確認安裝離線更新",
            f"目標版本：{manifest.target_version}\n"
            f"檔案數：{len(manifest.files)}\n"
            f"目的資料夾：Version/{manifest.version_folder}\n\n"
            "驗證已通過。安裝後需由新資料夾重新啟動，是否繼續？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            target = context.offline_updates.install(result)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(panel, "離線更新安裝失敗", str(error))
            return
        QMessageBox.information(
            panel,
            "離線更新已安裝",
            f"新版本已建立於：\n{target}\n\n目前程式未被替換，請關閉後執行新版本。",
        )

    choose.clicked.connect(select_update)
    return panel
