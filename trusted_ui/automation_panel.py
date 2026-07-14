"""UI for explicitly enabled local automation rules."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def create_automation_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
        QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    )

    service = context.automation
    if service is None:
        raise RuntimeError("Automation service is unavailable")
    panel = QWidget(parent)
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)
    title = QLabel("Automation")
    title.setObjectName("sectionTitle")
    subtitle = QLabel(
        "MOD 與每條規則都必須分別啟用。新增規則預設關閉，不會立即掃描、讀取剪貼簿或連線。"
    )
    subtitle.setObjectName("sectionSubtitle")
    subtitle.setWordWrap(True)
    page.addWidget(title)
    page.addWidget(subtitle)

    card = QFrame()
    card.setObjectName("card")
    grid = QGridLayout(card)
    name = QLineEdit()
    name.setPlaceholderText("規則名稱")
    kind = QComboBox()
    kind.addItem("網址／頻道／播放清單排程", "schedule")
    kind.addItem("監看資料夾", "watch-folder")
    kind.addItem("剪貼簿 HTTPS 網址", "clipboard")
    source = QLineEdit()
    source.setPlaceholderText("HTTPS 網址或資料夾")
    browse_source = QPushButton("選擇資料夾")
    action = QComboBox()
    action.addItem("下載", "download")
    detail = QLineEdit()
    detail.setPlaceholderText("轉檔預設或語音模型 ID（下載可留空）")
    output = QLineEdit()
    output.setPlaceholderText("輸出資料夾（留空使用預設下載位置）")
    browse_output = QPushButton("選擇輸出")
    interval = QSpinBox()
    interval.setRange(1, 43_200)
    interval.setValue(60)
    interval.setSuffix(" 分鐘")
    rate = QSpinBox()
    rate.setRange(1, 100)
    rate.setValue(10)
    window_start = QLineEdit("00:00")
    window_start.setMaximumWidth(70)
    window_end = QLineEdit("23:59")
    window_end.setMaximumWidth(70)
    playlist = QCheckBox("展開播放清單／頻道")
    recursive = QCheckBox("包含子資料夾")
    add_rule = QPushButton("新增關閉中的規則")
    add_rule.setObjectName("primary")
    grid.addWidget(name, 0, 0)
    grid.addWidget(kind, 0, 1)
    grid.addWidget(source, 0, 2, 1, 2)
    grid.addWidget(browse_source, 0, 4)
    grid.addWidget(action, 1, 0)
    grid.addWidget(detail, 1, 1)
    grid.addWidget(output, 1, 2, 1, 2)
    grid.addWidget(browse_output, 1, 4)
    grid.addWidget(interval, 2, 0)
    grid.addWidget(rate, 2, 1)
    window = QHBoxLayout()
    window.addWidget(QLabel("允許時段"))
    window.addWidget(window_start)
    window.addWidget(QLabel("至"))
    window.addWidget(window_end)
    window.addWidget(playlist)
    window.addWidget(recursive)
    grid.addLayout(window, 2, 2, 1, 2)
    grid.addWidget(add_rule, 2, 4)
    page.addWidget(card)

    views = QTabWidget()
    rules = QTableWidget(0, 7)
    rules.setHorizontalHeaderLabels(("狀態", "名稱", "類型", "來源", "動作", "下次執行", "訊息"))
    candidates = QTableWidget(0, 6)
    candidates.setHorizontalHeaderLabels(("狀態", "規則", "來源", "發現時間", "嘗試", "訊息"))
    for table in (rules, candidates):
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().hide()
        table.horizontalHeader().setStretchLastSection(True)
    views.addTab(rules, "規則")
    views.addTab(candidates, "候選帳本")
    page.addWidget(views, 1)
    controls = QHBoxLayout()
    controls.addStretch()
    toggle = QPushButton("切換選取規則")
    remove = QPushButton("刪除選取規則")
    retry = QPushButton("重試選取失敗候選")
    controls.addWidget(toggle)
    controls.addWidget(remove)
    controls.addWidget(retry)
    page.addLayout(controls)

    def update_kind() -> None:
        selected = str(kind.currentData())
        source.setEnabled(selected != "clipboard")
        browse_source.setVisible(selected == "watch-folder")
        playlist.setVisible(selected == "schedule")
        recursive.setVisible(selected == "watch-folder")
        current_action = action.currentData()
        action.clear()
        if selected == "watch-folder":
            action.addItem("Media Convert", "media-convert")
            action.addItem("Speech to Text", "speech-to-text")
        else:
            action.addItem("下載", "download")
        index = action.findData(current_action)
        if index >= 0:
            action.setCurrentIndex(index)

    def choose_source_folder() -> None:
        value = QFileDialog.getExistingDirectory(panel, "選擇監看資料夾", str(Path.home()))
        if value:
            source.setText(value)

    def choose_output_folder() -> None:
        value = QFileDialog.getExistingDirectory(panel, "選擇輸出資料夾", str(Path.home()))
        if value:
            output.setText(value)

    def create_rule() -> None:
        preset = {"action": str(action.currentData())}
        if output.text().strip():
            preset["output_dir"] = output.text().strip()
        if kind.currentData() == "schedule":
            preset["playlist"] = playlist.isChecked()
        elif action.currentData() == "media-convert":
            preset["conversion_preset"] = detail.text().strip() or "remux-copy"
            preset["recursive"] = recursive.isChecked()
        else:
            preset["model_id"] = detail.text().strip()
            preset["formats"] = ["txt", "srt", "vtt"]
            preset["recursive"] = recursive.isChecked()
        try:
            service.create_rule(
                name=name.text(), kind=str(kind.currentData()), source=source.text(),
                preset=preset, interval_minutes=interval.value(),
                window_start=window_start.text(), window_end=window_end.text(),
                rate_limit=rate.value(),
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "Automation 規則", str(error))
            return
        QMessageBox.information(panel, "Automation 規則", "規則已建立但仍是關閉狀態；確認內容後再啟用。")
        refresh()

    def selected_rule() -> object | None:
        cell = rules.item(rules.currentRow(), 0) if rules.currentRow() >= 0 else None
        return cell.data(Qt.ItemDataRole.UserRole) if cell is not None else None

    def toggle_rule() -> None:
        rule = selected_rule()
        if rule is None:
            return
        if not rule.enabled:
            answer = QMessageBox.question(panel, "啟用自動化規則", "啟用後可能掃描資料夾、讀取剪貼簿網址或連線分析。確定啟用？")
            if answer != QMessageBox.StandardButton.Yes:
                return
        service.set_rule_enabled(rule.rule_id, not rule.enabled)
        refresh()

    def remove_rule() -> None:
        rule = selected_rule()
        if rule is not None and QMessageBox.question(panel, "刪除規則", f"刪除「{rule.name}」及其候選帳本？") == QMessageBox.StandardButton.Yes:
            service.remove_rule(rule.rule_id)
            refresh()

    def retry_candidate() -> None:
        cell = candidates.item(candidates.currentRow(), 0) if candidates.currentRow() >= 0 else None
        candidate = cell.data(Qt.ItemDataRole.UserRole) if cell is not None else None
        if candidate is not None and candidate.state == "FAILED":
            service.retry_candidate(candidate.candidate_key)
            refresh()

    def refresh() -> None:
        rule_rows = service.list_rules()
        rules.setRowCount(len(rule_rows))
        rule_names = {rule.rule_id: rule.name for rule in rule_rows}
        for row, rule in enumerate(rule_rows):
            next_run = datetime.fromtimestamp(rule.next_run).strftime("%Y-%m-%d %H:%M") if rule.next_run else "—"
            values = ("啟用" if rule.enabled else "關閉", rule.name, rule.kind, rule.source or "剪貼簿 HTTPS", str(rule.preset.get("action", "")), next_run, rule.last_error or "—")
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, rule)
                table_value = value
                cell.setToolTip(table_value)
                rules.setItem(row, column, cell)
        candidate_rows = service.list_candidates(limit=200)
        candidates.setRowCount(len(candidate_rows))
        for row, candidate in enumerate(candidate_rows):
            values = (candidate.state, rule_names.get(candidate.rule_id, candidate.rule_id), candidate.source, datetime.fromtimestamp(candidate.discovered_at).strftime("%Y-%m-%d %H:%M:%S"), str(candidate.attempts), candidate.error or candidate.dispatch_token or "—")
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, candidate)
                cell.setToolTip(value)
                candidates.setItem(row, column, cell)

    def poll() -> None:
        if any(rule.enabled and rule.kind == "clipboard" for rule in service.list_rules()):
            service.observe_clipboard(QApplication.clipboard().text())
        refresh()

    kind.currentIndexChanged.connect(update_kind)
    browse_source.clicked.connect(choose_source_folder)
    browse_output.clicked.connect(choose_output_folder)
    add_rule.clicked.connect(create_rule)
    toggle.clicked.connect(toggle_rule)
    remove.clicked.connect(remove_rule)
    retry.clicked.connect(retry_candidate)
    timer = QTimer(panel)
    timer.setInterval(2_000)
    timer.timeout.connect(poll)
    timer.start()
    panel.timer = timer
    panel.shutdown = timer.stop
    update_kind()
    refresh()
    return panel
