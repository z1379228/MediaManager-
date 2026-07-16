"""Dedicated trusted UI for explicit HTTPS file downloads."""

from __future__ import annotations

import re
import threading
from pathlib import Path

from core.downloads.archive import DuplicateDownloadError
from core.downloads.direct_http_policy import direct_http_url_candidate
from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.downloads.preflight import preflight_download_batch
from core.downloads.preparation import human_bytes
from core.localization import normalized_core_locale
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.download_panel import download_refresh_interval, safe_task_output_path


_TEXT = {
    "zh-TW": {
        "title": "Direct HTTP 下載",
        "subtitle": "只接受明確 HTTPS 檔案網址；不解析網頁、不接管其他網站 MOD。",
        "enable": "啟用 Direct HTTP 主 MOD",
    },
    "zh-CN": {
        "title": "Direct HTTP 下载",
        "subtitle": "只接受明确 HTTPS 文件网址；不解析网页、不接管其他网站 MOD。",
        "enable": "启用 Direct HTTP 主 MOD",
    },
    "en": {
        "title": "Direct HTTP Downloads",
        "subtitle": "Explicit HTTPS files only; no page extraction or site-MOD takeover.",
        "enable": "Enable Direct HTTP main MOD",
    },
    "ja": {
        "title": "Direct HTTP ダウンロード",
        "subtitle": "明示的な HTTPS ファイル専用。Web 解析やサイト MOD の代替はしません。",
        "enable": "Direct HTTP メイン MOD を有効化",
    },
}


def _direct_tasks(context: object) -> tuple[DownloadTask, ...]:
    return tuple(
        task
        for task in context.download_queue.snapshots()
        if task.request.source_category == "direct-http"
    )


