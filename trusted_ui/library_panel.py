"""Persistent local media-library panel kept separate from downloads."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from trusted_ui.empty_state import create_empty_state


def create_library_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QAction, QDesktopServices
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    panel = QWidget(parent)
    panel.items = []
    panel.current_root = None
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)

    heading = QHBoxLayout()
    titles = QVBoxLayout()
    titles.setSpacing(2)
    title = QLabel("本機媒體庫")
    title.setObjectName("sectionTitle")
    subtitle = QLabel("索引本機圖片、影片與音訊；自訂資訊只存於本機資料庫。")
    subtitle.setObjectName("sectionSubtitle")
    titles.addWidget(title)
    titles.addWidget(subtitle)
    heading.addLayout(titles)
    heading.addStretch()
    count = QLabel("0 個項目")
    count.setObjectName("badge")
    heading.addWidget(count)
    page.addLayout(heading)

    tools_card = QFrame()
    tools_card.setObjectName("card")
    tools = QHBoxLayout(tools_card)
    tools.setContentsMargins(14, 12, 14, 12)
    choose = QPushButton("選擇媒體資料夾")
    choose.setObjectName("primary")
    search = QLineEdit()
    search.setPlaceholderText("搜尋名稱、歌手或標籤")
    search.setClearButtonEnabled(True)
    include_offline = QCheckBox("顯示離線")
    manage = QPushButton("管理")
    manage.setObjectName("ghost")
    manage_menu = manage.menu() or None
    if manage_menu is None:
        from PySide6.QtWidgets import QMenu

        manage_menu = QMenu(manage)
        manage.setMenu(manage_menu)
    edit_metadata_action = QAction("編輯標題、歌手與標籤", manage_menu)
    artwork_action = QAction("設定封面圖片", manage_menu)
    duplicates_action = QAction("檢視重複檔案", manage_menu)
    move_action = QAction("移動／重新命名", manage_menu)
    import_action = QAction("匯入 M3U／JSON 播放清單", manage_menu)
    export_action = QAction("匯出播放清單", manage_menu)
    create_playlist_action = QAction("以選取項目建立播放清單", manage_menu)
    smart_playlist_action = QAction("以目前篩選建立智慧播放清單", manage_menu)
    for action in (
        edit_metadata_action,
        artwork_action,
        duplicates_action,
        move_action,
    ):
        manage_menu.addAction(action)
    manage_menu.addSeparator()
    for action in (
        create_playlist_action,
        smart_playlist_action,
        import_action,
        export_action,
    ):
        manage_menu.addAction(action)
    folder = QLabel("尚未選擇資料夾")
    folder.setObjectName("muted")
    folder.setMinimumWidth(220)
    tools.addWidget(choose)
    tools.addWidget(folder, 1)
    tools.addWidget(search, 1)
    tools.addWidget(include_offline)
    tools.addWidget(manage)
    page.addWidget(tools_card)

    stack = QStackedWidget()
    empty = create_empty_state(
        "選擇一個資料夾建立本機索引",
        "媒體不會上傳；標籤、播放紀錄與播放清單保存在本機。",
    )
    stack.addWidget(empty)

    table = QTableWidget(0, 7)
    table.setHorizontalHeaderLabels(
        ["標題／檔名", "歌手", "類型", "標籤", "大小", "播放", "修改時間"]
    )
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    for column in (1, 2, 4, 5, 6):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    stack.addWidget(table)
    page.addWidget(stack, 1)

    def size_text(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def selected_items() -> list[object]:
        selected = []
        for model_index in table.selectionModel().selectedRows(0):
            cell = table.item(model_index.row(), 0)
            if cell is not None:
                item = cell.data(Qt.ItemDataRole.UserRole)
                if item is not None:
                    selected.append(item)
        return selected

    def selected_one(action: str) -> object | None:
        selected = selected_items()
        if len(selected) != 1:
            QMessageBox.information(panel, action, "請先選擇一個項目。")
            return None
        return selected[0]

    def refresh() -> None:
        query = search.text().strip()
        panel.items = list(
            context.library.search(
                query,
                available_only=not include_offline.isChecked(),
                root=panel.current_root,
            )
        )
        count.setText(f"{len(panel.items)} 個項目")
        table.setRowCount(len(panel.items))
        for row, item in enumerate(panel.items):
            table.setRowHeight(row, 42)
            display = item.display_title
            if item.title:
                display = f"{item.title}\n{item.name}"
            name = QTableWidgetItem(display)
            name.setData(Qt.ItemDataRole.UserRole, item)
            name.setToolTip(str(item.path))
            if not item.available:
                name.setText(f"{display}（離線）")
            table.setItem(row, 0, name)
            table.setItem(row, 1, QTableWidgetItem(item.artist or "—"))
            media_type = QTableWidgetItem(item.media_type)
            media_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, media_type)
            table.setItem(row, 3, QTableWidgetItem("、".join(item.tags) or "—"))
            table.setItem(row, 4, QTableWidgetItem(size_text(item.size)))
            plays = QTableWidgetItem(str(item.play_count))
            plays.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 5, plays)
            table.setItem(
                row,
                6,
                QTableWidgetItem(
                    datetime.fromtimestamp(item.modified).strftime("%Y-%m-%d %H:%M")
                ),
            )
        stack.setCurrentWidget(table if panel.items else empty)

    def choose_folder() -> None:
        selected = QFileDialog.getExistingDirectory(
            panel, "選擇媒體資料夾", str(panel.current_root or Path.home())
        )
        if not selected:
            return
        panel.current_root = Path(selected).resolve()
        folder.setText(selected)
        folder.setToolTip(selected)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            context.library.scan(panel.current_root)
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "媒體庫掃描", f"掃描未完成：{error}")
        finally:
            QApplication.restoreOverrideCursor()
        refresh()

    def open_item() -> None:
        item = selected_one("開啟媒體")
        if item is None or not item.available:
            return
        context.library.record_play(item.item_id)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.path)))
        refresh()

    def edit_metadata() -> None:
        item = selected_one("編輯媒體資訊")
        if item is None:
            return
        dialog = QDialog(panel)
        dialog.setWindowTitle("編輯本機媒體資訊")
        form = QFormLayout(dialog)
        title_input = QLineEdit(item.title)
        artist_input = QLineEdit(item.artist)
        tags_input = QLineEdit(", ".join(item.tags))
        tags_input.setPlaceholderText("以逗號分隔，例如：工作, 日文, BGM")
        form.addRow("標題", title_input)
        form.addRow("歌手／作者", artist_input)
        form.addRow("標籤", tags_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            context.library.update_metadata(
                item.item_id,
                title=title_input.text(),
                artist=artist_input.text(),
                tags=(tag.strip() for tag in tags_input.text().split(",")),
            )
        except (KeyError, ValueError) as error:
            QMessageBox.warning(panel, "編輯媒體資訊", str(error))
        refresh()

    def set_artwork() -> None:
        item = selected_one("設定封面")
        if item is None:
            return
        selected, _ = QFileDialog.getOpenFileName(
            panel,
            "選擇封面圖片",
            str(Path.home()),
            "圖片 (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if not selected:
            return
        try:
            context.library.set_artwork(item.item_id, Path(selected))
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "設定封面", str(error))
            return
        QMessageBox.information(panel, "設定封面", "封面已保存至本機限制大小的快取。")

    def show_duplicates() -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            groups = context.library.duplicate_groups()
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "重複檔案", str(error))
            return
        finally:
            QApplication.restoreOverrideCursor()
        if not groups:
            QMessageBox.information(panel, "重複檔案", "目前沒有找到內容相同的檔案。")
            return
        lines = []
        for index, group in enumerate(groups[:30], 1):
            lines.append(f"群組 {index}（{size_text(group.size)}）")
            lines.extend(f"  {item.path}" for item in group.items)
        if len(groups) > 30:
            lines.append(f"另有 {len(groups) - 30} 個群組未顯示。")
        QMessageBox.information(
            panel,
            "重複檔案檢視",
            "只列出供確認，不會自動刪除。\n\n" + "\n".join(lines),
        )

    def move_item() -> None:
        item = selected_one("移動／重新命名")
        if item is None:
            return
        selected, _ = QFileDialog.getSaveFileName(
            panel,
            "選擇新位置（不會覆寫既有檔案）",
            str(item.path),
            f"相同格式 (*{item.path.suffix})",
        )
        if not selected:
            return
        try:
            plan = context.library.preview_move(item.item_id, Path(selected))
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "移動／重新命名", str(error))
            return
        answer = QMessageBox.question(
            panel,
            "確認移動",
            f"來源：{plan.source}\n目標：{plan.target}\n\n不會覆寫既有檔案，確定執行？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            context.library.apply_move(plan)
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "移動／重新命名", f"未完成且已嘗試回復：{error}")
        refresh()

    def create_playlist(*, smart: bool = False) -> None:
        if not smart and not selected_items():
            QMessageBox.information(panel, "建立播放清單", "請先選擇至少一個項目。")
            return
        name, accepted = QInputDialog.getText(panel, "建立播放清單", "播放清單名稱")
        if not accepted or not name.strip():
            return
        try:
            if smart:
                context.library.create_playlist(
                    name,
                    query={"query": search.text().strip(), "available_only": True},
                )
            else:
                context.library.create_playlist(
                    name, [item.item_id for item in selected_items()]
                )
        except (KeyError, ValueError) as error:
            QMessageBox.warning(panel, "建立播放清單", str(error))
            return
        QMessageBox.information(panel, "建立播放清單", "播放清單已保存於本機。")

    def import_playlist() -> None:
        selected, _ = QFileDialog.getOpenFileName(
            panel,
            "匯入播放清單",
            str(Path.home()),
            "播放清單 (*.m3u *.m3u8 *.json)",
        )
        if not selected:
            return
        try:
            preview = context.library.preview_playlist_import(Path(selected))
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "匯入播放清單", str(error))
            return
        available = len(preview.paths) - len(preview.missing)
        answer = QMessageBox.question(
            panel,
            "匯入預覽",
            f"名稱：{preview.name}\n可加入：{available}\n遺失／離線：{len(preview.missing)}\n重複略過：{len(preview.duplicates)}\n\n確定建立？",
        )
        if answer == QMessageBox.StandardButton.Yes:
            context.library.apply_playlist_import(preview)

    def export_playlist() -> None:
        playlists = context.library.playlists()
        if not playlists:
            QMessageBox.information(panel, "匯出播放清單", "目前沒有播放清單。")
            return
        labels = [f"{name}{'（智慧）' if smart else ''}" for _, name, smart in playlists]
        label, accepted = QInputDialog.getItem(
            panel, "匯出播放清單", "選擇播放清單", labels, 0, False
        )
        if not accepted:
            return
        playlist_id = playlists[labels.index(label)][0]
        selected, _ = QFileDialog.getSaveFileName(
            panel,
            "匯出播放清單",
            str(Path.home() / f"{label.replace('（智慧）', '')}.m3u8"),
            "M3U 播放清單 (*.m3u8);;MediaManager JSON (*.json)",
        )
        if not selected:
            return
        try:
            context.library.export_playlist(playlist_id, Path(selected))
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "匯出播放清單", str(error))

    choose.clicked.connect(choose_folder)
    search.textChanged.connect(refresh)
    include_offline.toggled.connect(refresh)
    table.itemDoubleClicked.connect(open_item)
    edit_metadata_action.triggered.connect(edit_metadata)
    artwork_action.triggered.connect(set_artwork)
    duplicates_action.triggered.connect(show_duplicates)
    move_action.triggered.connect(move_item)
    create_playlist_action.triggered.connect(
        lambda _checked=False: create_playlist(smart=False)
    )
    smart_playlist_action.triggered.connect(
        lambda _checked=False: create_playlist(smart=True)
    )
    import_action.triggered.connect(import_playlist)
    export_action.triggered.connect(export_playlist)
    refresh()
    return panel
