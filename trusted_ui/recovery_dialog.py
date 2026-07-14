"""Explicit recovery candidate dialog for failed download tasks."""

from __future__ import annotations

from contracts.recovery_v1 import RecoveryCandidateV1
from core.downloads.archive import DuplicateDownloadError
from core.downloads.models import DownloadRequest


def build_replacement_request(
    original: DownloadRequest,
    candidate: RecoveryCandidateV1,
) -> DownloadRequest:
    item = candidate.item
    return DownloadRequest(
        item.url,
        original.output_dir,
        priority=original.priority,
        start_time=original.start_time,
        end_time=original.end_time,
        source_video_id=item.video_id,
        source_title=item.title,
        source_artist=item.artist,
        source_language=item.language,
        source_category=item.category,
        output_filename=original.output_filename,
        audio_only=original.audio_only,
        format_preset=original.format_preset,
        subtitle_mode=original.subtitle_mode,
        subtitle_languages=original.subtitle_languages,
        timed_comment_mode=original.timed_comment_mode,
        container_preset=original.container_preset,
    )


def show_recovery_dialog(
    context: object,
    original: DownloadRequest,
    candidates: tuple[RecoveryCandidateV1, ...],
    parent: object = None,
) -> int:
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle("選擇替代影片")
    dialog.resize(860, 480)
    layout = QVBoxLayout(dialog)
    title = QLabel("請確認替代候選；系統不會自動替換原工作。")
    title.setObjectName("sectionSubtitle")
    layout.addWidget(title)

    table = QTableWidget(len(candidates), 4)
    table.setHorizontalHeaderLabels(["標題", "作者 / 頻道", "符合度", "原因"])
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().hide()
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    reason_names = {
        "title": "標題",
        "artist": "歌手",
        "language": "語言",
        "category": "類別",
        "related": "相關",
    }
    for row, candidate in enumerate(candidates):
        item = candidate.item
        name = QTableWidgetItem(item.title)
        name.setData(Qt.ItemDataRole.UserRole, row)
        name.setToolTip(item.url)
        table.setItem(row, 0, name)
        table.setItem(row, 1, QTableWidgetItem(item.artist or "—"))
        score = QTableWidgetItem(f"{candidate.score}%")
        score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 2, score)
        reasons = "、".join(
            reason_names.get(reason, reason) for reason in candidate.reasons
        )
        table.setItem(row, 3, QTableWidgetItem(reasons))
    if candidates:
        table.selectRow(0)
    layout.addWidget(table, 1)

    buttons = QHBoxLayout()
    add = QPushButton("加入替代下載")
    add.setObjectName("primary")
    open_button = QPushButton("在瀏覽器開啟")
    cancel = QPushButton("取消")
    buttons.addWidget(add)
    buttons.addWidget(open_button)
    buttons.addStretch()
    buttons.addWidget(cancel)
    layout.addLayout(buttons)

    def selected() -> RecoveryCandidateV1 | None:
        row = table.currentRow()
        return candidates[row] if 0 <= row < len(candidates) else None

    def add_selected() -> None:
        candidate = selected()
        if candidate is None:
            QMessageBox.information(dialog, "替代下載", "請先選擇候選影片。")
            return
        try:
            context.download_queue.add(
                build_replacement_request(original, candidate)
            )
        except DuplicateDownloadError:
            QMessageBox.information(
                dialog,
                "重複下載",
                "這個替代影片已在佇列或成功下載封存中。",
            )
            return
        dialog.accept()

    def open_selected() -> None:
        candidate = selected()
        if candidate is not None:
            QDesktopServices.openUrl(QUrl(candidate.item.url))

    add.clicked.connect(add_selected)
    open_button.clicked.connect(open_selected)
    cancel.clicked.connect(dialog.reject)
    table.itemDoubleClicked.connect(lambda *_: open_selected())
    return dialog.exec()
