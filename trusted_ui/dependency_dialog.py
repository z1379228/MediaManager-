"""Trusted UI for local dependency health."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.dependency_health import DependencyReport, check_dependencies


def dependency_presentation(report: DependencyReport) -> tuple[str, str, str]:
    count = f"{report.ready_count}/{report.total_count}"
    if report.youtube_ready:
        return f"環境 {count}", "ready", "YouTube 完整支援所需元件均可用"
    return f"環境 {count}", "warning", f"有 {report.issue_count} 個元件需要處理"


def startup_dependency_prompt_required(report: DependencyReport) -> bool:
    """Return whether startup should surface dependency remediation."""

    return not report.youtube_ready


def create_dependency_dialog(
    application_root: Path,
    parent: object = None,
    *,
    report_factory: Callable[[Path], DependencyReport] = check_dependencies,
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
    dialog.resize(850, 480)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(20, 18, 20, 16)
    page.setSpacing(12)

    title = QLabel("YouTube 與媒體處理環境")
    title.setObjectName("sectionTitle")
    page.addWidget(title)
    intro = QLabel(
        "正式資料夾版會攜帶必要元件，不需要額外硬體驅動。"
        "若此處顯示缺少，下載與安裝都需要使用者明確確認；"
        "核心媒體庫仍可繼續使用。"
    )
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary = QLabel()
    summary.setObjectName("dependencySummary")
    page.addWidget(summary)

    table = QTableWidget(0, 4)
    table.setHorizontalHeaderLabels(("元件", "狀態", "版本 / 位置", "用途與影響"))
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setStretchLastSection(True)
    table.setColumnWidth(0, 145)
    table.setColumnWidth(1, 76)
    table.setColumnWidth(2, 235)
    page.addWidget(table, 1)

    controls = QHBoxLayout()
    install_help = QPushButton("安裝／修復方式…")
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
        help_dialog.setWindowTitle("安裝與修復方式")
        help_dialog.resize(720, 520)
        layout = QVBoxLayout(help_dialog)
        guidance = QTextBrowser()
        guidance.setOpenExternalLinks(True)
        guidance.setHtml(
            "<h2>不需要額外驅動程式</h2>"
            "<p>MediaManager 需要的是執行元件，不是顯示卡或音效卡驅動。</p>"
            "<h3>正式資料夾版（建議）</h3>"
            "<p>請重新取得並完整解壓 <b>Version/&lt;版本&gt;</b> 資料夾，"
            "不要只複製 MediaManager.exe。這能保留經 SHA-256 驗證的 "
            "Deno、FFmpeg 與 ffprobe，也不會改寫已簽章版本。</p>"
            "<h3>開發環境</h3>"
            "<p>在專案根目錄的 PowerShell 執行：</p>"
            "<pre>.\\.venv\\Scripts\\python.exe -m pip install -e .</pre>"
            "<p>系統工具可使用 Windows Package Manager 安裝：</p>"
            "<pre>winget install --id DenoLand.Deno -e\n"
            "winget install --id Gyan.FFmpeg -e</pre>"
            "<p>安裝後按「重新檢查」；若開啟中的程式尚未取得新 PATH，"
            "請關閉後重新啟動。</p>"
            '<p><a href="https://docs.deno.com/runtime/getting_started/installation/">'
            "Deno 官方安裝說明</a><br>"
            '<a href="https://www.gyan.dev/ffmpeg/builds/">FFmpeg Windows 建置頁</a></p>'
        )
        layout.addWidget(guidance)
        dismiss = QPushButton("關閉")
        dismiss.clicked.connect(help_dialog.accept)
        layout.addWidget(dismiss, alignment=Qt.AlignmentFlag.AlignRight)
        help_dialog.exec()

    install_help.clicked.connect(show_install_help)

    def populate() -> None:
        report = report_factory(application_root)
        summary.setText(
            (
                f"完整支援已就緒 · {report.ready_count}/{report.total_count}"
                if report.youtube_ready
                else f"目前可用 {report.ready_count}/{report.total_count} · "
                "缺少元件時仍可使用不依賴該元件的功能"
            )
        )
        summary.setProperty(
            "dependencyState", "ready" if report.youtube_ready else "warning"
        )
        summary.style().unpolish(summary)
        summary.style().polish(summary)
        table.setRowCount(len(report.statuses))
        for row, status in enumerate(report.statuses):
            state = QTableWidgetItem("可用" if status.available else "待處理")
            version_path = "\n".join(
                value for value in (status.version, status.path) if value
            ) or "未偵測到"
            values = (
                QTableWidgetItem(status.label),
                state,
                QTableWidgetItem(version_path),
                QTableWidgetItem(status.detail),
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 58)

    refresh.clicked.connect(populate)
    populate()
    return dialog


def show_dependency_dialog(application_root: Path, parent: object) -> None:
    create_dependency_dialog(application_root, parent).exec()
