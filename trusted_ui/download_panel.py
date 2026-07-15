"""Transport-neutral website download panel."""

from __future__ import annotations

import threading
from pathlib import Path

from contracts.media_options_v1 import FORMAT_PRESETS_V1
from contracts.media_analysis_v1 import (
    MediaAnalysisContractError,
    parse_media_formats,
    parse_media_languages,
)
from contracts.playlist_v1 import PlaylistEntryV1
from contracts.discovery_v1 import DiscoveryItemV1
from core.downloads.archive import DuplicateDownloadError
from core.downloads.batch_import import (
    BatchImportIssue,
    BatchImportResult,
    build_import_requests,
    parse_batch_import,
)
from core.downloads.models import (
    DownloadRequest,
    DownloadState,
    DownloadTask,
)
from core.downloads.playlist_batch import build_playlist_requests
from core.downloads.playlist_transfer import import_playlist_entries
from core.downloads.preflight import preflight_download_batch
from core.downloads.preparation import (
    available_preset_ids,
    build_batch_preview,
    download_option_lines,
    estimate_preset_bytes,
    format_detail_lines,
    human_bytes,
    suggest_output_filename,
)
from core.downloads.split_batch import build_split_requests
from core.mod_groups import BuiltinModGroupError, load_builtin_mod_group
from core.site_routing import classify_site_url
from core.settings import SettingsService, normalized_download_workers
from trusted_ui.batch_import_dialog import show_batch_import_dialog
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.empty_state import create_empty_state
from trusted_ui.playlist_dialog import show_playlist_dialog
from trusted_ui.recovery_dialog import show_recovery_dialog
from trusted_ui.split_dialog import show_split_dialog
from trusted_ui.theme import COLORS
from trusted_ui.youtube_workspace import (
    create_youtube_workspace,
    is_youtube_playlist_url,
    merge_download_urls,
)


ACTIVE_REFRESH_INTERVAL_MS = 500
IDLE_REFRESH_INTERVAL_MS = 1500
HIDDEN_REFRESH_INTERVAL_MS = 2500


def site_workspace_text(site_family: str, locale: object) -> dict[str, str]:
    """Read the pinned site-MOD translation selected by the trusted core."""

    try:
        return dict(load_builtin_mod_group(site_family, locale=locale).workspace)
    except BuiltinModGroupError:
        site_label = "YouTube" if site_family == "youtube" else "Bilibili"
        return {
            "title": f"{site_label} 下載工作區",
            "subtitle": f"{site_label} 網址與選項只在此工作區處理。",
            "enable": f"啟用 {site_label} 主 MOD",
            "url_label": f"{site_label} 網址",
            "placeholder": f"每行貼上一個 {site_label} 網址",
            "initial_preview": f"輸入 {site_label} 網址後可讀取資訊。",
            "wrong_site": (
                f"此頁只接受 {site_label} 網址；請切換到對應網站工作區。"
            ),
        }


def download_refresh_interval(
    tasks: tuple[DownloadTask, ...], *, visible: bool
) -> int:
    """Choose a responsive interval without polling an idle or hidden UI heavily."""

    if not visible:
        return HIDDEN_REFRESH_INTERVAL_MS
    if any(
        task.state in {DownloadState.QUEUED, DownloadState.RUNNING}
        for task in tasks
    ):
        return ACTIVE_REFRESH_INTERVAL_MS
    return IDLE_REFRESH_INTERVAL_MS


def discovery_item_for_task(task: DownloadTask) -> DiscoveryItemV1 | None:
    request = task.request
    title = request.source_title or task.title
    if not title:
        return None
    return DiscoveryItemV1(
        video_id=request.source_video_id or request.url,
        url=request.url,
        title=title[:300],
        artist=request.source_artist[:200],
        duration=None,
        language=request.source_language[:32],
        category=request.source_category[:100] or "video",
        thumbnail_url="",
    )


def safe_task_output_path(task: DownloadTask) -> Path | None:
    """Return a completed task output only when it remains a safe regular file."""

    if task.state is not DownloadState.COMPLETED or not task.output_path:
        return None
    try:
        output_root = task.request.output_dir.resolve()
        output_path = Path(task.output_path).resolve()
        if (
            not output_path.is_relative_to(output_root)
            or not output_path.is_file()
            or output_path.is_symlink()
        ):
            return None
        return output_path
    except OSError:
        return None


def task_detail_summary(task: DownloadTask) -> str:
    """Build bounded, useful selected-task detail text for the compact UI."""

    title = " ".join((task.title or task.request.source_title).split())
    if not title:
        title = task.request.url
    if len(title) > 160:
        title = f"{title[:157]}…"
    error = " ".join(task.error.split())
    if error:
        if len(error) > 600:
            error = f"{error[:597]}…"
        label = "失敗原因" if task.state is DownloadState.FAILED else "狀態訊息"
        return f"{title}\n{label}：{error}"
    if task.state is DownloadState.COMPLETED:
        output = safe_task_output_path(task)
        if output is not None:
            return f"{title}\n輸出：{output}"
        return f"{title}\n任務已完成，但輸出檔案已移動或目前不存在。"
    try:
        destination = task.request.output_dir.resolve()
    except OSError:
        destination = task.request.output_dir
    return f"{title}\n目標：{destination}"


def download_render_signature(
    tasks: tuple[DownloadTask, ...],
) -> tuple[tuple[object, ...], ...]:
    """Return the minimal UI-visible queue state used to suppress redraws."""

    return tuple(
        (
            task.task_id,
            task.state,
            task.title,
            task.progress,
            task.speed,
            task.eta,
            task.error,
            task.output_path,
            task.request.priority,
            task.pause_requested.is_set(),
        )
        for task in tasks
    )


