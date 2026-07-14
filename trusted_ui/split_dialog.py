"""Trusted, on-demand editor for auto-split drafts and audio previews."""

from __future__ import annotations

import re

from contracts.split_plan_v1 import SplitPlanV1


_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def split_plan_review(plan: SplitPlanV1) -> tuple[str, ...]:
    """Return bounded quality warnings before the user confirms a draft."""

    warnings: list[str] = []
    previous_end = 0.0
    for segment in plan.segments:
        duration = segment.end - segment.start
        if segment.start - previous_end > 1.0:
            warnings.append(f"第 {segment.index:02d} 段前有未涵蓋的時間間隙。")
        if duration < 15.0:
            warnings.append(f"第 {segment.index:02d} 段短於 15 秒，可能是誤切。")
        if not segment.title.strip() or segment.title.casefold().startswith("track "):
            warnings.append(f"第 {segment.index:02d} 段仍使用預設名稱。")
        if segment.evidence and max(item.confidence for item in segment.evidence) < 0.7:
            warnings.append(f"第 {segment.index:02d} 段切點信心偏低，請試聽確認。")
        previous_end = segment.end
        if len(warnings) >= 20:
            break
    return tuple(warnings)


def split_filename_preview(
    source_title: str, index: int, title: str, start: float, duration: float
) -> str:
    """Show the naming shape without writing a file or invoking a MOD."""

    def safe(value: str, fallback: str) -> str:
        normalized = " ".join(_UNSAFE_FILENAME.sub("_", value).split()).strip(" ._")
        return normalized or fallback

    source = safe(source_title, "video")
    track = safe(title, f"Track {index:02d}")
    value = f"{source}-{index:02d}-{track}-{int(start):06d}s-{int(duration):04d}s.m4a"
    return value[:180]


def build_edited_plan(
    original: SplitPlanV1,
    rows: list[tuple[float, str]],
) -> SplitPlanV1:
    if not 2 <= len(rows) <= 200:
        raise ValueError("至少需要兩個片段。")
    if abs(rows[0][0]) > 0.001:
        raise ValueError("第一個片段必須從 0 秒開始。")
    payload: list[dict[str, object]] = []
    previous = -1.0
    for index, (start, title) in enumerate(rows, 1):
        if not 0 <= start < original.duration or start <= previous:
            raise ValueError("切點必須依時間遞增且位於影片範圍內。")
        normalized_title = " ".join(title.split())[:200] or f"Track {index:02d}"
        end = rows[index][0] if index < len(rows) else original.duration
        if end - start < 1:
            raise ValueError("每個片段至少需要 1 秒。")
        evidence = [
            {
                "source": "manual",
                "confidence": 1.0,
                "detail": "user-confirmed boundary",
            }
        ]
        payload.append(
            {
                "index": index,
                "start": start,
                "end": end,
                "title": normalized_title,
                "evidence": evidence,
            }
        )
        previous = start
    warnings = [
        warning
        for warning in original.warnings
        if "requires user confirmation" not in warning
    ]
    return SplitPlanV1.from_dict(
        {
            "source_url": original.source_url,
            "source_title": original.source_title,
            "duration": original.duration,
            "composite_likely": True,
            "segments": payload,
            "warnings": warnings,
        }
    )


