"""Trusted UI for local dependency health."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.dependency_health import DependencyReport, DependencyStatus, check_dependencies
from core.dependency_snapshot import DependencySnapshotService


def dependency_presentation(report: DependencyReport) -> tuple[str, str, str]:
    core_total = len(report.core_statuses)
    optional_total = len(report.optional_statuses)
    label = f"核心 {report.core_ready_count}/{core_total}"
    if optional_total:
        label += f"｜選用 MOD 工具 {report.optional_ready_count}/{optional_total}"
    if report.youtube_ready:
        return (
            label,
            "ready",
            "核心下載環境已就緒；MEGAcmd、whisper-cli 與語音模型依使用的 MOD 選裝。",
        )
    missing = core_total - report.core_ready_count
    return label, "warning", f"缺少 {missing} 項核心依賴，請開啟環境檢查。"


_OPTIONAL_DEPENDENCY_MOD = {
    "mega-get": "MEGA MOD",
    "whisper-cli": "Speech to Text MOD",
    "speech-model": "Speech to Text MOD",
}


def dependency_table_row(
    status: DependencyStatus,
    *,
    is_core: bool,
) -> tuple[str, str, str, str, str]:
    """Return explicit table text without treating an optional miss as a fault."""

    version_path = " · ".join(
        value for value in (status.version, status.path) if value
    ) or "尚未偵測到"
    if is_core:
        state = "可用" if status.available else "缺少（阻擋核心）"
        detail = status.detail
        scope = "核心"
    else:
        state = "可用" if status.available else "未安裝（不影響核心）"
        mod_name = _OPTIONAL_DEPENDENCY_MOD.get(
            status.dependency_id, "對應的選用 MOD"
        )
        detail = f"{mod_name}：{status.detail}"
        scope = "選用 MOD"
    return scope, status.label, state, version_path, detail


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
        QApplication,
        QDialog,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextBrowser,
        QVBoxLayout,
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle("執行環境")
    dialog.resize(980, 560)
    dialog.setMinimumSize(760, 480)
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
    table.setHorizontalHeaderLabels(
        ("需求範圍", "工具", "偵測結果", "完整版本／路徑", "影響範圍與說明")
    )
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setWordWrap(False)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column, width in ((0, 92), (1, 145), (2, 178)):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(column, width)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    page.addWidget(table, 1)

    controls = QHBoxLayout()
    copy_path = QPushButton("複製所選工具路徑")
    copy_path.setEnabled(False)
    controls.addWidget(copy_path)
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

    def selected_path() -> str:
        row = table.currentRow()
        item = table.item(row, 3) if row >= 0 else None
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else ""
        return value if isinstance(value, str) else ""

    def update_copy_state() -> None:
        copy_path.setEnabled(bool(selected_path()))

    def copy_selected_path() -> None:
        path = selected_path()
        if path:
            QApplication.clipboard().setText(path)

    table.itemSelectionChanged.connect(update_copy_state)
    copy_path.clicked.connect(copy_selected_path)

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
            texts = dependency_table_row(
                status,
                is_core=status.dependency_id in core_ids,
            )
            values = tuple(QTableWidgetItem(value) for value in texts)
            values[3].setData(Qt.ItemDataRole.UserRole, status.path)
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 42)
        update_copy_state()

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
