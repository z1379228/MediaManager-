"""Trusted UI for local dependency health."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.dependency_health import DependencyReport, check_dependencies
from core.dependency_snapshot import DependencySnapshotService


def dependency_presentation(report: DependencyReport) -> tuple[str, str, str]:
    core_total = len(report.core_statuses)
    optional_total = len(report.optional_statuses)
    label = f"核心 {report.core_ready_count}/{core_total}"
    if optional_total:
        label += f"｜選用 {report.optional_ready_count}/{optional_total}"
    if report.youtube_ready:
        return (
            label,
            "ready",
            "核心下載環境已就緒；MEGAcmd、whisper-cli 與語音模型依使用的 MOD 選裝。",
        )
    missing = core_total - report.core_ready_count
    return label, "warning", f"缺少 {missing} 項核心依賴，請開啟環境檢查。"


def startup_dependency_prompt_required(report: DependencyReport) -> bool:
    """Only startup-critical tools may trigger the remediation prompt."""

    return not report.youtube_ready


def create_dependency_dialog(
    application_root: Path,
    parent: object = None,
    *,
    report_factory: Callable[[Path], DependencyReport] = check_dependencies,
    snapshot_service: DependencySnapshotService | None = None,
) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextBrowser,
        QVBoxLayout,
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle("執行環境")
    dialog.resize(860, 520)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(20, 18, 20, 16)
    page.setSpacing(12)

    title = QLabel("核心工具與選用 MOD 依賴")
    title.setObjectName("sectionTitle")
    page.addWidget(title)
    intro = QLabel(
        "核心項目影響 YouTube 搜尋、解析與下載；選用項目只影響 MEGA 或 "
        "Speech to Text。選用項目未安裝時，不代表 MediaManager 核心故障。"
    )
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary = QLabel()
    summary.setObjectName("dependencySummary")
    page.addWidget(summary)

    table = QTableWidget(0, 5)
    table.setObjectName("dependencyTable")
    table.setHorizontalHeaderLabels(("類別", "工具", "狀態", "版本／路徑", "說明"))
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setStretchLastSection(True)
    table.setColumnWidth(0, 70)
    table.setColumnWidth(1, 145)
    table.setColumnWidth(2, 76)
    table.setColumnWidth(3, 240)
    page.addWidget(table, 1)

    controls = QHBoxLayout()
    install_help = QPushButton("一鍵安裝與選用工具說明")
    controls.addWidget(install_help)
    controls.addStretch()
    refresh = QPushButton("重新檢查")
    close = QPushButton("關閉")
    close.clicked.connect(dialog.accept)
    controls.addWidget(refresh)
    controls.addWidget(close)
    page.addLayout(controls)

    def show_install_help() -> None:
        help_dialog = QDialog(dialog)
        help_dialog.setWindowTitle("安裝執行環境")
        help_dialog.resize(720, 500)
        layout = QVBoxLayout(help_dialog)
        guidance = QTextBrowser()
        guidance.setOpenExternalLinks(True)
        guidance.setHtml(
            "<h2>一鍵補齊核心外部工具</h2>"
            "<p>關閉 MediaManager 後，在程式資料夾執行 "
            "<b>安裝必備軟體.bat</b>。批次檔會透過 winget 安裝缺少的 "
            "FFmpeg、ffprobe 與 Deno；完成後重新啟動程式。</p>"
            "<h3>選用 MOD 依賴</h3>"
            "<p><b>MEGA：</b>需要官方 MEGAcmd 的 mega-get。未安裝時仍能辨識 "
            "MEGA 公開網址，但下載保持關閉。</p>"
            "<p><b>Speech to Text：</b>需要 whisper.cpp 的 whisper-cli，並由使用者 "
            "自行匯入本機 GGML／GGUF 語音模型。模型不會自動下載。</p>"
            "<p>選用工具不影響 YouTube、Bilibili 與一般媒體工作區。</p>"
        )
        layout.addWidget(guidance)
        dismiss = QPushButton("關閉")
        dismiss.clicked.connect(help_dialog.accept)
        layout.addWidget(dismiss, alignment=Qt.AlignmentFlag.AlignRight)
        help_dialog.exec()

    install_help.clicked.connect(show_install_help)

    def populate(*, force: bool = False) -> None:
        report = (
            snapshot_service.refresh().report
            if snapshot_service is not None and force
            else snapshot_service.snapshot().report
            if snapshot_service is not None
            else report_factory(application_root)
        )
        label, state, tip = dependency_presentation(report)
        summary.setText(f"{label}　{tip}")
        summary.setProperty("dependencyState", state)
        summary.style().unpolish(summary)
        summary.style().polish(summary)
        core_ids = {status.dependency_id for status in report.core_statuses}
        table.setRowCount(len(report.statuses))
        for row, status in enumerate(report.statuses):
            version_path = "\n".join(
                value for value in (status.version, status.path) if value
            ) or "尚未偵測到"
            values = (
                QTableWidgetItem("核心" if status.dependency_id in core_ids else "選用"),
                QTableWidgetItem(status.label),
                QTableWidgetItem("可用" if status.available else "待處理"),
                QTableWidgetItem(version_path),
                QTableWidgetItem(status.detail),
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 58)

    refresh.clicked.connect(lambda: populate(force=True))
    populate()
    return dialog


def show_dependency_dialog(
    application_root: Path,
    parent: object,
    *,
    snapshot_service: DependencySnapshotService | None = None,
) -> None:
    create_dependency_dialog(
        application_root,
        parent,
        snapshot_service=snapshot_service,
    ).exec()
