"""Dedicated trusted workspace for public MEGA shares."""

from __future__ import annotations

import threading
from pathlib import Path

from core.dependency_health import find_executable
from core.downloads.archive import DuplicateDownloadError
from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.downloads.preflight import preflight_download_batch
from core.mod_groups import load_builtin_mod_group
from core.site_routing import classify_site_url
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.download_panel import download_refresh_interval, safe_task_output_path


_CONTENT_LABELS = {
    "video": "影片",
    "archive": "壓縮檔",
    "document": "文件",
    "audio": "音訊",
    "image": "圖片",
    "unknown": "下載後判定",
}
_CONTENT_SUFFIXES = {
    "video": {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"},
    "archive": {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
    "document": {
        ".pdf",
        ".doc",
        ".docx",
        ".odt",
        ".txt",
        ".rtf",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".epub",
    },
    "audio": {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"},
}


def mega_content_kind(filename: str) -> str:
    """Classify a disclosed output name without guessing from a share ID."""

    suffixes = [suffix.casefold() for suffix in Path(filename).suffixes]
    if "".join(suffixes[-2:]) in {".tar.gz", ".tar.bz2", ".tar.xz"}:
        return "archive"
    suffix = suffixes[-1] if suffixes else ""
    for content_kind, values in _CONTENT_SUFFIXES.items():
        if suffix in values:
            return content_kind
    return "unknown"


def _mega_tasks(context: object) -> tuple[DownloadTask, ...]:
    tasks = []
    for task in context.download_queue.snapshots():
        route = classify_site_url(task.request.url)
        if route is not None and route.site_family == "mega":
            tasks.append(task)
    return tuple(tasks)


def create_mega_workspace(context: object, parent: object = None) -> object:
    """Create a MEGA-only UI with no audiovisual download controls."""

    from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
    from PySide6.QtGui import QColor, QDesktopServices
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLayout,
        QLineEdit,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class InfoBridge(QObject):
        finished = Signal(int, object, str)

    class MegaWorkspace(QWidget):
        site_family = "mega"
        provider_id = "mega"

        def __init__(self) -> None:
            super().__init__(parent)
            self.workspace_text = dict(
                load_builtin_mod_group(
                    "mega",
                    locale=getattr(
                        getattr(context, "settings", None),
                        "language",
                        "zh-TW",
                    ),
                ).workspace
            )
            self.info_bridge = InfoBridge(self)
            self.info_bridge.finished.connect(self.show_info)
            self.info_generation = 0
            self.info_busy = False
            self.analyzed_url = ""
            self.render_signature: tuple[object, ...] | None = None
            self.workspace_title = QLabel(self.workspace_text["title"])
            self.workspace_title.setObjectName("sectionTitle")

            shell = QVBoxLayout(self)
            shell.setContentsMargins(0, 0, 0, 0)
            self.scroll_area = QScrollArea()
            self.scroll_area.setObjectName("workspaceScroll")
            self.scroll_area.setAccessibleName("MEGA 下載工作區捲動內容")
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            self.scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.scroll_content = QWidget()
            page = QVBoxLayout(self.scroll_content)
            page.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            page.setContentsMargins(2, 4, 2, 2)
            page.setSpacing(12)
            self.scroll_area.setWidget(self.scroll_content)
            shell.addWidget(self.scroll_area)

            heading = QHBoxLayout()
            titles = QVBoxLayout()
            titles.setSpacing(2)
            self.workspace_subtitle = QLabel(self.workspace_text["subtitle"])
            self.workspace_subtitle.setObjectName("sectionSubtitle")
            self.workspace_subtitle.setWordWrap(True)
            titles.addWidget(self.workspace_title)
            titles.addWidget(self.workspace_subtitle)
            heading.addLayout(titles, 1)
            self.provider_badge = QLabel()
            self.provider_badge.setObjectName("providerBadge")
            heading.addWidget(self.provider_badge)
            page.addLayout(heading)

            input_card = QFrame()
            input_card.setObjectName("card")
            input_layout = QVBoxLayout(input_card)
            input_layout.setContentsMargins(16, 14, 16, 14)
            input_layout.setSpacing(10)

            top = QHBoxLayout()
            self.enabled = QCheckBox(self.workspace_text["enable"])
            provider_ids = {
                status.provider_id for status in context.download_providers.statuses()
            }
            self.enabled.setEnabled("mega" in provider_ids)
            self.enabled.setChecked(context.download_providers.is_enabled("mega"))
            self.enabled.toggled.connect(self.toggle_provider)
            top.addWidget(self.enabled)
            top.addStretch()
            self.dependency_status = QLabel()
            self.dependency_status.setObjectName("dependencySummary")
            top.addWidget(self.dependency_status)
            input_layout.addLayout(top)

            output_row = QHBoxLayout()
            output_label = QLabel("輸出資料夾")
            output_label.setObjectName("fieldLabel")
            output_row.addWidget(output_label)
            self.output = QLineEdit(str(context.paths.downloads))
            self.output.setAccessibleName("MEGA 輸出資料夾")
            output_row.addWidget(self.output, 1)
            choose_output = QPushButton("選擇資料夾")
            choose_output.clicked.connect(self.choose_output)
            output_row.addWidget(choose_output)
            input_layout.addLayout(output_row)

            self.urls_label = QLabel(self.workspace_text["url_label"])
            self.urls_label.setObjectName("fieldLabel")
            input_layout.addWidget(self.urls_label)
            self.urls = QPlainTextEdit()
            self.urls.setAccessibleName("MEGA 公開分享網址")
            self.urls.setPlaceholderText(self.workspace_text["placeholder"])
            self.urls.setMaximumHeight(100)
            self.urls.textChanged.connect(self.update_site_options)
            input_layout.addWidget(self.urls)

            classification_row = QHBoxLayout()
            self.share_icon = QLabel("MEGA")
            self.share_icon.setObjectName("downloadThumbnail")
            self.share_icon.setAccessibleName("MEGA 分享類型")
            self.share_icon.setFixedSize(104, 62)
            self.share_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            classification_row.addWidget(self.share_icon)
            self.preview = QLabel(self.workspace_text["initial_preview"])
            self.preview.setObjectName("preview")
            self.preview.setWordWrap(True)
            classification_row.addWidget(self.preview, 1)
            self.read_info = QPushButton("讀取分享資訊")
            self.read_info.clicked.connect(self.analyze_first)
            classification_row.addWidget(self.read_info)
            input_layout.addLayout(classification_row)

            filename_row = QHBoxLayout()
            self.filename_label = QLabel("指定檔名（僅單檔選填）")
            self.filename_label.setObjectName("fieldLabel")
            filename_row.addWidget(self.filename_label)
            self.output_filename = QLineEdit()
            self.output_filename.setMaxLength(180)
            self.output_filename.setPlaceholderText(
                "例如 backup.zip；留空則沿用 MEGA 提供的原始名稱"
            )
            self.output_filename.textChanged.connect(self.update_content_type)
            filename_row.addWidget(self.output_filename, 1)
            self.content_type = QLabel("類型：下載後判定")
            self.content_type.setObjectName("urlClassification")
            filename_row.addWidget(self.content_type)
            input_layout.addLayout(filename_row)

            split_card = QFrame()
            split_card.setObjectName("subCard")
            split_layout = QVBoxLayout(split_card)
            split_layout.setContentsMargins(12, 10, 12, 10)
            split_layout.setSpacing(8)
            split_heading = QHBoxLayout()
            split_title = QLabel("MEGAcmd 連線分流")
            split_title.setObjectName("fieldLabel")
            split_heading.addWidget(split_title)
            split_heading.addStretch()
            self.custom_transfer = QCheckBox("下載前套用自訂設定")
            self.custom_transfer.setToolTip(
                "只在加入的 MEGA 工作開始時呼叫官方 mega-speedlimit；預設不修改"
            )
            self.custom_transfer.toggled.connect(self.update_transfer_controls)
            split_heading.addWidget(self.custom_transfer)
            split_layout.addLayout(split_heading)

            split_controls = QHBoxLayout()
            connection_label = QLabel("下載連線數")
            connection_label.setObjectName("fieldLabel")
            split_controls.addWidget(connection_label)
            self.download_connections = QComboBox()
            self.download_connections.setAccessibleName("MEGA 下載連線數")
            for count, label in ((1, "1（保守）"), (2, "2"), (4, "4（建議）"), (6, "6（高）")):
                self.download_connections.addItem(label, count)
            self.download_connections.setCurrentIndex(
                self.download_connections.findData(4)
            )
            split_controls.addWidget(self.download_connections)
            speed_label = QLabel("速率上限")
            speed_label.setObjectName("fieldLabel")
            split_controls.addWidget(speed_label)
            self.speed_limit = QSpinBox()
            self.speed_limit.setAccessibleName("MEGA 下載速率上限")
            self.speed_limit.setRange(0, 1024)
            self.speed_limit.setSuffix(" MiB/s")
            self.speed_limit.setSpecialValueText("不限速")
            self.speed_limit.setValue(0)
            split_controls.addWidget(self.speed_limit)
            split_controls.addStretch()
            self.transfer_note = QLabel(
                "此設定控制 MEGAcmd 下載連線，不是影音切段；可能影響同一 MEGAcmd 工作階段。"
            )
            self.transfer_note.setObjectName("dependencySummary")
            self.transfer_note.setWordWrap(True)
            split_layout.addLayout(split_controls)
            split_layout.addWidget(self.transfer_note)
            input_layout.addWidget(split_card)

            action_row = QHBoxLayout()
            priority_label = QLabel("優先級")
            priority_label.setObjectName("fieldLabel")
            action_row.addWidget(priority_label)
            self.priority = QComboBox()
            self.priority.addItem("低", -5)
            self.priority.addItem("一般", 0)
            self.priority.addItem("高", 5)
            self.priority.setCurrentIndex(1)
            action_row.addWidget(self.priority)
            action_row.addStretch()
            self.add_download = QPushButton("加入 MEGA 下載佇列")
            self.add_download.setObjectName("primary")
            self.add_download.clicked.connect(self.add_batch)
            action_row.addWidget(self.add_download)
            input_layout.addLayout(action_row)
            page.addWidget(input_card)

            self.table = QTableWidget(0, 5)
            self.table.setAccessibleName("MEGA 下載工作佇列")
            self.table.setHorizontalHeaderLabels(
                ["MEGA 檔案／資料夾 / 網址", "狀態", "進度", "速度", "剩餘"]
            )
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(False)
            self.table.verticalHeader().hide()
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(2, 130)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self.table.itemSelectionChanged.connect(self.update_action_state)
            self.table.setMinimumHeight(190)
            page.addWidget(self.table, 1)

            controls = QHBoxLayout()
            self.retry_button = QPushButton("重試")
            self.retry_button.clicked.connect(self.retry_selected)
            controls.addWidget(self.retry_button)
            self.pause_button = QPushButton("暫停")
            self.pause_button.setToolTip(
                "可暫停尚未開始的 MEGA 工作；執行中傳輸由 MEGAcmd server 管理"
            )
            self.pause_button.clicked.connect(self.toggle_pause_selected)
            controls.addWidget(self.pause_button)
            self.cancel_button = QPushButton("停止")
            self.cancel_button.setObjectName("danger")
            self.cancel_button.setToolTip(
                "可停止尚未開始的 MEGA 工作；不會用全域命令誤停其他 MEGAcmd 傳輸"
            )
            self.cancel_button.clicked.connect(self.cancel_selected)
            controls.addWidget(self.cancel_button)
            self.open_result_button = QPushButton("開啟檔案位置")
            self.open_result_button.clicked.connect(self.open_selected_output)
            controls.addWidget(self.open_result_button)
            controls.addStretch()
            self.queue_summary = QLabel()
            self.queue_summary.setObjectName("sectionSubtitle")
            controls.addWidget(self.queue_summary)
            page.addLayout(controls)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh)
            self.timer.start(1000)
            self.update_dependency_status()
            self.update_provider_badge()
            self.update_transfer_controls()
            self.update_site_options()
            self.refresh()
            self.events = getattr(context, "events", None)
            if self.events is not None:
                self.events.subscribe("ui.language.changed", self.apply_language)

        def apply_language(self, payload: object = None) -> None:
            locale = (
                payload.get("locale")
                if isinstance(payload, dict)
                else getattr(
                    getattr(context, "settings", None), "language", "zh-TW"
                )
            )
            self.workspace_text = dict(
                load_builtin_mod_group("mega", locale=locale).workspace
            )
            self.workspace_title.setText(self.workspace_text["title"])
            self.workspace_subtitle.setText(self.workspace_text["subtitle"])
            self.enabled.setText(self.workspace_text["enable"])
            self.urls_label.setText(self.workspace_text["url_label"])
            self.urls.setPlaceholderText(self.workspace_text["placeholder"])
            self.update_site_options()

        def update_dependency_status(self) -> None:
            mega_get = find_executable(context.paths.application, "mega-get")
            mega_speedlimit = find_executable(
                context.paths.application, "mega-speedlimit"
            )
            self.mega_get_available = bool(mega_get)
            self.mega_speedlimit_available = bool(mega_speedlimit)
            if self.mega_get_available and self.mega_speedlimit_available:
                text = "官方 mega-get／mega-speedlimit 已偵測"
                state = "ready"
            elif self.mega_get_available:
                text = "mega-get 可用；自訂分流需 mega-speedlimit"
                state = "warning"
            else:
                text = "未偵測到官方 mega-get，暫時只能辨識網址"
                state = "warning"
            self.dependency_status.setText(text)
            self.dependency_status.setProperty("dependencyState", state)
            self.dependency_status.style().unpolish(self.dependency_status)
            self.dependency_status.style().polish(self.dependency_status)

        def update_provider_badge(self) -> None:
            status = next(
                (
                    item
                    for item in context.download_providers.statuses()
                    if item.provider_id == "mega"
                ),
                None,
            )
            available = bool(status and status.available)
            active = bool(status and status.enabled)
            state = "已啟用" if active else "未啟用" if available else "不可用"
            self.provider_badge.setText(f"MEGA MOD {state}")
            self.provider_badge.setProperty("active", active)
            self.provider_badge.style().unpolish(self.provider_badge)
            self.provider_badge.style().polish(self.provider_badge)

        def toggle_provider(self, enabled: bool) -> None:
            set_builtin_mod_enabled(context, "mega", enabled)
            self.update_provider_badge()
            self.update_site_options()

        def choose_output(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self, "選擇 MEGA 輸出資料夾", self.output.text()
            )
            if selected:
                self.output.setText(selected)

        def _urls(self) -> tuple[str, ...]:
            return tuple(
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            )

        def _route_counts(self) -> tuple[int, int, int]:
            files = folders = invalid = 0
            for url in self._urls():
                route = classify_site_url(url)
                if route is None or route.site_family != "mega":
                    invalid += 1
                elif route.resource_kind == "public-file":
                    files += 1
                elif route.resource_kind == "public-folder":
                    folders += 1
                else:
                    invalid += 1
            return files, folders, invalid

        def update_site_options(self) -> None:
            urls = self._urls()
            files, folders, invalid = self._route_counts()
            enabled = context.download_providers.is_enabled("mega")
            too_many = len(urls) > 50
            self.read_info.setEnabled(
                enabled and len(urls) == 1 and invalid == 0 and not self.info_busy
            )
            can_download = (
                enabled
                and bool(urls)
                and not too_many
                and invalid == 0
                and files + folders == len(urls)
                and self.mega_get_available
                and (not self.custom_transfer.isChecked() or self.mega_speedlimit_available)
            )
            self.add_download.setEnabled(can_download)
            filename_available = len(urls) == 1 and files == 1 and folders == 0
            self.output_filename.setEnabled(filename_available)
            self.filename_label.setEnabled(filename_available)
            self.output_filename.setToolTip(
                ""
                if filename_available
                else "整個資料夾或批量工作會沿用 MEGA 提供的名稱"
            )
            if not urls:
                message = "尚未輸入 MEGA 公開分享網址。"
            elif too_many:
                message = "一次最多加入 50 個 MEGA 檔案連結。"
            elif invalid:
                message = self.workspace_text["wrong_site"]
            elif folders:
                message = (
                    f"已辨識 {folders} 個公開資料夾、{files} 個公開檔案；"
                    "資料夾會由官方 mega-get 完整下載，完成後驗證本機樹狀輸出。"
                )
            else:
                message = f"已辨識 {files} 個公開檔案，可加入 MEGA 專屬佇列。"
            self.preview.setText(message)
            self.share_icon.setText("FOLDER" if folders else "FILE" if files else "MEGA")

        def update_content_type(self) -> None:
            content_kind = mega_content_kind(self.output_filename.text().strip())
            self.content_type.setText(f"類型：{_CONTENT_LABELS[content_kind]}")

        def update_transfer_controls(self) -> None:
            active = self.custom_transfer.isChecked()
            self.download_connections.setEnabled(active)
            self.speed_limit.setEnabled(active)
            if active and not self.mega_speedlimit_available:
                self.transfer_note.setText(
                    "尚未偵測到官方 mega-speedlimit；取消自訂設定後仍可使用 mega-get。"
                )
            else:
                self.transfer_note.setText(
                    "此設定控制 MEGAcmd 下載連線，不是影音切段；可能影響同一 MEGAcmd 工作階段。"
                )
            self.update_site_options()

        def analyze_first(self) -> None:
            urls = self._urls()
            if len(urls) != 1:
                return
            self.info_busy = True
            self.info_generation += 1
            generation = self.info_generation
            self.analyzed_url = urls[0]
            self.preview.setText("正在由 MEGA MOD 驗證公開分享資訊…")
            self.update_site_options()

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
            self.update_site_options()
            if error:
                self.preview.setText(f"讀取失敗：{error}")
                return
            data = info if isinstance(info, dict) else {}
            resource_kind = str(data.get("resource_kind") or "")
            content_kind = str(data.get("content_kind") or "unknown")
            kind_text = "公開檔案" if resource_kind == "public-file" else "公開資料夾"
            content_text = _CONTENT_LABELS.get(content_kind, "下載後判定")
            dependency_text = (
                "mega-get 可用"
                if data.get("dependency_available") is True
                else "mega-get 未偵測"
            )
            self.preview.setText(
                f"{data.get('title', 'MEGA 公開分享')} · {kind_text} · "
                f"類型：{content_text} · {dependency_text}"
            )
            self.share_icon.setText("FOLDER" if resource_kind == "public-folder" else "FILE")

        def _provider_options(self) -> tuple[tuple[str, str], ...]:
            if not self.custom_transfer.isChecked():
                return ()
            options = [
                (
                    "download_connections",
                    str(int(self.download_connections.currentData())),
                )
            ]
            speed_mib = self.speed_limit.value()
            if speed_mib:
                options.append(
                    ("download_speed_limit_bps", str(speed_mib * 1024 * 1024))
                )
            return tuple(options)

        def add_batch(self) -> None:
            urls = self._urls()
            files, folders, invalid = self._route_counts()
            if (
                not urls
                or len(urls) > 50
                or invalid
                or files + folders != len(urls)
            ):
                QMessageBox.information(
                    self,
                    "MEGA 下載",
                    "只會加入最多 50 個完整的 MEGA 公開檔案或資料夾連結。",
                )
                return
            filename = self.output_filename.text().strip()
            if filename and (len(urls) != 1 or folders):
                QMessageBox.information(
                    self,
                    "MEGA 檔名",
                    "批量或資料夾下載請留空指定檔名，避免輸出樹互相覆蓋。",
                )
                return
            try:
                requests = []
                for url in urls:
                    route = classify_site_url(url)
                    if route is None or route.site_family != "mega":
                        raise ValueError("MEGA 網址分類已失效")
                    requests.append(
                        DownloadRequest(
                            url=url,
                            output_dir=Path(self.output.text()),
                            priority=int(self.priority.currentData()),
                            output_filename=filename,
                            source_category=(
                                "mega-folder"
                                if route.resource_kind == "public-folder"
                                else "mega-file"
                            ),
                            provider_options=self._provider_options(),
                        )
                    )
                requests = tuple(requests)
                preflight_download_batch(requests)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "MEGA 下載設定無效", str(error))
                return
            transfer_text = (
                f"連線 {self.download_connections.currentData()}；"
                f"速率 {self.speed_limit.text()}"
                if self.custom_transfer.isChecked()
                else "沿用 MEGAcmd 目前設定"
            )
            answer = QMessageBox.question(
                self,
                "確認 MEGA 下載",
                f"公開檔案：{files} 個；公開資料夾：{folders} 個\n"
                f"分流：{transfer_text}\n"
                f"輸出：{self.output.text()}\n\n"
                "檔名與實際檔案類型會由官方 MEGAcmd 下載結果確認。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                context.download_queue.add_batch(list(requests))
            except DuplicateDownloadError:
                QMessageBox.information(
                    self, "重複 MEGA 工作", "其中一個公開分享已在佇列或下載紀錄中。"
                )
                return
            except (OSError, RuntimeError, ValueError) as error:
                QMessageBox.warning(self, "加入 MEGA 佇列失敗", str(error))
                return
            self.urls.clear()
            self.output_filename.clear()
            self.refresh()

        def selected_task(self) -> DownloadTask | None:
            selected = self.table.selectionModel().selectedRows()
            if not selected:
                return None
            item = self.table.item(selected[0].row(), 0)
            task_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            return next(
                (task for task in _mega_tasks(context) if task.task_id == task_id),
                None,
            )

        def refresh(self) -> None:
            selected = self.selected_task()
            selected_id = selected.task_id if selected else ""
            tasks = _mega_tasks(context)
            interval = download_refresh_interval(tasks, visible=self.isVisible())
            if self.timer.interval() != interval:
                self.timer.setInterval(interval)
            signature = tuple(
                (
                    task.task_id,
                    task.state,
                    task.title,
                    task.progress,
                    task.speed,
                    task.eta,
                    task.output_path,
                    task.error,
                    task.pause_requested.is_set(),
                    task.cancel_event.is_set(),
                )
                for task in tasks
            )
            if signature == self.render_signature:
                return
            self.render_signature = signature
            self.table.setRowCount(len(tasks))
            state_labels = {
                DownloadState.QUEUED: "等待中",
                DownloadState.RUNNING: "下載中",
                DownloadState.PAUSED: "已暫停",
                DownloadState.COMPLETED: "已完成",
                DownloadState.FAILED: "失敗",
                DownloadState.CANCELLED: "已停止",
            }
            for row, task in enumerate(tasks):
                title = task.title or task.request.output_filename or task.request.url
                title_item = QTableWidgetItem(title)
                title_item.setData(Qt.ItemDataRole.UserRole, task.task_id)
                title_item.setToolTip(task.error or task.request.url)
                self.table.setItem(row, 0, title_item)
                state_item = QTableWidgetItem(state_labels[task.state])
                if task.state is DownloadState.FAILED:
                    state_item.setForeground(QColor("#ff7b72"))
                self.table.setItem(row, 1, state_item)
                progress = QProgressBar()
                progress.setRange(0, 1000)
                progress.setValue(int(task.progress * 10))
                progress.setFormat(f"{task.progress:.0f}%")
                self.table.setCellWidget(row, 2, progress)
                self.table.setItem(row, 3, QTableWidgetItem(task.speed or "—"))
                self.table.setItem(row, 4, QTableWidgetItem(task.eta or "—"))
                if task.task_id == selected_id:
                    self.table.selectRow(row)
            active = sum(
                task.state in {DownloadState.QUEUED, DownloadState.RUNNING}
                for task in tasks
            )
            failed = sum(task.state is DownloadState.FAILED for task in tasks)
            self.queue_summary.setText(
                f"MEGA 工作 {len(tasks)} · 進行中 {active} · 失敗 {failed}"
            )
            self.update_action_state()

        def update_action_state(self) -> None:
            task = self.selected_task()
            state = task.state if task else None
            self.retry_button.setEnabled(
                state in {DownloadState.FAILED, DownloadState.CANCELLED}
            )
            self.pause_button.setText(
                "繼續" if state is DownloadState.PAUSED else "暫停"
            )
            self.pause_button.setEnabled(
                state in {DownloadState.QUEUED, DownloadState.PAUSED}
            )
            self.cancel_button.setEnabled(
                state in {DownloadState.QUEUED, DownloadState.PAUSED}
            )
            self.open_result_button.setEnabled(
                safe_task_output_path(task) is not None if task else False
            )

        def retry_selected(self) -> None:
            task = self.selected_task()
            if task:
                context.download_queue.retry(task.task_id)
                self.refresh()

        def toggle_pause_selected(self) -> None:
            task = self.selected_task()
            if task is None:
                return
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

        def open_selected_output(self) -> None:
            task = self.selected_task()
            output = safe_task_output_path(task) if task else None
            if output is not None:
                target = output if output.is_dir() else output.parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

        def apply_search_result_metadata(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            title = payload.get("title")
            if isinstance(title, str) and title.strip():
                self.preview.setText(f"已從搜尋結果帶入：{title.strip()[:120]}")

        def shutdown(self) -> None:
            self.info_generation += 1
            self.timer.stop()
            if self.events is not None:
                self.events.unsubscribe(
                    "ui.language.changed", self.apply_language
                )
                self.events = None

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return MegaWorkspace()
