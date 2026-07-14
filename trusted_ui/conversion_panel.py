"""UI for the optional local Media Convert MOD."""

from __future__ import annotations

from pathlib import Path

from core.conversion import ConversionRequest, ConversionState
from trusted_ui.table_refresh import task_table_interval, visible_rows_signature


def create_conversion_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
        QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )

    service = context.conversion
    if service is None:
        raise RuntimeError("Media Convert service is unavailable")
    panel = QWidget(parent)
    panel.sources = []
    panel.render_signature = None
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)
    title = QLabel("Media Convert")
    title.setObjectName("sectionTitle")
    subtitle = QLabel("本機 FFmpeg 工作區；不覆寫來源，完成前使用 .part，停用即取消工作。")
    subtitle.setObjectName("sectionSubtitle")
    page.addWidget(title)
    page.addWidget(subtitle)
    guide = QLabel(
        "使用方式：① 確認環境頁已偵測 FFmpeg；② 選擇一個或多個來源檔；"
        "③ 選擇轉檔、抽取音訊、字幕或合併／分割預設；④ 指定輸出後開始。"
        "停用 MOD 會取消尚未完成的工作，但不會刪除已完成檔案。"
    )
    guide.setObjectName("modUsageGuide")
    guide.setWordWrap(True)
    page.addWidget(guide)

    card = QFrame()
    card.setObjectName("card")
    form = QVBoxLayout(card)
    source_row = QHBoxLayout()
    source_text = QLineEdit()
    source_text.setReadOnly(True)
    source_text.setPlaceholderText("尚未選擇來源")
    choose_sources = QPushButton("選擇來源")
    source_row.addWidget(source_text, 1)
    source_row.addWidget(choose_sources)
    form.addLayout(source_row)
    options = QHBoxLayout()
    preset = QComboBox()
    labels = {
        "remux-copy": "轉封裝（串流複製）", "split-copy": "依時間切割",
        "join-copy": "串接相同格式", "video-h264": "H.264 相容轉檔",
        "compress-h265": "H.265 CPU 壓縮", "audio-mp3": "抽取 MP3",
        "audio-flac": "抽取 FLAC", "subtitle-srt": "抽取 SRT 字幕",
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
    gpu = QCheckBox("H.264 嘗試 NVIDIA GPU，失敗回退 CPU")
    output_text = QLineEdit()
    output_text.setReadOnly(True)
    output_text.setPlaceholderText("尚未選擇輸出")
    choose_output = QPushButton("選擇輸出")
    options.addWidget(preset)
    options.addWidget(QLabel("開始"))
    options.addWidget(start)
    options.addWidget(QLabel("結束"))
    options.addWidget(end)
    options.addWidget(gpu)
    options.addWidget(output_text, 1)
    options.addWidget(choose_output)
    form.addLayout(options)
    submit_row = QHBoxLayout()
    estimate = QLabel("選擇來源、預設與輸出後會顯示估算。")
    estimate.setObjectName("muted")
    submit = QPushButton("預覽並加入")
    submit.setObjectName("primary")
    submit_row.addWidget(estimate, 1)
    submit_row.addWidget(submit)
    form.addLayout(submit_row)
    page.addWidget(card)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("狀態", "來源", "預設", "輸出", "訊息"))
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    page.addWidget(table, 1)
    cancel = QPushButton("取消選取工作")
    page.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def current_request() -> ConversionRequest:
        if not panel.sources or not output_text.text():
            raise ValueError("請先選擇來源與輸出位置")
        return ConversionRequest(
            tuple(panel.sources), Path(output_text.text()), str(preset.currentData()),
            None if start.value() == 0 else float(start.value()),
            None if end.value() == 0 else float(end.value()),
            hardware_acceleration=gpu.isChecked(),
        )

    def size_text(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if number < 1024 or unit == "TB":
                return f"{number:.1f} {unit}"
            number /= 1024
        return str(value)

    def update_preview() -> None:
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError):
            estimate.setText("選擇有效來源、預設與輸出後會顯示估算。")
        else:
            estimate.setText(f"{plan.strategy}；估計約 {size_text(plan.estimated_bytes)}")

    def select_sources() -> None:
        values, _ = QFileDialog.getOpenFileNames(panel, "選擇本機媒體", str(Path.home()), "所有檔案 (*)")
        if values:
            panel.sources = [Path(value) for value in values]
            source_text.setText(values[0] if len(values) == 1 else f"{values[0]} 等 {len(values)} 個")
            update_preview()

    def select_output() -> None:
        value, _ = QFileDialog.getSaveFileName(panel, "選擇新輸出檔（不覆寫）", str(Path.home()), "媒體檔案 (*)")
        if value:
            output_text.setText(value)
            update_preview()

    def enqueue() -> None:
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
            return
        if QMessageBox.question(panel, "確認加入", f"{plan.strategy}\n估計：{size_text(plan.estimated_bytes)}\n目標：{plan.request.output}\n\n確定加入？") != QMessageBox.StandardButton.Yes:
            return
        try:
            service.submit(plan.request)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
        refresh()

    labels_by_state = {
        ConversionState.QUEUED: "等待中", ConversionState.RUNNING: "處理中",
        ConversionState.COMPLETED: "完成", ConversionState.FAILED: "失敗",
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
            source = task.request.sources[0].name + (f" 等 {len(task.request.sources)} 個" if len(task.request.sources) > 1 else "")
            values = (labels_by_state[task.state], source, task.request.preset, task.output_path or str(task.request.output), task.error or "—")
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

    choose_sources.clicked.connect(select_sources)
    choose_output.clicked.connect(select_output)
    preset.currentIndexChanged.connect(update_preview)
    start.valueChanged.connect(update_preview)
    end.valueChanged.connect(update_preview)
    gpu.toggled.connect(update_preview)
    submit.clicked.connect(enqueue)
    cancel.clicked.connect(cancel_selected)
    timer = QTimer(panel)
    timer.setInterval(1500)
    timer.timeout.connect(refresh)
    timer.start()
    panel.timer = timer
    panel.shutdown = timer.stop
    refresh()
    return panel
