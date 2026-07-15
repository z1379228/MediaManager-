"""Trusted playlist selection, thumbnail, audio and video preview dialog."""

from __future__ import annotations

from pathlib import Path
import threading

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
    entries: tuple[PlaylistEntryV1, ...],
    parent: object = None,
    *,
    preview_provider: object | None = None,
    video_preview_provider: object | None = None,
) -> tuple[PlaylistEntryV1, ...] | None:
    from PySide6.QtCore import QObject, QSize, Qt, QUrl, Signal
    from PySide6.QtGui import QColor, QIcon
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
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
    from trusted_ui.thumbnail_loader import create_thumbnail_loader

    class PreviewBridge(QObject):
        finished = Signal(int, object, str, str)

    dialog = QDialog(parent)
    dialog.setWindowTitle("播放清單項目")
    dialog.resize(980, 650)
    page = QVBoxLayout(dialog)
    page.setContentsMargins(18, 16, 18, 14)
    page.setSpacing(10)

    heading = QLabel("選擇要加入下載佇列的項目")
    heading.setObjectName("sectionTitle")
    page.addWidget(heading)
    summary = QLabel()
    summary.setObjectName("sectionSubtitle")
    page.addWidget(summary)

    tools = QHBoxLayout()
    search = QLineEdit()
    search.setObjectName("playlistFilter")
    search.setPlaceholderText("依標題或作者篩選")
    search.setClearButtonEnabled(True)
    select_visible = QPushButton("勾選可見項目")
    clear_visible = QPushButton("清除可見項目")
    invert_visible = QPushButton("反向勾選可見項目")
    export_checked = QPushButton("匯出所選 ID")
    tools.addWidget(search, 1)
    tools.addWidget(select_visible)
    tools.addWidget(clear_visible)
    tools.addWidget(invert_visible)
    tools.addWidget(export_checked)
    page.addLayout(tools)

    table = QTableWidget(0, 7)
    table.setObjectName("playlistEntries")
    table.setAccessibleName("播放清單項目")
    table.setHorizontalHeaderLabels(
        ("選取", "縮圖", "#", "標題", "作者", "長度", "狀態")
    )
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setIconSize(QSize(96, 54))
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(0, 58)
    table.setColumnWidth(1, 110)
    table.setColumnWidth(2, 48)
    table.setColumnWidth(4, 180)
    table.setColumnWidth(5, 82)
    table.setColumnWidth(6, 115)
    page.addWidget(table, 1)

    preview_row = QHBoxLayout()
    preview_button = QPushButton("試聽 30 秒")
    preview_button.setObjectName("playlistPreview")
    stop_preview = QPushButton("停止試聽")
    stop_preview.setObjectName("playlistStopPreview")
    preview_status = QLabel(
        "選取項目後可試聽" if preview_provider is not None else "此來源不提供試聽"
    )
    preview_status.setObjectName("playlistPreviewStatus")
    preview_row.addWidget(preview_button)
    preview_row.addWidget(stop_preview)
    preview_row.addWidget(preview_status, 1)
    page.addLayout(preview_row)

    video_preview_row = QHBoxLayout()
    video_preview_button = QPushButton("影片預覽 60 秒")
    video_preview_button.setObjectName("playlistVideoPreview")
    stop_video_preview_button = QPushButton("停止影片預覽")
    stop_video_preview_button.setObjectName("playlistStopVideoPreview")
    video_preview_status = QLabel(
        "選取項目後可預覽影片"
        if video_preview_provider is not None
        else "啟用 YouTube Player 子 MOD 後可預覽影片"
    )
    video_preview_status.setObjectName("playlistVideoPreviewStatus")
    video_preview_row.addWidget(video_preview_button)
    video_preview_row.addWidget(stop_video_preview_button)
    video_preview_row.addWidget(video_preview_status, 1)
    page.addLayout(video_preview_row)

    thumbnail_loader = create_thumbnail_loader(dialog)
    # Opening a playlist is an inspection step.  The user must explicitly opt
    # items into the download queue instead of accidentally accepting all.
    checked: set[str] = set()
    visible_entries: tuple[PlaylistEntryV1, ...] = entries
    thumbnail_generation = [0]
    preview_generation = [0]
    preview_busy = [False]
    preview_path: list[str | None] = [None]
    preview_owner: list[object | None] = [None]
    video_preview_generation = [0]
    video_preview_busy = [False]
    video_preview_path: list[str | None] = [None]
    video_preview_owner: list[object | None] = [None]
    video_preview_dialog: list[object | None] = [None]
    video_preview_player: list[object | None] = [None]
    closing = [False]
    bridge = PreviewBridge(dialog)
    video_bridge = PreviewBridge(dialog)
    player = QMediaPlayer(dialog)
    audio = QAudioOutput(dialog)
    audio.setVolume(0.7)
    player.setAudioOutput(audio)

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

    def selected_visible_entry() -> PlaylistEntryV1 | None:
        row = table.currentRow()
        return visible_entries[row] if 0 <= row < len(visible_entries) else None

    def update_preview_state() -> None:
        selected = selected_visible_entry()
        preview_button.setEnabled(
            preview_provider is not None
            and not preview_busy[0]
            and selected is not None
            and selected.available
        )
        stop_preview.setEnabled(preview_busy[0] or preview_path[0] is not None)
        video_preview_button.setEnabled(
            video_preview_provider is not None
            and not video_preview_busy[0]
            and selected is not None
            and selected.available
        )
        stop_video_preview_button.setEnabled(
            video_preview_busy[0] or video_preview_path[0] is not None
        )

    def update_summary() -> None:
        available = sum(entry.available for entry in entries)
        selected = sum(
            entry.available and entry.entry_id in checked for entry in entries
        )
        unavailable = len(entries) - available
        summary.setText(
            f"共 {len(entries)} 項；已選 {selected} 項；{unavailable} 項目前不可用"
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

    def show_thumbnail(
        generation: int, row: int, entry: PlaylistEntryV1, pixmap: object | None
    ) -> None:
        if closing[0] or generation != thumbnail_generation[0]:
            return
        item = table.item(row, 1)
        if item is None or item.data(Qt.ItemDataRole.UserRole) != entry:
            return
        item.setText("" if pixmap is not None else "—")
        item.setIcon(QIcon(pixmap) if pixmap is not None else QIcon())

    def populate() -> None:
        nonlocal visible_entries
        thumbnail_generation[0] += 1
        generation = thumbnail_generation[0]
        thumbnail_loader.cancel_pending()
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
            thumbnail = QTableWidgetItem("載入中" if entry.thumbnail_url else "—")
            thumbnail.setData(Qt.ItemDataRole.UserRole, entry)
            status = QTableWidgetItem(
                "可下載" if entry.available else entry.unavailable_reason or "不可用"
            )
            status.setForeground(
                QColor(COLORS["success"] if entry.available else COLORS["danger"])
            )
            values = (
                selected,
                thumbnail,
                QTableWidgetItem(str(entry.position)),
                QTableWidgetItem(entry.title),
                QTableWidgetItem(entry.artist or "—"),
                QTableWidgetItem(duration_text(entry.duration)),
                status,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(row, column, item)
            table.setRowHeight(row, 62)
            if entry.thumbnail_url:
                thumbnail_loader.load(
                    entry.thumbnail_url,
                    lambda pixmap, generation=generation, row=row, entry=entry: show_thumbnail(
                        generation, row, entry, pixmap
                    ),
                )
        table.blockSignals(False)
        if visible_entries:
            table.selectRow(0)
        update_summary()
        update_preview_state()

    def set_visible(mode: str) -> None:
        for entry in visible_entries:
            if not entry.available:
                continue
            if mode == "select":
                checked.add(entry.entry_id)
            elif mode == "clear":
                checked.discard(entry.entry_id)
            elif entry.entry_id in checked:
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

    def cleanup_preview() -> None:
        owner, path = preview_owner[0], preview_path[0]
        preview_owner[0] = None
        preview_path[0] = None
        player.stop()
        player.setSource(QUrl())
        if owner is not None and path is not None:
            try:
                owner.cleanup_audio_preview(path)
            except OSError:
                pass

    def stop_audio_preview() -> None:
        was_active = preview_busy[0] or preview_path[0] is not None
        preview_generation[0] += 1
        preview_busy[0] = False
        cleanup_preview()
        if was_active and not closing[0]:
            preview_status.setText("試聽已停止")
        update_preview_state()

    def prepare_audio_preview() -> None:
        entry = selected_visible_entry()
        if preview_provider is None or entry is None or not entry.available:
            return
        stop_video_preview()
        stop_audio_preview()
        preview_generation[0] += 1
        generation = preview_generation[0]
        preview_busy[0] = True
        preview_status.setText("正在準備 30 秒音訊…")
        update_preview_state()

        def worker() -> None:
            try:
                path = preview_provider.prepare_audio_preview(
                    entry.url,
                    duration=float(entry.duration or 30),
                    preview_length=30,
                )
                if closing[0] or generation != preview_generation[0]:
                    preview_provider.cleanup_audio_preview(path)
                    return
                bridge.finished.emit(generation, preview_provider, str(path), "")
            except Exception as error:
                if not closing[0] and generation == preview_generation[0]:
                    bridge.finished.emit(generation, None, "", str(error))

        threading.Thread(target=worker, daemon=True).start()

    def show_audio_preview(
        generation: int, owner: object | None, path: str, error: str
    ) -> None:
        if closing[0] or generation != preview_generation[0]:
            if owner is not None and path:
                owner.cleanup_audio_preview(path)
            return
        preview_busy[0] = False
        if error or owner is None or not path:
            preview_status.setText(f"試聽失敗：{error or '沒有可播放的音訊'}")
            update_preview_state()
            return
        preview_owner[0] = owner
        preview_path[0] = path
        player.setSource(QUrl.fromLocalFile(path))
        player.play()
        preview_status.setText("正在試聽 30 秒；可按停止")
        update_preview_state()

    def handle_media_status(status: object) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia and preview_path[0]:
            cleanup_preview()
            preview_status.setText("30 秒試聽已結束")
            update_preview_state()

    def handle_media_error(*_error: object) -> None:
        if not preview_path[0]:
            return
        message = player.errorString() or "無法播放音訊"
        cleanup_preview()
        preview_status.setText(f"播放失敗：{message}")
        update_preview_state()

    def cleanup_video_preview() -> None:
        child = video_preview_dialog[0]
        player_instance = video_preview_player[0]
        owner, path = video_preview_owner[0], video_preview_path[0]
        video_preview_dialog[0] = None
        video_preview_player[0] = None
        video_preview_owner[0] = None
        video_preview_path[0] = None
        if player_instance is not None:
            player_instance.stop()
            player_instance.setSource(QUrl())
        if child is not None and child.isVisible():
            child.close()
        if owner is not None and path is not None:
            try:
                owner.cleanup_video_preview(path)
            except OSError:
                pass

    def stop_video_preview() -> None:
        was_active = (
            video_preview_busy[0] or video_preview_path[0] is not None
        )
        video_preview_generation[0] += 1
        video_preview_busy[0] = False
        cleanup_video_preview()
        if was_active and not closing[0]:
            video_preview_status.setText("影片預覽已停止")
        update_preview_state()

    def prepare_video_preview() -> None:
        entry = selected_visible_entry()
        if (
            video_preview_provider is None
            or entry is None
            or not entry.available
        ):
            return
        stop_audio_preview()
        stop_video_preview()
        video_preview_generation[0] += 1
        generation = video_preview_generation[0]
        video_preview_busy[0] = True
        video_preview_status.setText("正在準備 60 秒影片…")
        update_preview_state()

        def worker() -> None:
            try:
                path = video_preview_provider.prepare_video_preview(
                    entry.url,
                    duration=float(entry.duration or 60),
                    preview_length=60,
                )
                if closing[0] or generation != video_preview_generation[0]:
                    video_preview_provider.cleanup_video_preview(path)
                    return
                video_bridge.finished.emit(
                    generation, video_preview_provider, str(path), ""
                )
            except Exception as error:
                if not closing[0] and generation == video_preview_generation[0]:
                    video_bridge.finished.emit(generation, None, "", str(error))

        threading.Thread(target=worker, daemon=True).start()

    def show_video_preview(
        generation: int, owner: object | None, path: str, error: str
    ) -> None:
        if closing[0] or generation != video_preview_generation[0]:
            if owner is not None and path:
                owner.cleanup_video_preview(path)
            return
        video_preview_busy[0] = False
        if error or owner is None or not path:
            video_preview_status.setText(
                f"影片預覽失敗：{error or '沒有可播放的影片'}"
            )
            update_preview_state()
            return
        video_preview_owner[0] = owner
        video_preview_path[0] = path
        child = QDialog(dialog)
        child.setWindowTitle("播放清單影片預覽（最多 60 秒）")
        child.resize(720, 480)
        child_layout = QVBoxLayout(child)
        video = QVideoWidget(child)
        child_layout.addWidget(video, 1)
        close_preview = QPushButton("停止並關閉", child)
        close_preview.clicked.connect(child.close)
        child_layout.addWidget(close_preview)
        player_instance = QMediaPlayer(child)
        video_audio = QAudioOutput(child)
        video_audio.setVolume(0.7)
        player_instance.setAudioOutput(video_audio)
        player_instance.setVideoOutput(video)
        player_instance.setSource(QUrl.fromLocalFile(path))
        child._player = player_instance
        child._audio = video_audio
        child.finished.connect(lambda _result: cleanup_video_preview())
        video_preview_dialog[0] = child
        video_preview_player[0] = player_instance
        child.show()
        player_instance.play()
        video_preview_status.setText("正在預覽影片；最多 60 秒")
        update_preview_state()

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

    def shutdown(_result: int) -> None:
        closing[0] = True
        preview_generation[0] += 1
        video_preview_generation[0] += 1
        thumbnail_generation[0] += 1
        thumbnail_loader.cancel_pending()
        cleanup_preview()
        cleanup_video_preview()

    search.textChanged.connect(populate)
    table.itemChanged.connect(checkbox_changed)
    table.currentCellChanged.connect(lambda *_args: update_preview_state())
    select_visible.clicked.connect(lambda: set_visible("select"))
    clear_visible.clicked.connect(lambda: set_visible("clear"))
    invert_visible.clicked.connect(lambda: set_visible("invert"))
    export_checked.clicked.connect(export_selection)
    preview_button.clicked.connect(prepare_audio_preview)
    stop_preview.clicked.connect(stop_audio_preview)
    bridge.finished.connect(show_audio_preview)
    video_preview_button.clicked.connect(prepare_video_preview)
    stop_video_preview_button.clicked.connect(stop_video_preview)
    video_bridge.finished.connect(show_video_preview)
    player.mediaStatusChanged.connect(handle_media_status)
    player.errorOccurred.connect(handle_media_error)
    dialog.finished.connect(shutdown)
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