def create_download_panel(
    context: object,
    parent: object = None,
    *,
    site_family: str = "youtube",
) -> object:
    if site_family not in {"youtube", "bilibili"}:
        raise ValueError("download workspace site family is unsupported")
    provider_id = "youtube" if site_family == "youtube" else "bilibili"
    site_label = "YouTube" if site_family == "youtube" else "Bilibili"
    from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
    from PySide6.QtGui import QAction, QColor, QDesktopServices
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QLayout,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class InfoBridge(QObject):
        finished = Signal(object, str)

    class RecoveryBridge(QObject):
        finished = Signal(object, str)

    class SplitBridge(QObject):
        finished = Signal(object, object, str)

    class PlaylistBridge(QObject):
        finished = Signal(object, str)

    class DownloadPanel(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.site_family = site_family
            self.provider_id = provider_id
            self.workspace_text = site_workspace_text(
                site_family,
                getattr(getattr(context, "settings", None), "language", "zh-TW"),
            )
            self.info_bridge = InfoBridge()
            self.info_bridge.finished.connect(self.show_info)
            self.recovery_bridge = RecoveryBridge()
            self.recovery_bridge.finished.connect(self.show_recovery_results)
            self.split_bridge = SplitBridge()
            self.split_bridge.finished.connect(self.show_split_results)
            self.playlist_bridge = PlaylistBridge()
            self.playlist_bridge.finished.connect(self.show_playlist_results)
            self.pending_recovery_request: DownloadRequest | None = None
            self.confirmed_split_plan = None
            self.analyzed_url = ""
            self.analyzed_info: dict[str, object] = {}
            self.analyzed_formats = ()
            self.analyzed_audio_languages = ()
            self.analyzed_subtitle_languages = ()
            self.filename_manually_edited = False
            self.render_signature: tuple[object, ...] | None = None
            self.rendered_task_ids: tuple[str, ...] = ()
            shell = QVBoxLayout(self)
            shell.setContentsMargins(0, 0, 0, 0)
            self.scroll_area = QScrollArea()
            self.scroll_area.setObjectName("workspaceScroll")
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
            self.workspace_title = QLabel(self.workspace_text["title"])
            self.workspace_title.setObjectName("sectionTitle")
            self.workspace_subtitle = QLabel(self.workspace_text["subtitle"])
            self.workspace_subtitle.setObjectName("sectionSubtitle")
            titles.addWidget(self.workspace_title)
            titles.addWidget(self.workspace_subtitle)
            heading.addLayout(titles)
            heading.addStretch()
            self.provider_badge = QLabel()
            self.provider_badge.setObjectName("providerBadge")
            heading.addWidget(self.provider_badge)
            page.addLayout(heading)

            self.youtube_workspace = None
            if site_family == "youtube":
                self.youtube_workspace = create_youtube_workspace(
                    context,
                    self.append_youtube_search_urls,
                    self,
                )
                page.addWidget(self.youtube_workspace)

            input_card = QFrame()
            input_card.setObjectName("card")
            input_layout = QVBoxLayout(input_card)
            input_layout.setContentsMargins(16, 14, 16, 14)
            input_layout.setSpacing(10)

            provider_ids = {
                status.provider_id for status in context.download_providers.statuses()
            }
            top_controls = QHBoxLayout()
            self.enabled = QCheckBox(self.workspace_text["enable"])
            self.enabled.setEnabled(provider_id in provider_ids)
            self.enabled.setChecked(
                context.download_providers.is_enabled(provider_id)
            )
            if provider_id not in provider_ids:
                self.enabled.setText(
                    f"{site_label} MOD 不可用（完整性檢查失敗）"
                )
            self.enabled.toggled.connect(self.toggle_provider)
            top_controls.addWidget(self.enabled)
            top_controls.addStretch()
            worker_label = QLabel("同時工作")
            worker_label.setObjectName("fieldLabel")
            top_controls.addWidget(worker_label)
            self.worker_count = QComboBox()
            self.worker_count.setToolTip("同時執行 1 至 4 個下載工作")
            for count in range(1, 5):
                self.worker_count.addItem(f"{count} 個", count)
            selected_workers = normalized_download_workers(
                context.settings.download_workers
            )
            self.worker_count.setCurrentIndex(
                self.worker_count.findData(selected_workers)
            )
            self.worker_count.currentIndexChanged.connect(
                self.change_worker_count
            )
            top_controls.addWidget(self.worker_count)
            input_layout.addLayout(top_controls)

            output_row = QHBoxLayout()
            output_label = QLabel("輸出")
            output_label.setObjectName("fieldLabel")
            output_row.addWidget(output_label)
            self.output = QLineEdit(str(context.paths.downloads))
            self.output.setMinimumWidth(240)
            choose = QPushButton("選擇資料夾")
            choose.clicked.connect(self.choose_output)
            output_row.addWidget(self.output, 1)
            output_row.addWidget(choose)
            input_layout.addLayout(output_row)

            urls_heading = QHBoxLayout()
            self.urls_label = QLabel(self.workspace_text["url_label"])
            self.urls_label.setObjectName("fieldLabel")
            urls_heading.addWidget(self.urls_label)
            urls_heading.addStretch()
            import_urls = QPushButton("匯入 TXT / CSV…")
            import_urls.setObjectName("ghost")
            import_urls.setToolTip("最多 500 列、2 MiB，匯入前會先顯示檢查結果")
            import_urls.clicked.connect(self.import_batch_file)
            urls_heading.addWidget(import_urls)
            import_playlist = QPushButton("匯入播放清單 ID…")
            import_playlist.setObjectName("ghost")
            import_playlist.clicked.connect(self.import_playlist_file)
            urls_heading.addWidget(import_playlist)
            input_layout.addLayout(urls_heading)
            self.urls = QPlainTextEdit()
            self.urls.setAccessibleName(f"{site_label} 下載網址清單")
            self.urls.setPlaceholderText(self.workspace_text["placeholder"])
            self.urls.setMaximumHeight(104)
            self.urls.textChanged.connect(self.update_site_options)
            input_layout.addWidget(self.urls)

            self.official_bridge_notice = QWidget(self)
            self.official_bridge_notice.setObjectName("officialBridgeNotice")
            official_bridge_layout = QHBoxLayout(self.official_bridge_notice)
            official_bridge_layout.setContentsMargins(0, 0, 0, 0)
            official_bridge_layout.setSpacing(8)
            self.official_bridge_message = QLabel()
            self.official_bridge_message.setObjectName("dependencySummary")
            self.official_bridge_message.setProperty("dependencyState", "warning")
            self.official_bridge_message.setAccessibleName("官方工具下載限制")
            self.official_bridge_message.setWordWrap(True)
            official_bridge_layout.addWidget(self.official_bridge_message, 1)
            self.open_official_bridge = QPushButton("前往網站 MOD 備選")
            self.open_official_bridge.setObjectName("ghost")
            self.open_official_bridge.setAccessibleName("開啟網站 MOD 備選官方工具")
            self.open_official_bridge.clicked.connect(
                self.open_official_bridge_catalog
            )
            official_bridge_layout.addWidget(self.open_official_bridge)
            self.official_bridge_notice.hide()
            self.official_bridge_id = ""
            # Official bridges and other website candidates belong to their
            # own workspaces/MOD pages, never to YouTube or Bilibili.

            preview_row = QHBoxLayout()
            self.preview = QLabel(self.workspace_text["initial_preview"])
            self.preview.setObjectName("preview")
            self.preview.setWordWrap(True)
            self.read_info = QPushButton("讀取網址資訊")
            self.read_info.clicked.connect(self.analyze_first)
            self.expand_playlist = QPushButton("展開播放清單")
            self.expand_playlist.clicked.connect(self.prepare_playlist)
            self.prepare_split = QPushButton("準備切割")
            self.prepare_split.setVisible(False)
            self.prepare_split.clicked.connect(self.prepare_split_preview)
            preview_row.addWidget(self.preview, 1)
            preview_row.addWidget(self.prepare_split)
            preview_row.addWidget(self.expand_playlist)
            preview_row.addWidget(self.read_info)
            input_layout.addLayout(preview_row)

            options = QHBoxLayout()
            options.setSpacing(8)
            priority_label = QLabel("優先級")
            priority_label.setObjectName("fieldLabel")
            options.addWidget(priority_label)
            self.priority = QComboBox()
            self.priority.addItem("低", -5)
            self.priority.addItem("一般", 0)
            self.priority.addItem("高", 5)
            self.priority.addItem("最高", 10)
            self.priority.setCurrentIndex(1)
            options.addWidget(self.priority)
            start_label = QLabel("開始秒數")
            start_label.setObjectName("fieldLabel")
            options.addWidget(start_label)
            self.start_time = QLineEdit()
            self.start_time.setPlaceholderText("從頭")
            self.start_time.setMaximumWidth(100)
            options.addWidget(self.start_time)
            end_label = QLabel("結束秒數")
            end_label.setObjectName("fieldLabel")
            options.addWidget(end_label)
            self.end_time = QLineEdit()
            self.end_time.setPlaceholderText("到結尾")
            self.end_time.setMaximumWidth(100)
            options.addWidget(self.end_time)
            options.addStretch()
            self.add_download = QPushButton("加入下載佇列")
            self.add_download.setObjectName("primary")
            self.add_download.clicked.connect(self.add_batch)
            options.addWidget(self.add_download)
            input_layout.addLayout(options)

            media_options = QHBoxLayout()
            media_options.setSpacing(8)
            format_label = QLabel("下載格式")
            format_label.setObjectName("fieldLabel")
            media_options.addWidget(format_label)
            self.format_preset = QComboBox()
            self.format_preset.setAccessibleName("下載格式")
            for preset in FORMAT_PRESETS_V1:
                self.format_preset.addItem(preset.label, preset.preset_id)
            media_options.addWidget(self.format_preset)
            subtitle_label = QLabel("字幕")
            subtitle_label.setObjectName("fieldLabel")
            media_options.addWidget(subtitle_label)
            self.subtitle_mode = QComboBox()
            self.subtitle_mode.setAccessibleName("字幕模式")
            self.subtitle_mode.addItem("不下載字幕", "none")
            self.subtitle_mode.addItem("指定語言", "selected")
            self.subtitle_mode.addItem("全部可用字幕", "all")
            media_options.addWidget(self.subtitle_mode)
            self.subtitle_languages = QLineEdit()
            self.subtitle_languages.setPlaceholderText("語言，例如 zh-TW,en")
            self.subtitle_languages.setMaximumWidth(220)
            self.subtitle_languages.setVisible(False)
            self.subtitle_mode.currentIndexChanged.connect(
                lambda: self.subtitle_languages.setVisible(
                    self.subtitle_mode.currentData() == "selected"
                )
            )
            media_options.addWidget(self.subtitle_languages)
            self.danmaku_xml = QCheckBox("保留彈幕 XML", self)
            self.danmaku_xml.setToolTip(
                "只下載為獨立 XML 檔，不會燒錄到影片；僅在輸入全為 Bilibili 時顯示"
            )
            self.danmaku_xml.setVisible(False)
            self.danmaku_xml.toggled.connect(self.update_danmaku_options)
            if site_family == "bilibili":
                media_options.addWidget(self.danmaku_xml)
            self.danmaku_ass = QCheckBox("轉為 ASS", self)
            self.danmaku_ass.setToolTip(
                "產生相容離線播放器的 ASS，原始 XML 仍會保留"
            )
            self.danmaku_ass.setVisible(False)
            self.danmaku_ass.toggled.connect(self.update_danmaku_options)
            if site_family == "bilibili":
                media_options.addWidget(self.danmaku_ass)
            self.danmaku_mkv = QCheckBox("嵌入 MKV", self)
            self.danmaku_mkv.setToolTip(
                "使用 FFmpeg 無重新編碼封裝；失敗時保留原影片、XML 與 ASS"
            )
            self.danmaku_mkv.setVisible(False)
            if site_family == "bilibili":
                media_options.addWidget(self.danmaku_mkv)
            self.format_preset.currentIndexChanged.connect(
                self.update_danmaku_options
            )
            self.format_preset.currentIndexChanged.connect(
                self.update_download_preparation
            )
            media_options.addStretch()
            input_layout.addLayout(media_options)

            naming_options = QHBoxLayout()
            naming_label = QLabel("輸出檔名")
            naming_label.setObjectName("fieldLabel")
            naming_options.addWidget(naming_label)
            self.output_filename = QLineEdit()
            self.output_filename.setAccessibleName("輸出檔名預覽")
            self.output_filename.setMaxLength(180)
            self.output_filename.setPlaceholderText(
                "讀取單一網址資訊後自動產生；可自行修改"
            )
            self.output_filename.textEdited.connect(
                lambda: setattr(self, "filename_manually_edited", True)
            )
            naming_options.addWidget(self.output_filename, 1)
            self.preparation_preview = QLabel("尚未取得實際格式與容量資訊")
            self.preparation_preview.setObjectName("preview")
            self.preparation_preview.setWordWrap(True)
            naming_options.addWidget(self.preparation_preview, 1)
            input_layout.addLayout(naming_options)
            page.addWidget(input_card)

            stats = QHBoxLayout()
            stats.setSpacing(10)
            self.stat_values: dict[str, QLabel] = {}
            for key, label in (
                ("all", "全部任務"),
                ("active", "進行中"),
                ("done", "已完成"),
                ("failed", "需處理"),
            ):
                card = QFrame()
                card.setObjectName("statCard")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(14, 10, 14, 10)
                card_layout.setSpacing(1)
                value = QLabel("0")
                value.setObjectName("statValue")
                caption = QLabel(label)
                caption.setObjectName("statLabel")
                card_layout.addWidget(value)
                card_layout.addWidget(caption)
                stats.addWidget(card, 1)
                self.stat_values[key] = value
            page.addLayout(stats)

            self.table = QTableWidget(0, 6)
            self.table.setAccessibleName("下載工作佇列")
            self.table.setAccessibleDescription(
                "顯示下載名稱、狀態、進度、速度、剩餘時間與優先級"
            )
            self.table.setHorizontalHeaderLabels(
                ["標題 / 網址", "狀態", "進度", "速度", "剩餘", "優先級"]
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
            for column in (3, 4, 5):
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )
            self.task_stack = QStackedWidget()
            self.task_empty = create_empty_state(
                "尚無下載任務",
                "貼上已啟用網站 MOD 支援的網址，進度會顯示在這裡。",
                "↓",
            )
            self.task_stack.addWidget(self.task_empty)
            self.task_stack.addWidget(self.table)
            page.addWidget(self.task_stack, 1)

            self.task_detail_card = QFrame()
            self.task_detail_card.setObjectName("taskDetailCard")
            task_detail_layout = QHBoxLayout(self.task_detail_card)
            task_detail_layout.setContentsMargins(12, 8, 8, 8)
            task_detail_layout.setSpacing(8)
            self.task_detail_text = QLabel()
            self.task_detail_text.setObjectName("taskDetailText")
            self.task_detail_text.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.task_detail_text.setWordWrap(True)
            task_detail_layout.addWidget(self.task_detail_text, 1)
            self.copy_error_button = QPushButton("複製錯誤")
            self.copy_error_button.setObjectName("ghost")
            self.copy_error_button.clicked.connect(self.copy_selected_error)
            task_detail_layout.addWidget(self.copy_error_button)
            self.open_result_button = QPushButton("開啟檔案位置")
            self.open_result_button.clicked.connect(self.open_selected_output)
            task_detail_layout.addWidget(self.open_result_button)
            self.task_detail_card.hide()
            page.addWidget(self.task_detail_card)

            actions = QHBoxLayout()
            self.retry_button = QPushButton("重試")
            self.retry_button.clicked.connect(self.retry_selected)
            self.pause_button = QPushButton("暫停")
            self.pause_button.clicked.connect(self.toggle_pause_selected)
            batch_control = QPushButton("批次控制")
            batch_menu = QMenu(batch_control)
            self.pause_all_action = QAction("全部暫停", batch_menu)
            self.pause_all_action.triggered.connect(self.pause_all_tasks)
            batch_menu.addAction(self.pause_all_action)
            self.resume_all_action = QAction("全部繼續", batch_menu)
            self.resume_all_action.triggered.connect(self.resume_all_tasks)
            batch_menu.addAction(self.resume_all_action)
            batch_menu.addSeparator()
            export_archive = QAction("匯出下載封存 ID…", batch_menu)
            export_archive.triggered.connect(self.export_archive_file)
            batch_menu.addAction(export_archive)
            import_archive = QAction("匯入下載封存 ID…", batch_menu)
            import_archive.triggered.connect(self.import_archive_file)
            batch_menu.addAction(import_archive)
            batch_control.setMenu(batch_menu)
            self.cancel_button = QPushButton("取消任務")
            self.cancel_button.setObjectName("danger")
            self.cancel_button.clicked.connect(self.cancel_selected)
            open_folder = QPushButton("開啟下載資料夾")
            open_folder.clicked.connect(self.open_output)
            self.clear_button = QPushButton("清除已結束紀錄")
            self.clear_button.setObjectName("ghost")
            self.clear_button.clicked.connect(self.clear_finished)
            actions.addWidget(self.retry_button)
            actions.addWidget(self.pause_button)
            actions.addWidget(batch_control)
            self.recovery_button = QPushButton("失敗項目找替代")
            self.recovery_button.clicked.connect(self.recover_selected)
            actions.addWidget(self.recovery_button)
            actions.addWidget(self.cancel_button)
            actions.addWidget(open_folder)
            actions.addStretch()
            actions.addWidget(self.clear_button)
            page.addLayout(actions)
            self.table.itemSelectionChanged.connect(self.update_action_state)
            self.table.itemDoubleClicked.connect(self.open_selected_output)

            self.update_provider_badge()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh)
            self.timer.start(IDLE_REFRESH_INTERVAL_MS)
            self.refresh()
            events = getattr(context, "events", None)
            if events is not None:
                events.subscribe(
                    "builtin_mod.changed", self.handle_builtin_mod_changed
                )
                events.subscribe("ui.language.changed", self.apply_site_language)
            self.update_site_options()

        def apply_site_language(self, payload: object = None) -> None:
            locale = (
                payload.get("locale")
                if isinstance(payload, dict)
                else getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            self.workspace_text = site_workspace_text(self.site_family, locale)
            self.workspace_title.setText(self.workspace_text["title"])
            self.workspace_subtitle.setText(self.workspace_text["subtitle"])
            self.urls_label.setText(self.workspace_text["url_label"])
            self.urls.setPlaceholderText(self.workspace_text["placeholder"])
            provider_ids = {
                status.provider_id for status in context.download_providers.statuses()
            }
            self.enabled.setText(
                self.workspace_text["enable"]
                if self.provider_id in provider_ids
                else f"{self.workspace_text['enable']}（不可用）"
            )

        def handle_builtin_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            changed_provider_id = payload.get("provider_id")
            if changed_provider_id == self.provider_id:
                self.enabled.blockSignals(True)
                self.enabled.setChecked(
                    context.download_providers.is_enabled(self.provider_id)
                )
                self.enabled.blockSignals(False)
                self.update_provider_badge()
                self.update_site_options()
            if changed_provider_id in {"youtube-recovery", "youtube-auto-split"}:
                self.update_action_state()
            if changed_provider_id == "youtube-search" and self.youtube_workspace:
                self.youtube_workspace.refresh_availability()

        def append_youtube_search_urls(self, selected_urls: tuple[str, ...]) -> None:
            """Bring search results into the existing reviewed download flow."""

            before = tuple(
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            )
            merged = merge_download_urls(self.urls.toPlainText(), selected_urls)
            self.urls.setPlainText("\n".join(merged))
            added = max(0, len(merged) - len(dict.fromkeys(before)))
            self.preview.setText(
                f"已從 YouTube 搜尋帶入 {added} 筆新網址；"
                "請確認格式、字幕、開始／結束時間與播放清單選項後再加入佇列。"
            )
            self.urls.setFocus()

        def update_action_state(self) -> None:
            task = self.selected_task()
            state = task.state if task is not None else None
            self.task_detail_card.setVisible(task is not None)
            if task is not None:
                self.task_detail_text.setText(task_detail_summary(task))
                self.task_detail_text.setToolTip(task.error or task.output_path)
                detail_state = (
                    "failed"
                    if state is DownloadState.FAILED
                    else "completed"
                    if state is DownloadState.COMPLETED
                    else "active"
                )
                self.task_detail_text.setProperty("taskState", detail_state)
                self.task_detail_text.style().unpolish(self.task_detail_text)
                self.task_detail_text.style().polish(self.task_detail_text)
            else:
                self.task_detail_text.clear()
                self.task_detail_text.setToolTip("")
            output_path = safe_task_output_path(task) if task is not None else None
            self.open_result_button.setEnabled(output_path is not None)
            self.copy_error_button.setVisible(bool(task and task.error))
            self.copy_error_button.setEnabled(bool(task and task.error))
            self.retry_button.setEnabled(
                state in {DownloadState.FAILED, DownloadState.CANCELLED}
            )
            pause_requested = bool(task and task.pause_requested.is_set())
            self.pause_button.setText(
                "繼續" if state is DownloadState.PAUSED else "暫停"
            )
            self.pause_button.setEnabled(
                state
                in {
                    DownloadState.QUEUED,
                    DownloadState.RUNNING,
                    DownloadState.PAUSED,
                }
                and not pause_requested
            )
            self.cancel_button.setEnabled(
                state
                in {
                    DownloadState.QUEUED,
                    DownloadState.RUNNING,
                    DownloadState.PAUSED,
                }
            )
            recovery_available = (
                state is DownloadState.FAILED
                and self.pending_recovery_request is None
                and task is not None
                and self.provider_id_for_url(task.request.url) == "youtube"
                and "youtube-recovery"
                in {status.provider_id for status in context.discovery.statuses()}
                and context.discovery.is_enabled("youtube-recovery")
            )
            self.recovery_button.setEnabled(recovery_available)
            self.clear_button.setEnabled(
                any(
                    task.state
                    in {
                        DownloadState.COMPLETED,
                        DownloadState.FAILED,
                        DownloadState.CANCELLED,
                    }
                    for task in context.download_queue.snapshots()
                )
            )
            tasks = context.download_queue.snapshots()
            self.pause_all_action.setEnabled(
                any(
                    item.state in {DownloadState.QUEUED, DownloadState.RUNNING}
                    and not item.pause_requested.is_set()
                    for item in tasks
                )
            )
            self.resume_all_action.setEnabled(
                any(item.state is DownloadState.PAUSED for item in tasks)
            )

        def update_provider_badge(self) -> None:
            status = next(
                (
                    item
                    for item in context.download_providers.statuses()
                    if item.provider_id == self.provider_id
                ),
                None,
            )
            available = bool(status and status.available)
            active = bool(status and status.enabled)
            state = "已啟用" if active else "未啟用" if available else "不可用"
            self.provider_badge.setText(f"{site_label} MOD {state}")
            self.provider_badge.setProperty("active", active)
            self.provider_badge.style().unpolish(self.provider_badge)
            self.provider_badge.style().polish(self.provider_badge)

        def toggle_provider(self, enabled: bool) -> None:
            self.toggle_download_provider(self.provider_id, enabled)

        def toggle_download_provider(self, provider_id: str, enabled: bool) -> None:
            set_builtin_mod_enabled(context, provider_id, enabled)
            self.update_provider_badge()
            self.update_site_options()

        def update_site_options(self) -> None:
            urls = [
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            ]
            wrong_site = any(
                (route := classify_site_url(url)) is None
                or route.site_family != self.site_family
                for url in urls
            )
            self.add_download.setEnabled(bool(urls) and not wrong_site)
            if wrong_site:
                self.preview.setText(self.workspace_text["wrong_site"])
            is_bilibili_batch = (
                self.site_family == "bilibili" and bool(urls) and not wrong_site
            )
            self.danmaku_xml.setVisible(is_bilibili_batch)
            if not is_bilibili_batch:
                self.danmaku_xml.setChecked(False)
            single_item = len(urls) <= 1
            self.output_filename.setEnabled(single_item)
            self.output_filename.setToolTip(
                "" if single_item else "批量下載會為每個項目各自產生檔名"
            )
            self.update_danmaku_options()

        def open_official_bridge_catalog(self) -> None:
            if not self.official_bridge_id:
                return
            from trusted_ui.plugin_manager import show_plugin_manager

            show_plugin_manager(
                context,
                self,
                initial_tab="site-catalog",
                bridge_id=self.official_bridge_id,
            )

        def update_download_preparation(self) -> None:
            if not self.analyzed_info:
                self.preparation_preview.setText("尚未取得實際格式與容量資訊")
                return
            preset_id = str(self.format_preset.currentData())
            if not self.filename_manually_edited:
                self.output_filename.setText(
                    suggest_output_filename(
                        str(self.analyzed_info.get("title") or "media"),
                        str(self.analyzed_info.get("id") or ""),
                        preset_id,
                    )
                )
            estimated = estimate_preset_bytes(self.analyzed_formats, preset_id)
            known_sizes = sum(
                item.estimated_bytes is not None for item in self.analyzed_formats
            )
            audio_label = ", ".join(self.analyzed_audio_languages) or "未標示"
            subtitle_label = ", ".join(self.analyzed_subtitle_languages) or "無"
            self.preparation_preview.setText(
                f"實際格式 {len(self.analyzed_formats)} 種 · "
                f"含容量資訊 {known_sizes} 種 · 音軌 {audio_label} · "
                f"字幕 {subtitle_label} · 此預設估計 {human_bytes(estimated)}"
            )
            self.preparation_preview.setToolTip(
                "\n".join(format_detail_lines(self.analyzed_formats))
                or "來源未提供格式細節"
            )

        def update_available_presets(self) -> None:
            current = str(self.format_preset.currentData() or "best")
            allowed = set(available_preset_ids(self.analyzed_formats))
            self.format_preset.blockSignals(True)
            self.format_preset.clear()
            for preset in FORMAT_PRESETS_V1:
                if preset.preset_id in allowed:
                    self.format_preset.addItem(preset.label, preset.preset_id)
            index = self.format_preset.findData(current)
            self.format_preset.setCurrentIndex(max(0, index))
            self.format_preset.blockSignals(False)
            self.update_danmaku_options()

        def update_available_subtitles(self) -> None:
            current = str(self.subtitle_mode.currentData() or "none")
            self.subtitle_mode.blockSignals(True)
            self.subtitle_mode.clear()
            self.subtitle_mode.addItem("不下載字幕", "none")
            if self.analyzed_subtitle_languages:
                self.subtitle_mode.addItem("指定語言", "selected")
                self.subtitle_mode.addItem("全部可用字幕", "all")
            index = self.subtitle_mode.findData(current)
            self.subtitle_mode.setCurrentIndex(max(0, index))
            self.subtitle_mode.blockSignals(False)
            self.subtitle_languages.setVisible(
                self.subtitle_mode.currentData() == "selected"
            )

        def update_danmaku_options(self) -> None:
            xml_active = (
                not self.danmaku_xml.isHidden()
                and self.danmaku_xml.isChecked()
            )
            video_format = not str(
                self.format_preset.currentData()
            ).startswith("audio-")
            ass_available = xml_active and video_format
            self.danmaku_ass.setVisible(ass_available)
            if not ass_available:
                self.danmaku_ass.setChecked(False)
            ass_active = (
                not self.danmaku_ass.isHidden()
                and self.danmaku_ass.isChecked()
                and video_format
            )
            self.danmaku_mkv.setVisible(ass_active)
            if not ass_active:
                self.danmaku_mkv.setChecked(False)

        @staticmethod
        def any_download_provider_enabled() -> bool:
            return context.download_providers.is_enabled(provider_id)

        def accepts_url(self, url: str) -> bool:
            route = classify_site_url(url)
            return route is not None and route.site_family == self.site_family

        def reject_wrong_site_urls(self, urls: list[str]) -> bool:
            if all(self.accepts_url(url) for url in urls):
                return False
            QMessageBox.information(
                self,
                self.workspace_text["title"],
                self.workspace_text["wrong_site"],
            )
            return True

        @staticmethod
        def provider_id_for_url(url: str) -> str:
            try:
                return str(context.download_providers.provider_for(url).provider_id)
            except RuntimeError:
                return ""

        def analyze_first(self) -> None:
            urls = [
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            ]
            if not urls:
                QMessageBox.information(self, "影片資訊", "請先輸入網址。")
                return
            if self.reject_wrong_site_urls(urls):
                return
            if len(urls) == 1 and is_youtube_playlist_url(urls[0]):
                self.preview.setText(
                    "已辨識為 YouTube 播放清單；改用播放清單展開與批量選取。"
                )
                self.prepare_playlist()
                return
            self.analyzed_url = urls[0]
            self.analyzed_info = {}
            self.analyzed_formats = ()
            self.analyzed_audio_languages = ()
            self.analyzed_subtitle_languages = ()
            self.filename_manually_edited = False
            self.output_filename.clear()
            self.update_available_presets()
            self.update_available_subtitles()
            self.update_download_preparation()
            self.confirmed_split_plan = None
            self.prepare_split.setVisible(False)
            self.read_info.setEnabled(False)
            self.preview.setText("正在讀取影片資訊…")

            def worker() -> None:
                try:
                    info = context.download_providers.analyze(urls[0])
                    self.info_bridge.finished.emit(info, "")
                except Exception as error:
                    self.info_bridge.finished.emit(None, str(error))

            threading.Thread(target=worker, daemon=True).start()

        def show_info(self, info: object, error: str) -> None:
            self.read_info.setEnabled(True)
            if error:
                self.analyzed_info = {}
                self.prepare_split.setVisible(False)
                self.preview.setText(f"讀取失敗：{error}")
                return
            data = info if isinstance(info, dict) else {}
            self.analyzed_info = data
            try:
                self.analyzed_formats = parse_media_formats(data.get("formats", []))
                self.analyzed_audio_languages = parse_media_languages(
                    data.get("audio_languages", [])
                )
                self.analyzed_subtitle_languages = parse_media_languages(
                    data.get("subtitle_languages", [])
                )
            except MediaAnalysisContractError as format_error:
                self.analyzed_formats = ()
                self.analyzed_audio_languages = ()
                self.analyzed_subtitle_languages = ()
                self.preparation_preview.setText(f"格式資訊無效：{format_error}")
            duration = data.get("duration")
            duration_text = (
                f"{int(duration) // 60}:{int(duration) % 60:02d}"
                if duration
                else "未知長度"
            )
            self.preview.setText(
                f"{data.get('title', '未知標題')}  ·  "
                f"{data.get('uploader', '未知作者')}  ·  {duration_text}"
            )
            part_count = data.get("part_count")
            if isinstance(part_count, int) and part_count > 1:
                self.preview.setText(
                    f"{self.preview.text()}  ·  {part_count} 個分段"
                )
            split_available = (
                bool(duration)
                and self.provider_id_for_url(self.analyzed_url) == "youtube"
                and "youtube-auto-split"
                in {status.provider_id for status in context.discovery.statuses()}
                and context.discovery.is_enabled("youtube-auto-split")
            )
            self.prepare_split.setVisible(split_available)
            self.prepare_split.setEnabled(split_available)
            self.filename_manually_edited = False
            self.update_available_presets()
            self.update_available_subtitles()
            self.update_download_preparation()

        def prepare_playlist(self) -> None:
            if not self.any_download_provider_enabled():
                QMessageBox.information(
                    self, "下載 MOD", "請先啟用支援這個網址的下載 MOD。"
                )
                return
            urls = [
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            ]
            if len(urls) != 1:
                QMessageBox.information(
                    self,
                    "展開播放清單",
                    "請只保留一個播放清單網址；展開後可逐項選擇。",
                )
                return
            if self.reject_wrong_site_urls(urls):
                return
            self.expand_playlist.setEnabled(False)
            self.expand_playlist.setText("正在展開…")

            def worker() -> None:
                try:
                    entries = context.download_providers.playlist(urls[0], limit=500)
                    self.playlist_bridge.finished.emit(entries, "")
                except Exception as error:
                    self.playlist_bridge.finished.emit(None, str(error))

            threading.Thread(target=worker, daemon=True).start()

        def show_playlist_results(self, result: object, error: str) -> None:
            self.expand_playlist.setEnabled(True)
            self.expand_playlist.setText("展開播放清單")
            if error:
                QMessageBox.warning(self, "播放清單展開失敗", error)
                return
            entries = (
                result
                if isinstance(result, tuple)
                and all(isinstance(item, PlaylistEntryV1) for item in result)
                else ()
            )
            if not entries:
                QMessageBox.information(
                    self, "展開播放清單", "播放清單沒有可顯示的項目。"
                )
                return
            selected = show_playlist_dialog(entries, self)
            if selected is None:
                return
            if not selected:
                QMessageBox.information(
                    self, "展開播放清單", "請至少選擇一個可下載項目。"
                )
                return
            self.enqueue_playlist_entries(selected)

        def enqueue_playlist_entries(
            self, selected: tuple[PlaylistEntryV1, ...]
        ) -> None:
            try:
                subtitle_mode, subtitle_languages = self.selected_media_options()
                timed_comment_mode, container_preset = (
                    self.selected_timed_comment_options()
                )
                requests = build_playlist_requests(
                    selected,
                    output_dir=Path(self.output.text()),
                    priority=int(self.priority.currentData()),
                    format_preset=str(self.format_preset.currentData()),
                    subtitle_mode=subtitle_mode,
                    subtitle_languages=subtitle_languages,
                    timed_comment_mode=timed_comment_mode,
                    container_preset=container_preset,
                )
                if not self.confirm_requests(tuple(requests)):
                    return
                context.download_queue.add_batch(list(requests))
            except DuplicateDownloadError:
                QMessageBox.information(
                    self,
                    "重複播放清單項目",
                    "選取項目中有影片已在佇列或成功下載紀錄中，因此整批未加入。",
                )
                return
            except (ValueError, RuntimeError) as queue_error:
                QMessageBox.warning(self, "加入播放清單失敗", str(queue_error))
                return
            self.urls.clear()
            self.preview.setText(
                f"已加入 {len(requests)} 個播放清單項目；不可用項目已保留但未下載。"
            )
            self.refresh()

        def import_playlist_file(self) -> None:
            filename, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "匯入播放清單 ID",
                "",
                "MediaManager 播放清單 (*.json)",
            )
            if not filename:
                return
            try:
                entries = import_playlist_entries(Path(filename))
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "匯入播放清單失敗", str(error))
                return
            selected = show_playlist_dialog(entries, self)
            if selected:
                self.enqueue_playlist_entries(selected)

        def export_archive_file(self) -> None:
            filename, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "匯出下載封存 ID",
                "download-archive.json",
                "MediaManager 下載封存 (*.json)",
            )
            if not filename:
                return
            try:
                count = context.download_queue.archive.export_file(Path(filename))
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "匯出下載封存失敗", str(error))
                return
            QMessageBox.information(
                self, "匯出完成", f"已安全匯出 {count} 個下載封存 ID。"
            )

        def import_archive_file(self) -> None:
            filename, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "匯入下載封存 ID",
                "",
                "MediaManager 下載封存 (*.json)",
            )
            if not filename:
                return
            try:
                preview = context.download_queue.archive.preview_import(
                    Path(filename)
                )
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "匯入下載封存失敗", str(error))
                return
            answer = QMessageBox.question(
                self,
                "確認匯入下載封存",
                f"檔案共 {preview.incoming_count} 個 ID。\n"
                f"新增 {preview.new_count} 個，重複 {preview.duplicate_count} 個。\n\n"
                "只會合併 ID，不會刪除或覆蓋現有紀錄。是否繼續？",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                added = context.download_queue.archive.apply_import(preview)
            except (OSError, ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "匯入下載封存失敗", str(error))
                return
            QMessageBox.information(
                self, "匯入完成", f"已新增 {added} 個下載封存 ID。"
            )

        def prepare_split_preview(self) -> None:
            info = dict(self.analyzed_info)
            source_url = self.analyzed_url
            duration = info.get("duration")
            if (
                not source_url
                or not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or duration <= 0
            ):
                QMessageBox.information(self, "準備切割", "請先讀取有效的影片資訊。")
                return
            source_title = str(info.get("title") or "Untitled")[:300]
            raw_chapters = info.get("chapters")
            chapters = (
                [item for item in raw_chapters if isinstance(item, dict)]
                if isinstance(raw_chapters, list)
                else []
            )
            description = str(info.get("description") or "")[:20_000]
            self.prepare_split.setEnabled(False)
            self.prepare_split.setText("正在準備預覽…")

            def worker() -> None:
                provider = None
                preview_path = None
                try:
                    plan = context.discovery.split_plan(
                        source_url=source_url,
                        source_title=source_title,
                        duration=float(duration),
                        chapters=chapters,
                        description=description,
                    )
                    provider = context.download_providers.provider_for(source_url)
                    preview_path = provider.prepare_audio_preview(
                        source_url,
                        duration=float(duration),
                    )
                    if not plan.segments:
                        plan = context.discovery.split_audio_plan(
                            source_url=source_url,
                            source_title=source_title,
                            duration=float(duration),
                            input_path=preview_path,
                        )
                    self.split_bridge.finished.emit(plan, preview_path, "")
                except Exception as error:
                    if provider is not None and preview_path is not None:
                        provider.cleanup_audio_preview(preview_path)
                    self.split_bridge.finished.emit(None, None, str(error))

            threading.Thread(target=worker, daemon=True).start()

        def show_split_results(
            self, plan: object, preview_path: object, error: str
        ) -> None:
            self.prepare_split.setEnabled(True)
            self.prepare_split.setText("準備切割")
            if error:
                QMessageBox.warning(self, "準備切割失敗", error)
                return
            if plan is None or preview_path is None:
                QMessageBox.warning(self, "準備切割失敗", "沒有可用的切割草稿。")
                return
            provider = context.download_providers.provider_for(plan.source_url)
            try:
                edited = show_split_dialog(plan, preview_path, self)
            finally:
                if not provider.cleanup_audio_preview(Path(preview_path)):
                    QMessageBox.warning(
                        self,
                        "預覽清理",
                        "預覽工作階段未能自動清理，請重新啟動程式後再試。",
                    )
            if edited is not None:
                info = (
                    self.analyzed_info if self.analyzed_url == edited.source_url else {}
                )
                try:
                    requests = build_split_requests(
                        edited,
                        output_dir=Path(self.output.text()),
                        priority=int(self.priority.currentData()),
                        filename_provider=context.discovery,
                        source_video_id=str(info.get("id") or ""),
                        source_artist=str(info.get("uploader") or ""),
                    )
                    context.download_queue.add_batch(list(requests))
                except DuplicateDownloadError:
                    QMessageBox.information(
                        self,
                        "重複切割下載",
                        "其中一個片段已在佇列或下載紀錄中，因此整批未加入。",
                    )
                    return
                except (ValueError, RuntimeError) as queue_error:
                    QMessageBox.warning(self, "加入切割下載失敗", str(queue_error))
                    return
                self.confirmed_split_plan = edited
                self.preview.setText(
                    f"已將 {len(edited.segments)} 個音訊片段加入下載佇列。"
                )
                self.refresh()

        def choose_output(self) -> None:
            folder = QFileDialog.getExistingDirectory(
                self, "選擇輸出資料夾", self.output.text()
            )
            if folder:
                self.output.setText(folder)

        @staticmethod
        def seconds(value: str) -> float | None:
            value = value.strip()
            return float(value) if value else None

        def selected_media_options(self) -> tuple[str, tuple[str, ...]]:
            subtitle_mode = str(self.subtitle_mode.currentData())
            subtitle_languages = tuple(
                dict.fromkeys(
                    item.strip()
                    for item in self.subtitle_languages.text().split(",")
                    if item.strip()
                )
            )
            if subtitle_mode != "selected":
                subtitle_languages = ()
            return subtitle_mode, subtitle_languages

        def selected_timed_comment_options(self) -> tuple[str, str]:
            if self.danmaku_xml.isHidden() or not self.danmaku_xml.isChecked():
                return "none", "auto"
            mode = "ass" if self.danmaku_ass.isChecked() else "source"
            container = "mkv" if self.danmaku_mkv.isChecked() else "auto"
            return mode, container

        def import_batch_file(self) -> None:
            if not self.any_download_provider_enabled():
                QMessageBox.information(
                    self, "下載 MOD", "請先啟用至少一個下載 MOD。"
                )
                return
            filename, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "匯入批量下載清單",
                "",
                "批量清單 (*.txt *.csv)",
            )
            if not filename:
                return
            try:
                parsed = parse_batch_import(Path(filename))
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "無法匯入清單", str(error))
                return

            supported = []
            issues = list(parsed.issues)
            for entry in parsed.entries:
                if not self.accepts_url(entry.url):
                    issues.append(
                        BatchImportIssue(
                            entry.row_number,
                            entry.url,
                            f"此清單只接受 {site_label} 網址",
                        )
                    )
                    continue
                try:
                    context.download_providers.provider_for(entry.url)
                except RuntimeError:
                    issues.append(
                        BatchImportIssue(
                            entry.row_number,
                            entry.url,
                            "目前沒有已啟用的下載 MOD 支援此網址",
                        )
                    )
                else:
                    supported.append(entry)
            preview = BatchImportResult(tuple(supported), tuple(issues))
            selected = show_batch_import_dialog(preview, self)
            if selected is None:
                return
            if not selected:
                QMessageBox.information(
                    self, "批量匯入", "沒有選取可加入下載佇列的項目。"
                )
                return
            try:
                subtitle_mode, subtitle_languages = self.selected_media_options()
                timed_comment_mode, container_preset = (
                    self.selected_timed_comment_options()
                )
                requests = build_import_requests(
                    selected,
                    output_dir=Path(self.output.text()),
                    priority=int(self.priority.currentData()),
                    start_time=self.seconds(self.start_time.text()),
                    end_time=self.seconds(self.end_time.text()),
                    format_preset=str(self.format_preset.currentData()),
                    subtitle_mode=subtitle_mode,
                    subtitle_languages=subtitle_languages,
                    timed_comment_mode=timed_comment_mode,
                    container_preset=container_preset,
                )
                if not self.confirm_requests(tuple(requests)):
                    return
                context.download_queue.add_batch(list(requests))
            except DuplicateDownloadError:
                QMessageBox.information(
                    self,
                    "重複下載",
                    "匯入項目含有已在佇列或成功下載封存中的相同內容。",
                )
                return
            except (ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "無法加入下載", str(error))
                return
            self.urls.clear()
            self.preview.setText(
                f"已從 {Path(filename).name} 加入 {len(requests)} 項；"
                f"檢查時略過 {len(preview.issues)} 項。"
            )
            self.refresh()

        def add_batch(self) -> None:
            if not self.any_download_provider_enabled():
                QMessageBox.information(
                    self, "下載 MOD", "請先啟用至少一個下載 MOD。"
                )
                return
            urls = [
                line.strip()
                for line in self.urls.toPlainText().splitlines()
                if line.strip()
            ]
            if not urls:
                QMessageBox.information(self, "批量下載", "請至少輸入一個網址。")
                return
            if self.reject_wrong_site_urls(urls):
                return
            try:
                subtitle_mode, subtitle_languages = self.selected_media_options()
                timed_comment_mode, container_preset = (
                    self.selected_timed_comment_options()
                )
                requests = []
                for url in urls:
                    info = self.analyzed_info if url == self.analyzed_url else {}
                    requests.append(
                        DownloadRequest(
                            url,
                            Path(self.output.text()),
                            priority=int(self.priority.currentData()),
                            start_time=self.seconds(self.start_time.text()),
                            end_time=self.seconds(self.end_time.text()),
                            source_video_id=str(info.get("id") or ""),
                            source_title=str(info.get("title") or ""),
                            source_artist=str(info.get("uploader") or ""),
                            source_category="video" if info else "",
                            output_filename=(
                                self.output_filename.text().strip()
                                if len(urls) == 1
                                else ""
                            ),
                            format_preset=str(self.format_preset.currentData()),
                            subtitle_mode=subtitle_mode,
                            subtitle_languages=subtitle_languages,
                            timed_comment_mode=timed_comment_mode,
                            container_preset=container_preset,
                        )
                    )
                estimated = (
                    estimate_preset_bytes(
                        self.analyzed_formats,
                        str(self.format_preset.currentData()),
                    )
                    if len(urls) == 1 and urls[0] == self.analyzed_url
                    else None
                )
                if not self.confirm_requests(
                    tuple(requests), estimated_bytes=estimated
                ):
                    return
                context.download_queue.add_batch(requests)
            except DuplicateDownloadError:
                QMessageBox.information(
                    self,
                    "重複下載",
                    "相同影片與時間區段已在佇列或成功下載封存中。",
                )
                return
            except (ValueError, RuntimeError) as error:
                QMessageBox.warning(self, "無法加入下載", str(error))
                return
            self.urls.clear()
            self.refresh()

        def confirm_requests(
            self,
            requests: tuple[DownloadRequest, ...],
            *,
            estimated_bytes: int | None = None,
        ) -> bool:
            context.download_providers.validate_batch(requests)
            preflight = preflight_download_batch(
                requests, estimated_bytes=estimated_bytes
            )
            confirmation = build_batch_preview(
                requests, preflight, estimated_bytes=estimated_bytes
            )
            option_text = "\n".join(download_option_lines(requests[0]))
            filename_line = (
                f"\n檔名：{confirmation.filename}"
                if confirmation.filename
                else "\n檔名：各項目依標題自動產生"
            )
            answer = QMessageBox.question(
                self,
                "確認下載工作",
                f"項目：{confirmation.item_count}\n"
                f"格式：{self.format_preset.currentText()}\n"
                f"{option_text}\n"
                f"估計容量：{human_bytes(confirmation.estimated_bytes)}\n"
                f"磁碟可用：{human_bytes(confirmation.free_bytes)}\n"
                f"輸出：{confirmation.output_directory}{filename_line}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            return answer == QMessageBox.StandardButton.Yes

        def refresh(self) -> None:
            selected_task_id = self.selected_task_id()
            tasks = context.download_queue.snapshots()
            refresh_interval = download_refresh_interval(
                tasks, visible=self.isVisible()
            )
            if self.timer.interval() != refresh_interval:
                self.timer.setInterval(refresh_interval)
            signature = download_render_signature(tasks)
            if signature == self.render_signature:
                return
            self.render_signature = signature
            counts = {
                "all": len(tasks),
                "active": sum(
                    str(task.state) in {"QUEUED", "RUNNING"} for task in tasks
                ),
                "done": sum(str(task.state) == "COMPLETED" for task in tasks),
                "failed": sum(
                    str(task.state) in {"FAILED", "CANCELLED"} for task in tasks
                ),
            }
            for key, value in counts.items():
                self.stat_values[key].setText(str(value))

            states = {
                "QUEUED": ("等待中", COLORS["muted"]),
                "RUNNING": ("下載中", COLORS["info"]),
                "PAUSED": ("已暫停", COLORS["warning"]),
                "COMPLETED": ("完成", COLORS["success"]),
                "FAILED": ("失敗", COLORS["danger"]),
                "CANCELLED": ("已取消", COLORS["warning"]),
            }
            priorities = {-5: "低", 0: "一般", 5: "高", 10: "最高"}
            task_ids = tuple(task.task_id for task in tasks)
            rebuild = (
                task_ids != self.rendered_task_ids
                or self.table.rowCount() != len(tasks)
            )
            previous_signal_state = self.table.blockSignals(True)
            self.table.setUpdatesEnabled(False)
            try:
                if rebuild:
                    self.table.setRowCount(len(tasks))
                self.task_stack.setCurrentWidget(
                    self.table if tasks else self.task_empty
                )
                for row, task in enumerate(tasks):
                    self.table.setRowHeight(row, 44)
                    name = self.table.item(row, 0)
                    if rebuild or name is None:
                        name = QTableWidgetItem()
                        self.table.setItem(row, 0, name)
                    name.setText(task.title or task.request.url)
                    name.setData(Qt.ItemDataRole.UserRole, task.task_id)
                    name.setToolTip(task.error or task.request.url)

                    status = self.table.item(row, 1)
                    if rebuild or status is None:
                        status = QTableWidgetItem()
                        status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(row, 1, status)
                    status_text, status_color = states[str(task.state)]
                    status.setText(status_text)
                    status.setForeground(QColor(status_color))

                    progress = self.table.cellWidget(row, 2)
                    if rebuild or not isinstance(progress, QProgressBar):
                        progress = QProgressBar()
                        progress.setRange(0, 1000)
                        self.table.setCellWidget(row, 2, progress)
                    progress.setValue(int(task.progress * 10))
                    progress.setFormat(f"{task.progress:.0f}%")

                    for column, value in (
                        (3, task.speed or "—"),
                        (4, task.eta or "—"),
                    ):
                        item = self.table.item(row, column)
                        if rebuild or item is None:
                            item = QTableWidgetItem()
                            self.table.setItem(row, column, item)
                        item.setText(value)

                    priority = self.table.item(row, 5)
                    if rebuild or priority is None:
                        priority = QTableWidgetItem()
                        priority.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(row, 5, priority)
                    priority.setText(
                        priorities.get(
                            task.request.priority, str(task.request.priority)
                        )
                    )
                    if task.task_id == selected_task_id:
                        self.table.selectRow(row)
                self.rendered_task_ids = task_ids
            finally:
                self.table.blockSignals(previous_signal_state)
                self.table.setUpdatesEnabled(True)
                self.table.viewport().update()
            self.update_action_state()

        def showEvent(self, event: object) -> None:
            """Refresh immediately when returning from another workspace."""

            super().showEvent(event)
            if hasattr(self, "timer"):
                self.timer.setInterval(ACTIVE_REFRESH_INTERVAL_MS)
                self.render_signature = None
                self.refresh()

        def hideEvent(self, event: object) -> None:
            """Reduce background polling while this workspace is hidden."""

            if hasattr(self, "timer"):
                self.timer.setInterval(HIDDEN_REFRESH_INTERVAL_MS)
            super().hideEvent(event)

        def selected_task_id(self) -> str | None:
            row = self.table.currentRow()
            item = self.table.item(row, 0) if row >= 0 else None
            return item.data(Qt.ItemDataRole.UserRole) if item else None

        def selected_task(self) -> DownloadTask | None:
            task_id = self.selected_task_id()
            if task_id is None:
                return None
            return next(
                (
                    task
                    for task in context.download_queue.snapshots()
                    if task.task_id == task_id
                ),
                None,
            )

        def recover_selected(self) -> None:
            task = self.selected_task()
            if task is None or task.state is not DownloadState.FAILED:
                QMessageBox.information(
                    self,
                    "尋找替代",
                    "請先選擇一個失敗的下載工作。",
                )
                return
            original = discovery_item_for_task(task)
            if original is None:
                QMessageBox.information(
                    self,
                    "尋找替代",
                    "這個工作沒有可用的原始標題，無法安全搜尋替代影片。",
                )
                return
            statuses = {status.provider_id for status in context.discovery.statuses()}
            if "youtube-recovery" not in statuses or not context.discovery.is_enabled(
                "youtube-recovery"
            ):
                QMessageBox.information(
                    self,
                    "尋找替代",
                    "請在網站搜尋頁的搜尋 MOD 選單啟用 YouTube 失效替換。",
                )
                return
            self.pending_recovery_request = task.request
            self.recovery_button.setText("正在尋找…")
            self.update_action_state()

            def worker() -> None:
                try:
                    candidates = context.discovery.replacement_candidates(
                        original, limit=12
                    )
                    self.recovery_bridge.finished.emit(candidates, "")
                except Exception as error:
                    self.recovery_bridge.finished.emit(None, str(error))

            threading.Thread(target=worker, daemon=True).start()

        def show_recovery_results(self, candidates: object, error: str) -> None:
            self.recovery_button.setText("失敗項目找替代")
            original = self.pending_recovery_request
            self.pending_recovery_request = None
            self.update_action_state()
            if error:
                QMessageBox.warning(self, "尋找替代失敗", error)
                return
            values = tuple(candidates) if isinstance(candidates, tuple) else ()
            if not values:
                QMessageBox.information(
                    self,
                    "尋找替代",
                    "目前沒有找到符合最低關聯度的替代候選。",
                )
                return
            if original is not None:
                show_recovery_dialog(context, original, values, self)
                self.refresh()

        def retry_selected(self) -> None:
            task_id = self.selected_task_id()
            try:
                retried = bool(task_id) and context.download_queue.retry(task_id)
            except (OSError, RuntimeError) as error:
                QMessageBox.warning(self, "重試任務失敗", str(error))
                return
            if task_id and not retried:
                QMessageBox.information(
                    self,
                    "重試任務",
                    "只有失敗或已取消的任務可以重試。",
                )

        def toggle_pause_selected(self) -> None:
            task = self.selected_task()
            if task is None:
                return
            try:
                changed = (
                    context.download_queue.resume(task.task_id)
                    if task.state is DownloadState.PAUSED
                    else context.download_queue.pause(task.task_id)
                )
            except (OSError, RuntimeError) as error:
                QMessageBox.warning(self, "變更暫停狀態失敗", str(error))
                return
            if not changed:
                QMessageBox.information(
                    self,
                    "暫停／繼續",
                    "工作狀態已改變，請重新選擇後再試。",
                )
            self.refresh()

        def pause_all_tasks(self) -> None:
            try:
                context.download_queue.pause_all()
            except (OSError, RuntimeError) as error:
                QMessageBox.warning(self, "全部暫停失敗", str(error))
            self.refresh()

        def resume_all_tasks(self) -> None:
            try:
                context.download_queue.resume_all()
            except (OSError, RuntimeError) as error:
                QMessageBox.warning(self, "全部繼續失敗", str(error))
            self.refresh()

        def change_worker_count(self, *_: object) -> None:
            workers = normalized_download_workers(self.worker_count.currentData())
            context.download_queue.set_worker_count(workers)
            context.settings.download_workers = workers
            try:
                SettingsService(
                    Path(context.paths.settings) / "settings.json"
                ).save(context.settings)
            except OSError as error:
                QMessageBox.warning(self, "無法儲存同時工作數", str(error))

        def cancel_selected(self) -> None:
            task_id = self.selected_task_id()
            if task_id:
                try:
                    context.download_queue.cancel(task_id)
                except (OSError, RuntimeError) as error:
                    QMessageBox.warning(self, "取消任務失敗", str(error))

        def clear_finished(self) -> None:
            try:
                count = context.download_queue.clear_finished()
            except (OSError, RuntimeError) as error:
                QMessageBox.warning(self, "清理紀錄失敗", str(error))
                return
            self.refresh()
            if not count:
                QMessageBox.information(self, "清理紀錄", "目前沒有已結束的任務。")

        def copy_selected_error(self) -> None:
            task = self.selected_task()
            if task is not None and task.error:
                QApplication.clipboard().setText(task.error)

        def open_selected_output(self, *_: object) -> None:
            task = self.selected_task()
            output = safe_task_output_path(task) if task is not None else None
            if output is not None:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

        def open_output(self) -> None:
            path = Path(self.output.text()).resolve()
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

        def closeEvent(self, event: object) -> None:
            if self.youtube_workspace is not None:
                self.youtube_workspace.shutdown()
            super().closeEvent(event)

    return DownloadPanel()
