"""UI for the optional local Media Convert MOD."""

from __future__ import annotations

import math
from pathlib import Path

from core.conversion import ConversionRequest, ConversionState
from trusted_ui.table_refresh import task_table_interval, visible_rows_signature


def _time_seconds(value: str) -> float:
    token = value.strip()
    if not token:
        raise ValueError("時間不可留空")
    parts = token.split(":")
    if len(parts) > 3:
        raise ValueError(f"無效時間：{value}")
    try:
        numbers = tuple(float(part) for part in parts)
    except ValueError as error:
        raise ValueError(f"無效時間：{value}") from error
    if any(not math.isfinite(number) or number < 0 for number in numbers):
        raise ValueError(f"無效時間：{value}")
    if len(numbers) > 1 and any(number >= 60 for number in numbers[1:]):
        raise ValueError(f"分與秒必須小於 60：{value}")
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def parse_removal_ranges(value: str) -> tuple[tuple[float, float], ...]:
    """Parse ``start-end`` ranges using seconds or HH:MM:SS values."""

    normalized = value.replace("；", ";").replace("\n", ";").strip()
    if not normalized:
        return ()
    ranges: list[tuple[float, float]] = []
    for raw_range in normalized.split(";"):
        item = raw_range.strip()
        if not item:
            continue
        if item.count("-") != 1:
            raise ValueError(f"區間格式應為 開始-結束：{item}")
        start, end = (_time_seconds(part) for part in item.split("-", 1))
        ranges.append((start, end))
    if len(ranges) > 50:
        raise ValueError("最多可輸入 50 個剪除區間")
    return tuple(ranges)


