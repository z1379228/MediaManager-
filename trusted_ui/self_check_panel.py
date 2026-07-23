"""Trusted manual self-check page."""

from __future__ import annotations

from pathlib import Path

from core.logging.redaction import bounded_redacted_text
from core.self_check import (
    SelfCheckItem,
    SelfCheckReport,
    load_provider_smoke_report,
    run_self_check,
    write_self_check_report,
)
from trusted_ui.self_check_probe import collect_ui_self_check_items


def create_self_check_panel(context: object, parent: object = None) -> object:
    from PySide6.QtWidgets import (
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class SelfCheckPanel(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.report: SelfCheckReport | None = None
            self.smoke_item: SelfCheckItem | None = None
            page = QVBoxLayout(self)
            intro = QLabel(
                "手動檢查 MOD 編目、父子狀態、語言、網址路由、目前 UI 按鈕、"
                "依賴快照、安全模式與發行資訊。不連線、不啟動下載器或媒體工具，"
                "也不執行完整測試。"
            )
            intro.setWordWrap(True)
            page.addWidget(intro)
            actions = QHBoxLayout()
            self.run_button = QPushButton("執行自我檢查")
            self.run_button.setObjectName("runSelfCheck")
            self.run_button.clicked.connect(self.run_check)
            actions.addWidget(self.run_button)
            self.export_button = QPushButton("匯出去識別 JSON…")
            self.export_button.setObjectName("exportSelfCheck")
            self.export_button.setEnabled(False)
            self.export_button.clicked.connect(self.export_report)
            actions.addWidget(self.export_button)
            self.import_smoke_button = QPushButton("匯入最近 smoke…")
            self.import_smoke_button.setObjectName("importProviderSmoke")
            self.import_smoke_button.clicked.connect(self.import_smoke_report)
            actions.addWidget(self.import_smoke_button)
            actions.addStretch()
            self.summary = QLabel("尚未執行")
            self.summary.setObjectName("selfCheckSummary")
            actions.addWidget(self.summary)
            page.addLayout(actions)
            self.table = QTableWidget(0, 5)
            self.table.setObjectName("selfCheckResults")
            self.table.setHorizontalHeaderLabels(
                ("狀態", "檢查項目", "摘要", "詳細資訊", "處理代碼")
            )
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setStretchLastSection(True)
            page.addWidget(self.table, 1)

        def run_check(self) -> None:
            ui_items = collect_ui_self_check_items(context, self)
            self.report = run_self_check(
                context,
                ui_items=ui_items,
                smoke_item=self.smoke_item,
            )
            self.table.setRowCount(len(self.report.items))
            state_labels = {"pass": "通過", "warning": "警告", "block": "阻擋"}
            for row, item in enumerate(self.report.items):
                values = (
                    state_labels[item.state],
                    item.check_id,
                    item.summary,
                    item.detail,
                    item.remediation_id or "—",
                )
                for column, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    cell.setToolTip(item.detail)
                    self.table.setItem(row, column, cell)
            self.summary.setText(
                f"通過 {self.report.pass_count} · 警告 {self.report.warning_count} · "
                f"阻擋 {self.report.block_count}"
            )
            self.export_button.setEnabled(True)
            self.table.resizeColumnsToContents()

        def import_smoke_report(self) -> None:
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "匯入最近一次 provider smoke",
                "",
                "JSON (*.json)",
            )
            if not selected:
                return
            self.smoke_item = load_provider_smoke_report(Path(selected))
            self.run_check()

        def export_report(self) -> None:
            if self.report is None:
                return
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "匯出自我檢查",
                "mediamanager-self-check.json",
                "JSON (*.json)",
            )
            if not selected:
                return
            destination = Path(selected)
            try:
                write_self_check_report(destination, self.report)
            except (OSError, ValueError) as error:
                QMessageBox.warning(
                    self,
                    "匯出失敗",
                    bounded_redacted_text(error, max_utf8_bytes=512),
                )
                return
            QMessageBox.information(self, "匯出完成", "自我檢查 JSON 已儲存。")

    return SelfCheckPanel()
