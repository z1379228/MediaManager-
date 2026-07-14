"""Trusted preview dialog for bounded TXT/CSV batch imports."""

from __future__ import annotations

from core.downloads.batch_import import (
    BatchImportEntry,
    BatchImportIssue,
    BatchImportResult,
)


def show_batch_import_dialog(
    result: BatchImportResult, parent: object = None
) -> tuple[BatchImportEntry, ...] | None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QDialogButtonBox,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    from trusted_ui.theme import COLORS

    dialog = QDialog(parent)
    dialog.setWindowTitle("批量匯入預覽")
    dialog.resize(980, 620)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(18, 16, 18, 14)
    page.setSpacing(10)

    heading = QLabel("確認 TXT / CSV 匯入內容")
    heading.setObjectName("sectionTitle")
    page.addWidget(heading)
    summary = QLabel()
    summary.setObjectName("sectionSubtitle")
    page.addWidget(summary)

    tools = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("篩選網址、標題或作者")
    search.setClearButtonEnabled(True)
    select_visible = QPushButton("選取顯示項目")
    clear_visible = QPushButton("清除顯示項目")
    tools.addWidget(search, 1)
    tools.addWidget(select_visible)
    tools.addWidget(clear_visible)
    page.addLayout(tools)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("選取", "列", "網址", "標題 / 作者", "檢查結果"))
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(0, 58)
    table.setColumnWidth(1, 48)
    table.setColumnWidth(4, 190)
    page.addWidget(table, 1)

    checked: set[int] = {entry.row_number for entry in result.entries}
    visible_entries: tuple[BatchImportEntry, ...] = result.entries

    def matches(value: BatchImportEntry | BatchImportIssue) -> bool:
        query = " ".join(search.text().split()).casefold()
        if not query:
            return True
        if isinstance(value, BatchImportEntry):
            text = f"{value.url} {value.title} {value.artist}"
        else:
            text = f"{value.value} {value.reason}"
        return query in text.casefold()

    def update_summary() -> None:
        selected = sum(entry.row_number in checked for entry in result.entries)
        summary.setText(
            f"有效 {len(result.entries)} 項，已選 {selected} 項；"
            f"略過 {len(result.issues)} 項。最多接受 500 列。"
        )

    def checkbox_changed(item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry, BatchImportEntry):
            return
        if item.checkState() == Qt.CheckState.Checked:
            checked.add(entry.row_number)
        else:
            checked.discard(entry.row_number)
        update_summary()

    def populate() -> None:
        nonlocal visible_entries
        visible_entries = tuple(entry for entry in result.entries if matches(entry))
        visible_issues = tuple(issue for issue in result.issues if matches(issue))
        table.blockSignals(True)
        table.setRowCount(len(visible_entries) + len(visible_issues))
        for row, entry in enumerate(visible_entries):
            selected = QTableWidgetItem()
            selected.setData(Qt.ItemDataRole.UserRole, entry)
            selected.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            selected.setCheckState(
                Qt.CheckState.Checked
                if entry.row_number in checked
                else Qt.CheckState.Unchecked
            )
            metadata = entry.title
            if entry.artist:
                metadata = f"{metadata} / {entry.artist}" if metadata else entry.artist
            status = QTableWidgetItem("可加入")
            status.setForeground(QColor(COLORS["success"]))
            values = (
                selected,
                QTableWidgetItem(str(entry.row_number)),
                QTableWidgetItem(entry.url),
                QTableWidgetItem(metadata or "—"),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 42)
        for offset, issue in enumerate(visible_issues, start=len(visible_entries)):
            unavailable = QTableWidgetItem()
            unavailable.setFlags(Qt.ItemFlag.NoItemFlags)
            status = QTableWidgetItem(issue.reason)
            status.setForeground(QColor(COLORS["danger"]))
            values = (
                unavailable,
                QTableWidgetItem(str(issue.row_number)),
                QTableWidgetItem(issue.value or "—"),
                QTableWidgetItem("—"),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(offset, column, item)
            table.setRowHeight(offset, 42)
        table.blockSignals(False)
        update_summary()

    def set_visible(selected: bool) -> None:
        for entry in visible_entries:
            if selected:
                checked.add(entry.row_number)
            else:
                checked.discard(entry.row_number)
        populate()

    search.textChanged.connect(populate)
    table.itemChanged.connect(checkbox_changed)
    select_visible.clicked.connect(lambda: set_visible(True))
    clear_visible.clicked.connect(lambda: set_visible(False))
    populate()

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText("加入下載佇列")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    page.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return tuple(
        entry for entry in result.entries if entry.row_number in checked
    )