def create_conversion_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import QSignalBlocker, Qt, QTimer, QUrl
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from trusted_ui.builtin_mod_control import (
        builtin_mod_is_enabled,
        set_builtin_mod_enabled,
    )

    service = context.conversion
    if service is None:
        raise RuntimeError("Media Convert service is unavailable")
    panel = QWidget(parent)
    panel.sources = []
    panel.render_signature = None
    panel.preview_dialog = None
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)

    title = QLabel("Media Convert")
    title.setObjectName("sectionTitle")
    subtitle = QLabel(
        "使用本機 FFmpeg 轉封裝、轉檔與剪輯；工作可取消、先寫入 .part，"
        "完成後才建立輸出檔。"
    )
    subtitle.setObjectName("sectionSubtitle")
    subtitle.setWordWrap(True)
    page.addWidget(title)
    page.addWidget(subtitle)

    guide = QLabel(
        "使用方式：先選擇來源和輸出位置，再選格式；所有工作由本機 FFmpeg 處理。"
        "Local Ad Segment Trim 是可獨立停用的"
        "子 MOD，只接受本機檔案與手動時間區間，不會存取網站或繞過廣告限制；"
        "輸出一定是新檔，不覆寫原檔。"
    )
    guide.setObjectName("modUsageGuide")
    guide.setWordWrap(True)
    page.addWidget(guide)

    card = QFrame()
    card.setObjectName("card")
    form = QVBoxLayout(card)
    form.setSpacing(10)

    source_row = QHBoxLayout()
    source_text = QLineEdit()
    source_text.setReadOnly(True)
    source_text.setPlaceholderText("尚未選擇本機媒體")
    choose_sources = QPushButton("選擇來源")
    source_row.addWidget(source_text, 1)
    source_row.addWidget(choose_sources)
    form.addLayout(source_row)

    option_grid = QGridLayout()
    option_grid.setColumnStretch(1, 1)
    option_grid.setColumnStretch(5, 1)
    preset = QComboBox()
    labels = {
        "remux-copy": "串流複製封裝",
        "split-copy": "依時間切割",
        "join-copy": "相同格式串接",
        "video-h264": "H.264 相容轉檔",
        "compress-h265": "H.265 CPU 壓縮",
        "audio-mp3": "音訊 MP3",
        "audio-flac": "音訊 FLAC",
        "subtitle-srt": "抽取 SRT 字幕",
        "ad-trim-h264": "本機廣告段落剪除（子 MOD）",
    }
    for preset_id in service.preset_ids():
        preset.addItem(labels.get(preset_id, preset_id), preset_id)

    start = QDoubleSpinBox()
    end = QDoubleSpinBox()
    for control in (start, end):
        control.setRange(0, 604_800)
        control.setDecimals(3)
        control.setSpecialValueText("未設定")
        control.setSuffix(" 秒")
    gpu = QCheckBox("H.264 使用 NVIDIA GPU（失敗回退 CPU）")
    output_text = QLineEdit()
    output_text.setReadOnly(True)
    output_text.setPlaceholderText("尚未選擇輸出新檔")
    choose_output = QPushButton("選擇輸出")

    option_grid.addWidget(QLabel("格式"), 0, 0)
    option_grid.addWidget(preset, 0, 1, 1, 2)
    option_grid.addWidget(gpu, 0, 3, 1, 3)
    option_grid.addWidget(QLabel("開始"), 1, 0)
    option_grid.addWidget(start, 1, 1)
    option_grid.addWidget(QLabel("結束"), 1, 2)
    option_grid.addWidget(end, 1, 3)
    option_grid.addWidget(output_text, 1, 4)
    option_grid.addWidget(choose_output, 1, 5)
    form.addLayout(option_grid)

    trim_card = QFrame()
    trim_card.setObjectName("subtleCard")
    trim_layout = QGridLayout(trim_card)
    ad_trim_enabled = QCheckBox("啟用 Local Ad Segment Trim 子 MOD")
    ad_ranges = QLineEdit()
    ad_ranges.setPlaceholderText("例：30-45; 01:30-01:45")
    preview_trim = QPushButton("預覽第一個切點 ±5 秒")
    trim_note = QLabel(
        "以分號分隔區間；可輸入秒數或 HH:MM:SS。只剪除指定區間並另存新檔。"
    )
    trim_note.setObjectName("muted")
    trim_note.setWordWrap(True)
    trim_layout.addWidget(ad_trim_enabled, 0, 0, 1, 2)
    trim_layout.addWidget(QLabel("剪除區間"), 1, 0)
    trim_layout.addWidget(ad_ranges, 1, 1)
    trim_layout.addWidget(preview_trim, 1, 2)
    trim_layout.addWidget(trim_note, 2, 0, 1, 3)
    form.addWidget(trim_card)

    submit_row = QHBoxLayout()
    estimate = QLabel("選擇來源、輸出與格式後會顯示估算。")
    estimate.setObjectName("muted")
    submit = QPushButton("加入轉換")
    submit.setObjectName("primary")
    submit_row.addWidget(estimate, 1)
    submit_row.addWidget(submit)
    form.addLayout(submit_row)
    page.addWidget(card)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("狀態", "來源", "處理", "輸出", "訊息"))
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    page.addWidget(table, 1)
    cancel = QPushButton("取消選取工作")
    page.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def trim_enabled() -> bool:
        return builtin_mod_is_enabled(context, "media-ad-trim")

    def current_request() -> ConversionRequest:
        if not panel.sources or not output_text.text():
            raise ValueError("請先選擇來源與輸出新檔")
        selected_preset = str(preset.currentData())
        ranges = ()
        if selected_preset == "ad-trim-h264":
            if not trim_enabled():
                raise ValueError("請先啟用 Local Ad Segment Trim 子 MOD")
            ranges = parse_removal_ranges(ad_ranges.text())
        return ConversionRequest(
            tuple(panel.sources),
            Path(output_text.text()),
            selected_preset,
            None if selected_preset == "ad-trim-h264" or start.value() == 0 else float(start.value()),
            None if selected_preset == "ad-trim-h264" or end.value() == 0 else float(end.value()),
            hardware_acceleration=gpu.isChecked() and selected_preset != "ad-trim-h264",
            remove_ranges=ranges,
        )

    def size_text(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if number < 1024 or unit == "TB":
                return f"{number:.1f} {unit}"
            number /= 1024
        return str(value)

    def update_mode() -> None:
        selected = str(preset.currentData()) == "ad-trim-h264"
        child_enabled = trim_enabled()
        trim_card.setVisible(selected)
        start.setEnabled(not selected)
        end.setEnabled(not selected)
        gpu.setEnabled(not selected)
        ad_ranges.setEnabled(selected and child_enabled)
        preview_trim.setEnabled(
            selected and child_enabled and len(panel.sources) == 1
        )
        submit.setEnabled(not selected or child_enabled)

    def update_preview() -> None:
        update_mode()
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError):
            estimate.setText("選擇來源、輸出與有效設定後會顯示估算。")
        else:
            estimate.setText(
                f"{plan.strategy}；預估輸出 {size_text(plan.estimated_bytes)}"
            )

    def sync_trim_state() -> None:
        with QSignalBlocker(ad_trim_enabled):
            ad_trim_enabled.setChecked(trim_enabled())
        available = any(
            status.provider_id == "media-ad-trim"
            and bool(getattr(status, "available", True))
            for status in context.features.statuses()
        )
        ad_trim_enabled.setEnabled(available)
        ad_trim_enabled.setToolTip(
            "僅處理本機檔案；不會略過或移除網站廣告。"
            if available
            else "此子 MOD 未載入，或尚未偵測到 FFmpeg。"
        )
        update_preview()

    def toggle_trim(checked: bool) -> None:
        try:
            set_builtin_mod_enabled(context, "media-ad-trim", checked)
        except (KeyError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Local Ad Segment Trim", str(error))
        sync_trim_state()

    def select_sources() -> None:
        values, _ = QFileDialog.getOpenFileNames(
            panel, "選擇本機媒體", str(Path.home()), "所有媒體 (*)"
        )
        if values:
            panel.sources = [Path(value) for value in values]
            source_text.setText(
                values[0]
                if len(values) == 1
                else f"{values[0]} 等 {len(values)} 個檔案"
            )
            update_preview()

    def select_output() -> None:
        value, _ = QFileDialog.getSaveFileName(
            panel, "選擇輸出新檔（不覆寫原檔）", str(Path.home()), "媒體檔案 (*)"
        )
        if value:
            output_text.setText(value)
            update_preview()

    def preview_first_cut() -> None:
        try:
            ranges = parse_removal_ranges(ad_ranges.text())
        except ValueError as error:
            QMessageBox.warning(panel, "切點預覽", str(error))
            return
        if len(panel.sources) != 1 or not ranges:
            QMessageBox.warning(panel, "切點預覽", "請選擇一個來源並輸入剪除區間")
            return
        if panel.preview_dialog is not None:
            panel.preview_dialog.close()
        dialog = QDialog(panel)
        dialog.setWindowTitle("本機切點預覽")
        dialog.resize(720, 460)
        layout = QVBoxLayout(dialog)
        video = QVideoWidget(dialog)
        layout.addWidget(video, 1)
        note = QLabel(
            f"預覽第一個切點：{ranges[0][0]:.3f} 秒附近；10 秒後自動暫停。"
        )
        layout.addWidget(note)
        controls = QHBoxLayout()
        replay = QPushButton("重新播放")
        stop = QPushButton("停止")
        close = QPushButton("關閉")
        controls.addWidget(replay)
        controls.addStretch(1)
        controls.addWidget(stop)
        controls.addWidget(close)
        layout.addLayout(controls)
        player = QMediaPlayer(dialog)
        audio = QAudioOutput(dialog)
        player.setAudioOutput(audio)
        player.setVideoOutput(video)
        player.setSource(QUrl.fromLocalFile(str(panel.sources[0].resolve())))
        preview_start = max(0, int((ranges[0][0] - 5.0) * 1000))
        pause_timer = QTimer(dialog)
        pause_timer.setSingleShot(True)

        def play() -> None:
            player.setPosition(preview_start)
            player.play()
            pause_timer.start(10_000)

        pause_timer.timeout.connect(player.pause)
        replay.clicked.connect(play)
        stop.clicked.connect(player.stop)
        close.clicked.connect(dialog.close)
        dialog.finished.connect(lambda _result: player.stop())
        dialog.finished.connect(lambda _result: pause_timer.stop())
        dialog.show()
        panel.preview_dialog = dialog
        QTimer.singleShot(0, play)

    def enqueue() -> None:
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
            return
        ranges = ""
        if plan.request.remove_ranges:
            ranges = "\n剪除：" + "; ".join(
                f"{start_value:.3f}-{end_value:.3f} 秒"
                for start_value, end_value in plan.request.remove_ranges
            )
        answer = QMessageBox.question(
            panel,
            "確認加入",
            f"{plan.strategy}\n預估：{size_text(plan.estimated_bytes)}"
            f"\n輸出：{plan.request.output}{ranges}\n\n原檔不會被覆寫，是否加入？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            service.submit(plan.request)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
        refresh()

    labels_by_state = {
        ConversionState.QUEUED: "排隊中",
        ConversionState.RUNNING: "處理中",
        ConversionState.COMPLETED: "完成",
        ConversionState.FAILED: "失敗",
        ConversionState.CANCELLED: "已取消",
    }

    def refresh() -> None:
        tasks = service.snapshots()
        rows = tuple(
            (
                task.task_id,
                task.state,
                task.request.sources,
                task.request.preset,
                task.output_path,
                task.request.output,
                task.error,
            )
            for task in tasks
        )
        interval = task_table_interval(
            active=any(
                task.state in {ConversionState.QUEUED, ConversionState.RUNNING}
                for task in tasks
            ),
            visible=panel.isVisible(),
        )
        if timer.interval() != interval:
            timer.setInterval(interval)
        signature = visible_rows_signature(rows)
        if signature == panel.render_signature:
            return
        panel.render_signature = signature
        table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            source = task.request.sources[0].name
            if len(task.request.sources) > 1:
                source += f" 等 {len(task.request.sources)} 個檔案"
            values = (
                labels_by_state[task.state],
                source,
                task.request.preset,
                task.output_path or str(task.request.output),
                task.error or "—",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, task.task_id)
                table.setItem(row, column, cell)

    def cancel_selected() -> None:
        cell = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
        if cell is not None:
            service.cancel(str(cell.data(Qt.ItemDataRole.UserRole)))
            refresh()

    def shutdown() -> None:
        timer.stop()
        if panel.preview_dialog is not None:
            panel.preview_dialog.close()
            panel.preview_dialog = None

    choose_sources.clicked.connect(select_sources)
    choose_output.clicked.connect(select_output)
    preset.currentIndexChanged.connect(update_preview)
    start.valueChanged.connect(update_preview)
    end.valueChanged.connect(update_preview)
    gpu.toggled.connect(update_preview)
    ad_ranges.textChanged.connect(update_preview)
    ad_trim_enabled.toggled.connect(toggle_trim)
    preview_trim.clicked.connect(preview_first_cut)
    submit.clicked.connect(enqueue)
    cancel.clicked.connect(cancel_selected)
    timer = QTimer(panel)
    timer.setInterval(1500)
    timer.timeout.connect(refresh)
    timer.start()
    panel.timer = timer
    panel.shutdown = shutdown
    panel.preset = preset
    panel.ad_trim_enabled = ad_trim_enabled
    panel.ad_ranges = ad_ranges
    panel.trim_card = trim_card
    panel.preview_trim = preview_trim
    panel.submit = submit
    sync_trim_state()
    refresh()
    return panel
