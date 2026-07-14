"""UI for the optional local Speech to Text MOD."""

from __future__ import annotations

from pathlib import Path

from core.transcription import TranscriptionRequest, TranscriptionState
from trusted_ui.table_refresh import task_table_interval, visible_rows_signature


def create_transcription_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
        QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )

    service = context.transcription
    if service is None:
        raise RuntimeError("Speech to Text service is unavailable")
    panel = QWidget(parent)
    panel.source = None
    panel.render_signature = None
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)
    title = QLabel("Speech to Text")
    title.setObjectName("sectionTitle")
    adapter = QLabel(
        f"whisper.cpp：{service.adapter if service.adapter else '未偵測到 whisper-cli；可管理模型，但無法開始工作'}"
    )
    adapter.setObjectName("sectionSubtitle")
    adapter.setWordWrap(True)
    page.addWidget(title)
    page.addWidget(adapter)
    guide = QLabel(
        "使用方式：① 先安裝 whisper.cpp 的 whisper-cli；② 選擇本機 GGML/GGUF 模型，"
        "輸入模型 ID 與檔案 SHA-256 後匯入；③ 選擇音訊或影片、輸出資料夾、語言"
        "（auto 代表自動判斷）與 TXT/SRT/VTT；④ 開始轉錄。軟體不會自動下載模型。"
    )
    guide.setObjectName("modUsageGuide")
    guide.setWordWrap(True)
    page.addWidget(guide)

    model_card = QFrame()
    model_card.setObjectName("card")
    model_layout = QHBoxLayout(model_card)
    model_file = QLineEdit()
    model_file.setReadOnly(True)
    model_file.setPlaceholderText("選擇本機 whisper.cpp GGML/GGUF 模型")
    choose_model = QPushButton("選擇模型")
    model_id = QLineEdit()
    model_id.setPlaceholderText("模型 ID，例如 base-zh")
    model_hash = QLineEdit()
    model_hash.setPlaceholderText("確認來源公布的 64 位 SHA-256")
    import_model = QPushButton("驗證並匯入")
    model_layout.addWidget(model_file, 2)
    model_layout.addWidget(choose_model)
    model_layout.addWidget(model_id, 1)
    model_layout.addWidget(model_hash, 2)
    model_layout.addWidget(import_model)
    page.addWidget(model_card)

    job_card = QFrame()
    job_card.setObjectName("card")
    grid = QGridLayout(job_card)
    source_text = QLineEdit()
    source_text.setReadOnly(True)
    source_text.setPlaceholderText("尚未選擇音訊或影片")
    choose_source = QPushButton("選擇來源")
    models = QComboBox()
    output_text = QLineEdit()
    output_text.setReadOnly(True)
    output_text.setPlaceholderText("尚未選擇輸出資料夾")
    choose_output = QPushButton("選擇輸出資料夾")
    language = QLineEdit("auto")
    language.setMaximumWidth(100)
    txt = QCheckBox("TXT")
    srt = QCheckBox("SRT")
    vtt = QCheckBox("VTT")
    for checkbox in (txt, srt, vtt):
        checkbox.setChecked(True)
    submit = QPushButton("預覽並開始")
    submit.setObjectName("primary")
    grid.addWidget(source_text, 0, 0, 1, 3)
    grid.addWidget(choose_source, 0, 3)
    grid.addWidget(QLabel("模型"), 1, 0)
    grid.addWidget(models, 1, 1)
    grid.addWidget(QLabel("語言"), 1, 2)
    grid.addWidget(language, 1, 3)
    grid.addWidget(output_text, 2, 0, 1, 3)
    grid.addWidget(choose_output, 2, 3)
    formats = QHBoxLayout()
    formats.addWidget(txt)
    formats.addWidget(srt)
    formats.addWidget(vtt)
    formats.addStretch()
    formats.addWidget(submit)
    grid.addLayout(formats, 3, 0, 1, 4)
    page.addWidget(job_card)

    table = QTableWidget(0, 4)
    table.setHorizontalHeaderLabels(("狀態", "來源", "輸出", "訊息"))
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    table.horizontalHeader().setStretchLastSection(True)
    page.addWidget(table, 1)
    cancel = QPushButton("取消選取工作")
    page.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def reload_models() -> None:
        selected = models.currentData()
        models.clear()
        for model in service.models.list_models():
            models.addItem(f"{model.model_id}（{model.size / 1024**2:.0f} MB）", model.model_id)
        if selected is not None:
            index = models.findData(selected)
            if index >= 0:
                models.setCurrentIndex(index)

    def select_model_file() -> None:
        value, _ = QFileDialog.getOpenFileName(panel, "選擇本機模型", str(Path.home()), "模型 (*.bin *.gguf);;所有檔案 (*)")
        if value:
            model_file.setText(value)
            if not model_id.text():
                model_id.setText(Path(value).stem.casefold().replace("ggml-", "")[:64])

    def import_selected_model() -> None:
        if not model_file.text():
            QMessageBox.information(panel, "模型匯入", "請先選擇模型檔。")
            return
        try:
            service.models.import_model(Path(model_file.text()), model_id.text(), model_hash.text())
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "模型匯入", str(error))
            return
        reload_models()
        QMessageBox.information(panel, "模型匯入", "模型已驗證 SHA-256 並保存於本機。")

    def select_source() -> None:
        value, _ = QFileDialog.getOpenFileName(panel, "選擇音訊或影片", str(Path.home()), "媒體檔案 (*)")
        if value:
            panel.source = Path(value)
            source_text.setText(value)

    def select_output() -> None:
        value = QFileDialog.getExistingDirectory(panel, "選擇輸出資料夾", str(Path.home()))
        if value:
            output_text.setText(value)

    def current_request() -> TranscriptionRequest:
        selected_formats = tuple(name for name, checked in (("txt", txt), ("srt", srt), ("vtt", vtt)) if checked.isChecked())
        if panel.source is None or models.currentData() is None or not output_text.text():
            raise ValueError("請選擇來源、已驗證模型與輸出資料夾")
        return TranscriptionRequest(panel.source, str(models.currentData()), Path(output_text.text()), selected_formats, language.text())

    def enqueue() -> None:
        try:
            plan = service.preview(current_request())
        except (KeyError, OSError, ValueError) as error:
            QMessageBox.warning(panel, "Speech to Text", str(error))
            return
        ram = plan.estimated_ram_bytes / 1024**3
        if QMessageBox.question(panel, "確認語音轉文字", f"輸出：{', '.join(path.name for path in plan.outputs)}\n估計 RAM：{ram:.1f} GB\n\n確定開始本機處理？") != QMessageBox.StandardButton.Yes:
            return
        try:
            service.submit(plan.request)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Speech to Text", str(error))
        refresh()

    state_text = {
        TranscriptionState.QUEUED: "等待中", TranscriptionState.RUNNING: "處理中",
        TranscriptionState.COMPLETED: "完成", TranscriptionState.FAILED: "失敗",
        TranscriptionState.CANCELLED: "已取消",
    }

    def refresh() -> None:
        tasks = service.snapshots()
        rows = tuple(
            (
                task.task_id,
                task.state,
                task.request.source,
                task.outputs,
                task.request.output_dir,
                task.error,
            )
            for task in tasks
        )
        interval = task_table_interval(
            active=any(
                task.state in {
                    TranscriptionState.QUEUED,
                    TranscriptionState.RUNNING,
                }
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
            values = (state_text[task.state], task.request.source.name, ", ".join(task.outputs) or str(task.request.output_dir), task.error or "—")
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, task.task_id)
                table.setItem(row, column, cell)

    def cancel_selected() -> None:
        cell = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
        if cell is not None:
            service.cancel(str(cell.data(Qt.ItemDataRole.UserRole)))

    choose_model.clicked.connect(select_model_file)
    import_model.clicked.connect(import_selected_model)
    choose_source.clicked.connect(select_source)
    choose_output.clicked.connect(select_output)
    submit.clicked.connect(enqueue)
    cancel.clicked.connect(cancel_selected)
    timer = QTimer(panel)
    timer.setInterval(1500)
    timer.timeout.connect(refresh)
    timer.start()
    panel.timer = timer
    panel.shutdown = timer.stop
    reload_models()
    refresh()
    return panel
