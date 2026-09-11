"""UI for the optional local Speech to Text MOD."""

from __future__ import annotations

from pathlib import Path
import threading

from core.transcription import (
    TranscriptionCapabilities,
    TranscriptionRequest,
    TranscriptionState,
)
from trusted_ui.table_refresh import task_table_interval, visible_rows_signature


def create_transcription_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import QObject, Qt, QTimer, Signal
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
    panel.capability_generation = 0
    panel.model_import_generation = 0
    panel.model_import_cancel = None
    panel.closing = False
    panel.vad_supported = False

    class CapabilityBridge(QObject):
        finished = Signal(int, object, str)

    class ModelImportBridge(QObject):
        finished = Signal(int, object, str)

    capability_bridge = CapabilityBridge(panel)
    model_import_bridge = ModelImportBridge(panel)
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
        "（auto 代表自動判斷）與 TXT/SRT/VTT；④ 開始轉錄。VAD 預設關閉，只有"
        "明確匯入 VAD 模型並偵測到 CLI 支援後才可啟用；軟體不會自動下載模型。"
    )
    guide.setObjectName("modUsageGuide")
    guide.setWordWrap(True)
    page.addWidget(guide)

    model_card = QFrame()
    model_card.setObjectName("card")
    model_layout = QGridLayout(model_card)
    model_file = QLineEdit()
    model_file.setReadOnly(True)
    model_file.setPlaceholderText("選擇本機 whisper.cpp GGML/GGUF 模型")
    choose_model = QPushButton("選擇模型")
    model_id = QLineEdit()
    model_id.setPlaceholderText("模型 ID，例如 base-zh")
    model_hash = QLineEdit()
    model_hash.setPlaceholderText("確認來源公布的 64 位 SHA-256")
    model_kind = QComboBox()
    model_kind.setAccessibleName("匯入模型用途")
    model_kind.addItem("語音辨識模型", "speech")
    model_kind.addItem("VAD 語音活動模型", "vad")
    import_model = QPushButton("驗證並匯入")
    import_model.setObjectName("primary")
    model_import_status = QLabel("模型驗證與複製會在背景執行，不會阻塞介面。")
    model_import_status.setObjectName("sectionSubtitle")
    model_import_status.setWordWrap(True)
    model_layout.addWidget(QLabel("模型檔"), 0, 0)
    model_layout.addWidget(model_file, 0, 1, 1, 4)
    model_layout.addWidget(choose_model, 0, 5)
    model_layout.addWidget(QLabel("用途"), 1, 0)
    model_layout.addWidget(model_kind, 1, 1)
    model_layout.addWidget(QLabel("模型 ID"), 1, 2)
    model_layout.addWidget(model_id, 1, 3)
    model_layout.addWidget(model_hash, 1, 4)
    model_layout.addWidget(import_model, 1, 5)
    model_layout.addWidget(model_import_status, 2, 0, 1, 6)
    page.addWidget(model_card)

    job_card = QFrame()
    job_card.setObjectName("card")
    grid = QGridLayout(job_card)
    source_text = QLineEdit()
    source_text.setReadOnly(True)
    source_text.setPlaceholderText("尚未選擇音訊或影片")
    choose_source = QPushButton("選擇來源")
    models = QComboBox()
    models.setAccessibleName("語音辨識模型")
    vad_enabled = QCheckBox("啟用 VAD")
    vad_enabled.setToolTip("預設關閉；可減少長段靜音的處理，但可能改變字幕分段。")
    vad_enabled.setEnabled(False)
    vad_models = QComboBox()
    vad_models.setAccessibleName("VAD 語音活動模型")
    vad_models.setEnabled(False)
    detect_vad = QPushButton("偵測 VAD 支援")
    detect_vad.setObjectName("ghost")
    vad_status = QLabel("尚未偵測 whisper-cli VAD 能力；一般轉錄不受影響。")
    vad_status.setObjectName("sectionSubtitle")
    vad_status.setWordWrap(True)
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
    grid.addWidget(vad_enabled, 2, 0)
    grid.addWidget(vad_models, 2, 1, 1, 2)
    grid.addWidget(detect_vad, 2, 3)
    grid.addWidget(vad_status, 3, 0, 1, 4)
    grid.addWidget(output_text, 4, 0, 1, 3)
    grid.addWidget(choose_output, 4, 3)
    formats = QHBoxLayout()
    formats.addWidget(txt)
    formats.addWidget(srt)
    formats.addWidget(vtt)
    formats.addStretch()
    formats.addWidget(submit)
    grid.addLayout(formats, 5, 0, 1, 4)
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
        selected_vad = vad_models.currentData()
        models.clear()
        for model in service.models.list_models("speech"):
            models.addItem(f"{model.model_id}（{model.size / 1024**2:.0f} MB）", model.model_id)
        vad_models.clear()
        for model in service.models.list_models("vad"):
            vad_models.addItem(
                f"{model.model_id}（{model.size / 1024**2:.0f} MB）",
                model.model_id,
            )
        if selected is not None:
            index = models.findData(selected)
            if index >= 0:
                models.setCurrentIndex(index)
        if selected_vad is not None:
            index = vad_models.findData(selected_vad)
            if index >= 0:
                vad_models.setCurrentIndex(index)
        supports_vad = panel.vad_supported
        vad_models.setEnabled(supports_vad and vad_models.count() > 0)
        vad_enabled.setEnabled(supports_vad and vad_models.count() > 0)
        if not vad_enabled.isEnabled():
            vad_enabled.setChecked(False)

    def select_model_file() -> None:
        value, _ = QFileDialog.getOpenFileName(panel, "選擇本機模型", str(Path.home()), "模型 (*.bin *.gguf);;所有檔案 (*)")
        if value:
            model_file.setText(value)
            if not model_id.text():
                model_id.setText(Path(value).stem.casefold().replace("ggml-", "")[:64])

    def import_selected_model() -> None:
        if panel.model_import_cancel is not None:
            return
        if not model_file.text():
            QMessageBox.information(panel, "模型匯入", "請先選擇模型檔。")
            return
        source = Path(model_file.text())
        selected_model_id = model_id.text()
        expected_hash = model_hash.text()
        selected_kind = str(model_kind.currentData())
        panel.model_import_generation += 1
        generation = panel.model_import_generation
        cancel_event = threading.Event()
        panel.model_import_cancel = cancel_event
        for control in (
            model_file,
            choose_model,
            model_id,
            model_hash,
            model_kind,
            import_model,
        ):
            control.setEnabled(False)
        import_model.setText("驗證與複製中…")
        model_import_status.setText("正在背景計算 SHA-256 並複製模型；關閉程式會取消匯入。")

        def worker() -> None:
            try:
                result = service.models.import_model(
                    source,
                    selected_model_id,
                    expected_hash,
                    kind=selected_kind,
                    cancel_event=cancel_event,
                )
            except InterruptedError:
                payload = (None, "cancelled")
            except (OSError, RuntimeError, ValueError) as error:
                payload = (None, str(error))
            else:
                payload = (result, "")
            try:
                model_import_bridge.finished.emit(generation, *payload)
            except RuntimeError:
                return

        threading.Thread(
            target=worker,
            name="speech-model-import",
            daemon=True,
        ).start()

    def finish_model_import(generation: int, result: object, error: str) -> None:
        if panel.closing or generation != panel.model_import_generation:
            return
        panel.model_import_cancel = None
        for control in (
            model_file,
            choose_model,
            model_id,
            model_hash,
            model_kind,
            import_model,
        ):
            control.setEnabled(True)
        import_model.setText("驗證並匯入")
        if error == "cancelled":
            model_import_status.setText("模型匯入已取消，未保留未完成檔案。")
            return
        if error:
            model_import_status.setText("模型匯入失敗；未保留未完成檔案。")
            QMessageBox.warning(panel, "模型匯入", error)
            return
        reload_models()
        model_import_status.setText("模型已驗證 SHA-256 並保存於本機。")
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
        return TranscriptionRequest(
            panel.source,
            str(models.currentData()),
            Path(output_text.text()),
            selected_formats,
            language.text(),
            vad_model_id=(
                str(vad_models.currentData())
                if vad_enabled.isChecked() and vad_models.currentData() is not None
                else None
            ),
        )

    def show_vad_capability(
        generation: int,
        result: object,
        error: str,
    ) -> None:
        if panel.closing or generation != panel.capability_generation:
            return
        detect_vad.setEnabled(True)
        if error or not isinstance(result, TranscriptionCapabilities):
            panel.vad_supported = False
            vad_status.setText(f"VAD 能力偵測失敗：{error or '回傳資料無效'}")
            vad_enabled.setChecked(False)
            vad_enabled.setEnabled(False)
            vad_models.setEnabled(False)
            return
        available = result.supports_vad and vad_models.count() > 0
        panel.vad_supported = result.supports_vad
        vad_enabled.setEnabled(available)
        vad_models.setEnabled(available)
        if result.supports_vad and vad_models.count() == 0:
            vad_status.setText("whisper-cli 支援 VAD；請先匯入明確標示為 VAD 的模型。")
        elif result.supports_vad:
            vad_status.setText("whisper-cli 與 VAD 模型已就緒；選項仍預設關閉。")
        else:
            vad_status.setText("目前 whisper-cli 未同時提供 --vad 與 --vad-model。")
            vad_enabled.setChecked(False)

    def detect_vad_capability() -> None:
        panel.capability_generation += 1
        generation = panel.capability_generation
        detect_vad.setEnabled(False)
        vad_status.setText("正在背景偵測 whisper-cli VAD 能力…")

        def worker() -> None:
            try:
                result = service.capabilities(refresh=True)
            except (OSError, RuntimeError, ValueError) as caught:
                capability_bridge.finished.emit(generation, None, str(caught))
            else:
                capability_bridge.finished.emit(generation, result, "")

        threading.Thread(
            target=worker,
            name="whisper-vad-capability",
            daemon=True,
        ).start()

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
    model_import_bridge.finished.connect(finish_model_import)
    choose_source.clicked.connect(select_source)
    choose_output.clicked.connect(select_output)
    detect_vad.clicked.connect(detect_vad_capability)
    capability_bridge.finished.connect(show_vad_capability)
    submit.clicked.connect(enqueue)
    cancel.clicked.connect(cancel_selected)
    timer = QTimer(panel)
    timer.setInterval(1500)
    timer.timeout.connect(refresh)
    timer.start()
    panel.timer = timer
    def shutdown() -> None:
        panel.closing = True
        panel.capability_generation += 1
        panel.model_import_generation += 1
        if panel.model_import_cancel is not None:
            panel.model_import_cancel.set()
        timer.stop()

    panel.shutdown = shutdown
    panel.model_kind = model_kind
    panel.vad_enabled = vad_enabled
    panel.vad_models = vad_models
    panel.detect_vad = detect_vad
    panel.vad_status = vad_status
    panel.capability_bridge = capability_bridge
    panel.model_import_bridge = model_import_bridge
    reload_models()
    refresh()
    return panel
