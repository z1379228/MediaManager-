"""Trusted playlist selection and filtering dialog."""

from __future__ import annotations

from pathlib import Path

from contracts.playlist_v1 import PlaylistEntryV1
from core.downloads.playlist_transfer import export_playlist_entries


def filtered_playlist_entries(
    entries: tuple[PlaylistEntryV1, ...], query: str
) -> tuple[PlaylistEntryV1, ...]:
    normalized = " ".join(query.split()).casefold()
    if not normalized:
        return entries
    return tuple(
        entry
        for entry in entries
        if normalized in f"{entry.title} {entry.artist}".casefold()
    )


def show_playlist_dialog(
    entries: tuple[PlaylistEntryV1, ...], parent: object = None
) -> tuple[PlaylistEntryV1, ...] | None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    from trusted_ui.theme import COLORS

    dialog = QDialog(parent)
    dialog.setWindowTitle("選擇播放清單項目")
    dialog.resize(940, 620)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(18, 16, 18, 14)
    page.setSpacing(10)

    heading = QLabel("播放清單展開結果")
    heading.setObjectName("sectionTitle")
    page.addWidget(heading)
    summary = QLabel()
    summary.setObjectName("sectionSubtitle")
    page.addWidget(summary)

    tools = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("依標題或作者篩選…")
    search.setClearButtonEnabled(True)
    select_visible = QPushButton("勾選可見項目")
    clear_visible = QPushButton("取消可見項目")
    invert_visible = QPushButton("反選可見項目")
    export_checked = QPushButton("匯出已選 ID")
    tools.addWidget(search, 1)
    tools.addWidget(select_visible)
    tools.addWidget(clear_visible)
    tools.addWidget(invert_visible)
    tools.addWidget(export_checked)
    page.addLayout(tools)

    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(("選取", "#", "標題", "作者", "長度", "狀態"))
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(0, 58)
    table.setColumnWidth(1, 48)
    table.setColumnWidth(3, 180)
    table.setColumnWidth(4, 82)
    table.setColumnWidth(5, 115)
    page.addWidget(table, 1)

    checked: set[str] = {entry.entry_id for entry in entries if entry.available}
    visible_entries: tuple[PlaylistEntryV1, ...] = entries

    def duration_text(duration: float | None) -> str:
        if duration is None:
            return "—"
        total = int(duration)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (
            f"{hours}:{minutes:02d}:{seconds:02d}"
            if hours
            else f"{minutes}:{seconds:02d}"
        )

    def update_summary() -> None:
        available = sum(entry.available for entry in entries)
        selected = sum(
            entry.available and entry.entry_id in checked for entry in entries
        )
        unavailable = len(entries) - available
        summary.setText(
            f"共 {len(entries)} 項 · {selected} 項已選 · "
            f"{unavailable} 項失效或不可用"
        )

    def checkbox_changed(item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry, PlaylistEntryV1) or not entry.available:
            return
        if item.checkState() == Qt.CheckState.Checked:
            checked.add(entry.entry_id)
        else:
            checked.discard(entry.entry_id)
        update_summary()

    def populate() -> None:
        nonlocal visible_entries
        table.blockSignals(True)
        visible_entries = filtered_playlist_entries(entries, search.text())
        table.setRowCount(len(visible_entries))
        for row, entry in enumerate(visible_entries):
            selected = QTableWidgetItem()
            selected.setData(Qt.ItemDataRole.UserRole, entry)
            selected.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                if entry.available
                else Qt.ItemFlag.NoItemFlags
            )
            selected.setCheckState(
                Qt.CheckState.Checked
                if entry.entry_id in checked and entry.available
                else Qt.CheckState.Unchecked
            )
            status = QTableWidgetItem(
                "可下載" if entry.available else entry.unavailable_reason or "不可用"
            )
            status.setForeground(
                QColor(COLORS["success"] if entry.available else COLORS["danger"])
            )
            values = (
                selected,
                QTableWidgetItem(str(entry.position)),
                QTableWidgetItem(entry.title),
                QTableWidgetItem(entry.artist or "—"),
                QTableWidgetItem(duration_text(entry.duration)),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 42)
        table.blockSignals(False)
        update_summary()

    def set_visible(mode: str) -> None:
        for entry in visible_entries:
            if not entry.available:
                continue
            if mode == "select":
                checked.add(entry.entry_id)
            elif mode == "clear":
                checked.discard(entry.entry_id)
            else:
                if entry.entry_id in checked:
                    checked.discard(entry.entry_id)
                else:
                    checked.add(entry.entry_id)
        populate()

    def selected_entries() -> tuple[PlaylistEntryV1, ...]:
        return tuple(
            entry
            for entry in entries
            if entry.available and entry.entry_id in checked
        )

    def export_selection() -> None:
        selected = selected_entries()
        if not selected:
            QMessageBox.information(dialog, "匯出播放清單", "請先選擇項目。")
            return
        filename, _selected_filter = QFileDialog.getSaveFileName(
            dialog,
            "匯出播放清單 ID",
            "playlist-ids.json",
            "MediaManager 播放清單 (*.json)",
        )
        if not filename:
            return
        try:
            count = export_playlist_entries(Path(filename), selected)
        except (OSError, ValueError) as error:
            QMessageBox.warning(dialog, "匯出失敗", str(error))
            return
        QMessageBox.information(dialog, "匯出完成", f"已匯出 {count} 個項目。")

    search.textChanged.connect(populate)
    table.itemChanged.connect(checkbox_changed)
    select_visible.clicked.connect(lambda: set_visible("select"))
    clear_visible.clicked.connect(lambda: set_visible("clear"))
    invert_visible.clicked.connect(lambda: set_visible("invert"))
    export_checked.clicked.connect(export_selection)
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
    return selected_entries()
