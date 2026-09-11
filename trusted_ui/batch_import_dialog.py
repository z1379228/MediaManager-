"""Trusted download inbox for bounded manual, TXT and CSV URL batches."""

from __future__ import annotations

from core.downloads.batch_import import (
    BatchImportEntry,
    BatchImportIssue,
    BatchImportResult,
)


def _source_label(value: object) -> str:
    text = " ".join(str(value or "").split())
    if any(ord(character) < 32 for character in text):
        return "匯入清單"
    return text[:80] or "匯入清單"


def show_batch_import_dialog(
    result: BatchImportResult,
    parent: object = None,
    *,
    source_label: object = "TXT / CSV",
) -> tuple[BatchImportEntry, ...] | None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QDialogButtonBox,
        QFrame,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    from trusted_ui.table_refresh import limit_resize_contents_work
    from trusted_ui.theme import COLORS

    dialog = QDialog(parent)
    dialog.setWindowTitle("下載收件匣")
    dialog.setAccessibleName("MediaManager 下載收件匣")
    dialog.resize(980, 640)
    dialog.setMinimumSize(860, 560)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(22, 20, 22, 18)
    page.setSpacing(12)

    heading_row = QHBoxLayout()
    heading = QLabel("下載收件匣")
    heading.setObjectName("sectionTitle")
    heading_row.addWidget(heading)
    heading_row.addStretch()
    source = QLabel(_source_label(source_label))
    source.setObjectName("downloadInboxSource")
    source.setAccessibleName("收件匣來源")
    heading_row.addWidget(source)
    page.addLayout(heading_row)

    intro = QLabel("先檢查網址與來源；只有勾選的有效項目會進入最後下載確認。")
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary_card = QFrame()
    summary_card.setObjectName("downloadInboxSummaryCard")
    summary_layout = QHBoxLayout(summary_card)
    summary_layout.setContentsMargins(12, 9, 12, 9)
    summary = QLabel()
    summary.setObjectName("downloadInboxSummary")
    summary.setAccessibleName("收件匣檢查摘要")
    summary_layout.addWidget(summary)
    summary_layout.addStretch()
    page.addWidget(summary_card)

    tools = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("篩選網址、標題或作者")
    search.setAccessibleName("篩選下載收件匣")
    search.setClearButtonEnabled(True)
    select_visible = QPushButton("全選有效項目")
    select_visible.setObjectName("batchImportSelectAll")
    select_visible.setAccessibleName("全選收件匣有效項目")
    clear_visible = QPushButton("全部取消")
    clear_visible.setObjectName("batchImportClearAll")
    clear_visible.setAccessibleName("取消選取所有收件匣項目")
    tools.addWidget(search, 1)
    tools.addWidget(select_visible)
    tools.addWidget(clear_visible)
    page.addLayout(tools)

    table = QTableWidget(0, 5)
    table.setObjectName("downloadInboxTable")
    table.setAccessibleName("下載收件匣項目")
    table.setHorizontalHeaderLabels(("選取", "列", "標題 / 作者", "網址", "狀態"))
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.horizontalHeader().setStretchLastSection(False)
    limit_resize_contents_work(table.horizontalHeader())
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(0, 58)
    table.setColumnWidth(1, 48)
    table.setColumnWidth(4, 210)
    page.addWidget(table, 1)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
    )
    confirm_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    confirm_button.setText("確認並加入佇列")
    confirm_button.setObjectName("primary")
    confirm_button.setAccessibleName("確認收件匣並加入下載佇列")
    cancel_button.setText("取消")
    cancel_button.setObjectName("ghost")

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
            f"有效 {len(result.entries)} 項  ·  已選 {selected} 項  ·  "
            f"略過 {len(result.issues)} 項  ·  上限 500 項"
        )
        confirm_button.setEnabled(selected > 0)

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
            status = QTableWidgetItem("✓ 可加入")
            status.setForeground(QColor(COLORS["success"]))
            values = (
                selected,
                QTableWidgetItem(str(entry.row_number)),
                QTableWidgetItem(metadata or "—"),
                QTableWidgetItem(entry.url),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 42)
        for offset, issue in enumerate(visible_issues, start=len(visible_entries)):
            unavailable = QTableWidgetItem()
            unavailable.setFlags(Qt.ItemFlag.NoItemFlags)
            status = QTableWidgetItem(f"! {issue.reason}")
            status.setForeground(QColor(COLORS["danger"]))
            values = (
                unavailable,
                QTableWidgetItem(str(issue.row_number)),
                QTableWidgetItem("—"),
                QTableWidgetItem(issue.value or "—"),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(offset, column, item)
            table.setRowHeight(offset, 42)
        table.blockSignals(False)
        update_summary()

    def set_all(selected: bool) -> None:
        if selected:
            checked.update(entry.row_number for entry in result.entries)
        else:
            checked.clear()
        populate()

    search.textChanged.connect(populate)
    table.itemChanged.connect(checkbox_changed)
    select_visible.clicked.connect(lambda: set_all(True))
    clear_visible.clicked.connect(lambda: set_all(False))
    populate()

    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    page.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return tuple(
        entry for entry in result.entries if entry.row_number in checked
    )