def create_direct_http_workspace(context: object, parent: object = None) -> object:
    from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QCheckBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class InfoBridge(QObject):
        finished = Signal(int, object, str)

    class DirectHttpWorkspace(QWidget):
        site_family = "direct-http"
        provider_id = "direct-http"

        def __init__(self) -> None:
            super().__init__(parent)
            self.info_bridge = InfoBridge(self)
            self.info_bridge.finished.connect(self.show_info)
            self.info_generation = 0
            self.info_busy = False
            self.analyzed_url = ""
            self.render_signature: tuple[object, ...] | None = None
            self.events = getattr(context, "events", None)

            page = QVBoxLayout(self)
            page.setContentsMargins(2, 4, 2, 2)
            page.setSpacing(12)
            heading = QHBoxLayout()
            titles = QVBoxLayout()
            self.title = QLabel()
            self.title.setObjectName("sectionTitle")
            self.subtitle = QLabel()
            self.subtitle.setObjectName("sectionSubtitle")
            self.subtitle.setWordWrap(True)
            titles.addWidget(self.title)
            titles.addWidget(self.subtitle)
            heading.addLayout(titles, 1)
            self.badge = QLabel()
            self.badge.setObjectName("providerBadge")
            heading.addWidget(self.badge)
            page.addLayout(heading)

            card = QFrame()
            card.setObjectName("card")
            form = QVBoxLayout(card)
            form.setContentsMargins(16, 14, 16, 14)
            form.setSpacing(10)
            self.enabled = QCheckBox()
            self.enabled.setObjectName("directHttpEnabled")
            self.enabled.toggled.connect(self.toggle_provider)
            form.addWidget(self.enabled)

            output_row = QHBoxLayout()
            output_row.addWidget(QLabel("輸出資料夾"))
            self.output = QLineEdit(str(context.paths.downloads))
            self.output.setAccessibleName("Direct HTTP 輸出資料夾")
            output_row.addWidget(self.output, 1)
            choose = QPushButton("選擇資料夾")
            choose.clicked.connect(self.choose_output)
            output_row.addWidget(choose)
            form.addLayout(output_row)

            self.urls = QPlainTextEdit()
            self.urls.setAccessibleName("Direct HTTP HTTPS 檔案網址")
            self.urls.setPlaceholderText(
                "每行一個完整 HTTPS 檔案網址，例如 https://downloads.example.org/file.zip"
            )
            self.urls.setMaximumHeight(110)
            self.urls.textChanged.connect(self.update_state)
            form.addWidget(self.urls)

            option_row = QHBoxLayout()
            option_row.addWidget(QLabel("單檔檔名（選填）"))
            self.output_filename = QLineEdit()
            self.output_filename.setMaxLength(180)
            option_row.addWidget(self.output_filename, 1)
            option_row.addWidget(QLabel("預期 SHA-256（選填）"))
            self.expected_sha256 = QLineEdit()
            self.expected_sha256.setMaxLength(64)
            self.expected_sha256.setPlaceholderText("64 位十六進位")
            self.expected_sha256.textChanged.connect(self.update_state)
            option_row.addWidget(self.expected_sha256, 1)
            form.addLayout(option_row)

            action_row = QHBoxLayout()
            self.preview = QLabel("尚未輸入直接檔案網址。")
            self.preview.setObjectName("preview")
            self.preview.setWordWrap(True)
            action_row.addWidget(self.preview, 1)
            self.read_info = QPushButton("讀取檔案資訊")
            self.read_info.clicked.connect(self.analyze_first)
            action_row.addWidget(self.read_info)
            self.add_download = QPushButton("加入 Direct HTTP 佇列")
            self.add_download.setObjectName("primary")
            self.add_download.clicked.connect(self.add_batch)
            action_row.addWidget(self.add_download)
            form.addLayout(action_row)
            page.addWidget(card)

            self.table = QTableWidget(0, 4)
            self.table.setHorizontalHeaderLabels(
                ["檔案 / 網址", "狀態", "進度", "速度"]
            )
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.verticalHeader().hide()
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(2, 130)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.table.itemSelectionChanged.connect(self.update_task_actions)
            page.addWidget(self.table, 1)

            controls = QHBoxLayout()
            self.retry = QPushButton("重試")
            self.retry.clicked.connect(self.retry_selected)
            self.pause = QPushButton("暫停")
            self.pause.clicked.connect(self.pause_selected)
            self.cancel = QPushButton("停止")
            self.cancel.setObjectName("danger")
            self.cancel.clicked.connect(self.cancel_selected)
            self.open_result = QPushButton("開啟檔案位置")
            self.open_result.clicked.connect(self.open_selected)
            for control in (self.retry, self.pause, self.cancel, self.open_result):
                controls.addWidget(control)
            controls.addStretch()
            page.addLayout(controls)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh)
            self.timer.start(1000)
            if self.events is not None:
                self.events.subscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.subscribe("ui.language.changed", self.apply_language)
            self.apply_language()
            self.sync_provider()
            self.update_state()
            self.refresh()

        def _urls(self) -> tuple[str, ...]:
            return tuple(
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            )

        def apply_language(self, _payload: object = None) -> None:
            locale = normalized_core_locale(
                getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            text = _TEXT[locale]
            self.title.setText(text["title"])
            self.subtitle.setText(text["subtitle"])
            self.enabled.setText(text["enable"])

        def sync_provider(self) -> None:
            status = next(
                (
                    item
                    for item in context.download_providers.statuses()
                    if item.provider_id == self.provider_id
                ),
                None,
            )
            self.enabled.blockSignals(True)
            self.enabled.setEnabled(bool(status and status.available))
            self.enabled.setChecked(bool(status and status.enabled))
            self.enabled.blockSignals(False)
            state = "已啟用" if status and status.enabled else "未啟用" if status else "不可用"
            self.badge.setText(f"Direct HTTP MOD {state}")
            self.badge.setProperty("active", bool(status and status.enabled))
            self.badge.style().unpolish(self.badge)
            self.badge.style().polish(self.badge)

        def toggle_provider(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(context, self.provider_id, enabled)
            except (KeyError, OSError, RuntimeError) as error:
                self.preview.setText(str(error)[:300])
            self.sync_provider()
            self.update_state()

        def handle_mod_changed(self, payload: object) -> None:
            if isinstance(payload, dict) and payload.get("provider_id") == self.provider_id:
                self.sync_provider()
                self.update_state()

        def update_state(self) -> None:
            urls = self._urls()
            valid = bool(urls) and len(urls) <= 100 and all(
                direct_http_url_candidate(url) for url in urls
            )
            enabled = context.download_providers.is_enabled(self.provider_id)
            checksum = self.expected_sha256.text().strip().casefold()
            checksum_valid = not checksum or bool(re.fullmatch(r"[0-9a-f]{64}", checksum))
            single = len(urls) == 1
            self.output_filename.setEnabled(single)
            self.expected_sha256.setEnabled(single)
            self.read_info.setEnabled(
                enabled and single and valid and not self.info_busy
            )
            self.add_download.setEnabled(enabled and valid and checksum_valid)
            if not urls:
                text = "尚未輸入直接檔案網址。"
            elif len(urls) > 100:
                text = "一次最多 100 個直接檔案網址。"
            elif not valid:
                text = (
                    "只接受公開 HTTPS 檔案副檔名；既有 YouTube、Bilibili、"
                    "Facebook、MEGA 等網域必須使用各自 MOD。"
                )
            elif not checksum_valid:
                text = "SHA-256 必須是 64 位十六進位；批量時不套用單一雜湊。"
            else:
                text = f"已確認 {len(urls)} 個 Direct HTTP 檔案網址。"
            self.preview.setText(text)

        def choose_output(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self, "選擇 Direct HTTP 輸出資料夾", self.output.text()
            )
            if selected:
                self.output.setText(selected)

        def analyze_first(self) -> None:
            urls = self._urls()
            if len(urls) != 1 or not direct_http_url_candidate(urls[0]):
                return
            self.info_generation += 1
            generation = self.info_generation
            self.info_busy = True
            self.analyzed_url = urls[0]
            self.preview.setText("正在驗證 HTTPS 重新導向與檔案資訊…")
            self.update_state()

            def worker() -> None:
                try:
                    info = context.download_providers.analyze(urls[0])
                    self.info_bridge.finished.emit(generation, info, "")
                except Exception as error:
                    self.info_bridge.finished.emit(generation, None, str(error))

            threading.Thread(target=worker, daemon=True).start()

        def show_info(self, generation: int, info: object, error: str) -> None:
            if generation != self.info_generation:
                return
            self.info_busy = False
            self.update_state()
            if error:
                self.preview.setText(f"讀取失敗：{error}")
                return
            data = info if isinstance(info, dict) else {}
            size = data.get("expected_bytes")
            size_text = human_bytes(size if isinstance(size, int) else None)
            self.preview.setText(
                f"{data.get('title', '未命名檔案')} · {data.get('content_type', '未知類型')} · {size_text}"
            )
            if not self.output_filename.text().strip():
                self.output_filename.setText(str(data.get("title") or "")[:180])

        def add_batch(self) -> None:
            urls = self._urls()
            if not urls or len(urls) > 100 or not all(
                direct_http_url_candidate(url) for url in urls
            ):
                return
            filename = self.output_filename.text().strip() if len(urls) == 1 else ""
            checksum = self.expected_sha256.text().strip().casefold() if len(urls) == 1 else ""
            options = (("expected_sha256", checksum),) if checksum else ()
            try:
                requests = tuple(
                    DownloadRequest(
                        url,
                        Path(self.output.text()),
                        source_category="direct-http",
                        output_filename=filename,
                        provider_options=options,
                    )
                    for url in urls
                )
                context.download_providers.validate_batch(requests)
                preflight_download_batch(requests)
            except (OSError, RuntimeError, ValueError) as error:
                QMessageBox.warning(self, "Direct HTTP 設定無效", str(error))
                return
            answer = QMessageBox.question(
                self,
                "確認 Direct HTTP 下載",
                f"檔案：{len(requests)} 個\n輸出：{self.output.text()}\n"
                f"SHA-256：{'下載後驗證' if checksum else '未指定'}\n\n"
                "此 MOD 不會解析登入頁、串流播放頁或未知網頁。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                context.download_queue.add_batch(list(requests))
            except DuplicateDownloadError:
                QMessageBox.information(self, "重複工作", "檔案已在佇列或下載封存中。")
                return
            self.urls.clear()
            self.output_filename.clear()
            self.expected_sha256.clear()
            self.refresh()

        def selected_task(self) -> DownloadTask | None:
            rows = self.table.selectionModel().selectedRows()
            if not rows:
                return None
            item = self.table.item(rows[0].row(), 0)
            task_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            return next(
                (task for task in _direct_tasks(context) if task.task_id == task_id),
                None,
            )

        def refresh(self) -> None:
            tasks = _direct_tasks(context)
            interval = download_refresh_interval(tasks, visible=self.isVisible())
            if self.timer.interval() != interval:
                self.timer.setInterval(interval)
            signature = tuple(
                (task.task_id, task.state, task.title, task.progress, task.speed)
                for task in tasks
            )
            if signature == self.render_signature:
                return
            selected = self.selected_task()
            selected_id = selected.task_id if selected else ""
            self.render_signature = signature
            self.table.setRowCount(len(tasks))
            states = {
                DownloadState.QUEUED: "等待中",
                DownloadState.RUNNING: "下載中",
                DownloadState.PAUSED: "已暫停",
                DownloadState.COMPLETED: "已完成",
                DownloadState.FAILED: "失敗",
                DownloadState.CANCELLED: "已停止",
            }
            for row, task in enumerate(tasks):
                title = task.title or task.request.output_filename or task.request.url
                item = QTableWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, task.task_id)
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QTableWidgetItem(states[task.state]))
                progress = QProgressBar()
                progress.setRange(0, 1000)
                progress.setValue(round(task.progress * 10))
                progress.setFormat(f"{task.progress:.1f}%")
                self.table.setCellWidget(row, 2, progress)
                self.table.setItem(row, 3, QTableWidgetItem(task.speed or "—"))
                if task.task_id == selected_id:
                    self.table.selectRow(row)
            self.update_task_actions()

        def update_task_actions(self) -> None:
            task = self.selected_task()
            state = task.state if task else None
            self.retry.setEnabled(state in {DownloadState.FAILED, DownloadState.CANCELLED})
            self.pause.setText("繼續" if state is DownloadState.PAUSED else "暫停")
            self.pause.setEnabled(
                state in {DownloadState.QUEUED, DownloadState.RUNNING, DownloadState.PAUSED}
            )
            self.cancel.setEnabled(
                state in {DownloadState.QUEUED, DownloadState.RUNNING, DownloadState.PAUSED}
            )
            self.open_result.setEnabled(
                safe_task_output_path(task) is not None if task else False
            )

        def retry_selected(self) -> None:
            task = self.selected_task()
            if task:
                context.download_queue.retry(task.task_id)
                self.refresh()

        def pause_selected(self) -> None:
            task = self.selected_task()
            if task:
                if task.state is DownloadState.PAUSED:
                    context.download_queue.resume(task.task_id)
                else:
                    context.download_queue.pause(task.task_id)
                self.refresh()

        def cancel_selected(self) -> None:
            task = self.selected_task()
            if task:
                context.download_queue.cancel(task.task_id)
                self.refresh()

        def open_selected(self) -> None:
            task = self.selected_task()
            output = safe_task_output_path(task) if task else None
            if output is not None:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

        def shutdown(self) -> None:
            self.info_generation += 1
            self.timer.stop()
            if self.events is not None:
                self.events.unsubscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.unsubscribe("ui.language.changed", self.apply_language)

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return DirectHttpWorkspace()