def show_split_dialog(
    plan: SplitPlanV1,
    preview_path: object,
    parent: object = None,
) -> SplitPlanV1 | None:
    from pathlib import Path

    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle("確認影片切割")
    dialog.resize(920, 560)
    layout = QVBoxLayout(dialog)
    heading = QLabel(
        "切點只是候選。請播放預覽、調整時間與曲名，確認後才會保存草稿。"
    )
    heading.setObjectName("sectionSubtitle")
    heading.setWordWrap(True)
    layout.addWidget(heading)
    review_warnings = tuple(dict.fromkeys((*plan.warnings, *split_plan_review(plan))))
    warning = QLabel("\n".join(review_warnings))
    warning.setObjectName("preview")
    warning.setWordWrap(True)
    warning.setVisible(bool(review_warnings))
    layout.addWidget(warning)

    rows: list[tuple[float, str]] = [
        (segment.start, segment.title) for segment in plan.segments
    ]
    if not rows:
        rows = [(0.0, "Track 01")]
    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(
        ["段落", "開始秒數", "結束秒數", "名稱", "來源", "輸出名稱預覽"]
    )
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().hide()
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
    layout.addWidget(table, 1)

    def capture_rows() -> list[tuple[float, str]]:
        captured: list[tuple[float, str]] = []
        for row in range(table.rowCount()):
            start_item = table.item(row, 1)
            title_item = table.item(row, 3)
            captured.append((float(start_item.text()), title_item.text()))
        return captured

    def refresh(values: list[tuple[float, str]]) -> None:
        rows[:] = sorted(values, key=lambda value: value[0])
        table.setRowCount(len(rows))
        for row, (start, title) in enumerate(rows):
            end = rows[row + 1][0] if row + 1 < len(rows) else plan.duration
            index_item = QTableWidgetItem(f"{row + 1:02d}")
            index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            start_item = QTableWidgetItem(f"{start:.3f}")
            if row == 0:
                start_item.setFlags(
                    start_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                )
            end_item = QTableWidgetItem(f"{end:.3f}")
            end_item.setFlags(end_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            title_item = QTableWidgetItem(title)
            source = (
                plan.segments[row].evidence[0].source
                if row < len(plan.segments) and plan.segments[row].evidence
                else "manual"
            )
            source_item = QTableWidgetItem(source)
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            filename_item = QTableWidgetItem(
                split_filename_preview(plan.source_title, row + 1, title, start, end - start)
            )
            filename_item.setFlags(
                filename_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            for column, item in enumerate(
                (
                    index_item,
                    start_item,
                    end_item,
                    title_item,
                    source_item,
                    filename_item,
                )
            ):
                table.setItem(row, column, item)
        if rows:
            table.selectRow(0)

    refresh(rows)

    audio_output = QAudioOutput(dialog)
    audio_output.setVolume(0.7)
    player = QMediaPlayer(dialog)
    player.setAudioOutput(audio_output)
    path = Path(preview_path).resolve()
    preview_available = path.is_file()
    if preview_available:
        player.setSource(QUrl.fromLocalFile(str(path)))
    stop_at_ms = [0]

    def stop_at(position: int) -> None:
        if stop_at_ms[0] and position >= stop_at_ms[0]:
            player.pause()
            stop_at_ms[0] = 0

    player.positionChanged.connect(stop_at)

    def play_range(start: float, end: float) -> None:
        if not preview_available:
            QMessageBox.information(dialog, "音訊預覽", "預覽音訊檔案不可用。")
            return
        player.setPosition(max(0, int(start * 1000)))
        stop_at_ms[0] = max(1, int(end * 1000))
        player.play()

    controls = QHBoxLayout()
    play_segment = QPushButton("播放選定片段")
    play_cut = QPushButton("播放切點前後 5 秒")
    add_cut = QPushButton("新增切點")
    remove_cut = QPushButton("移除切點／合併")
    stop = QPushButton("停止")
    for button in (play_segment, play_cut):
        button.setEnabled(preview_available)
    controls.addWidget(play_segment)
    controls.addWidget(play_cut)
    controls.addWidget(stop)
    controls.addStretch()
    controls.addWidget(add_cut)
    controls.addWidget(remove_cut)
    layout.addLayout(controls)

    def current_values() -> list[tuple[float, str]] | None:
        try:
            return capture_rows()
        except ValueError:
            QMessageBox.warning(dialog, "切點格式", "開始秒數必須是數字。")
            return None

    def play_selected() -> None:
        values = current_values()
        row = table.currentRow()
        if values is None or not 0 <= row < len(values):
            return
        end = values[row + 1][0] if row + 1 < len(values) else plan.duration
        play_range(values[row][0], end)

    def play_around_cut() -> None:
        values = current_values()
        row = table.currentRow()
        if values is None or not 0 < row < len(values):
            QMessageBox.information(dialog, "切點預覽", "請選擇第二段以後的切點。")
            return
        boundary = values[row][0]
        play_range(max(0, boundary - 5), min(plan.duration, boundary + 5))

    def add_boundary() -> None:
        values = current_values()
        if values is None:
            return
        value, accepted = QInputDialog.getDouble(
            dialog,
            "新增切點",
            "開始秒數",
            min(plan.duration - 1, max(1.0, plan.duration / 2)),
            1.0,
            max(1.0, plan.duration - 1),
            3,
        )
        if accepted:
            values.append((value, f"Track {len(values) + 1:02d}"))
            try:
                build_edited_plan(plan, sorted(values))
            except ValueError as error:
                QMessageBox.warning(dialog, "新增切點", str(error))
                return
            refresh(values)

    def remove_boundary() -> None:
        values = current_values()
        row = table.currentRow()
        if values is None or row <= 0:
            QMessageBox.information(dialog, "移除切點", "第一段起點不能移除。")
            return
        del values[row]
        refresh(values)

    result: list[SplitPlanV1] = []

    def confirm() -> None:
        values = current_values()
        if values is None:
            return
        try:
            edited = build_edited_plan(plan, values)
        except ValueError as error:
            QMessageBox.warning(dialog, "確認切割", str(error))
            return
        result.append(edited)
        dialog.accept()

    play_segment.clicked.connect(play_selected)
    play_cut.clicked.connect(play_around_cut)
    stop.clicked.connect(player.stop)
    add_cut.clicked.connect(add_boundary)
    remove_cut.clicked.connect(remove_boundary)

    buttons = QHBoxLayout()
    confirm_button = QPushButton("確認並加入下載佇列")
    confirm_button.setObjectName("primary")
    cancel = QPushButton("取消")
    buttons.addStretch()
    buttons.addWidget(confirm_button)
    buttons.addWidget(cancel)
    layout.addLayout(buttons)
    confirm_button.clicked.connect(confirm)
    cancel.clicked.connect(dialog.reject)
    dialog.finished.connect(lambda *_: player.stop())
    dialog.exec()
    player.setSource(QUrl())
    return result[0] if result else None
