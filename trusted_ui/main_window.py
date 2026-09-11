"""MediaManager trusted desktop shell."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from core.dependency_health import check_dependencies
from core.localization import CORE_LOCALES
from core.downloads.notifications import (
    DownloadCompletionTracker,
    DownloadNotificationCoalescer,
    completion_message,
)
from core.settings import (
    SettingsService,
    SettingsWriteBlockedError,
    normalized_close_behavior,
    normalized_language,
)
from core.startup_registration import create_startup_registration
from core.site_routing import classify_site_url
from core.version import application_display_name
from trusted_ui.app_icon import app_icon_path
from trusted_ui.background import (
    clear_background_copy,
    create_background_widget,
    load_background_path,
    store_background_copy,
)
from trusted_ui.dependency_dialog import (
    dependency_presentation,
    show_dependency_dialog,
)
from trusted_ui.download_panel import create_download_panel
from trusted_ui.idle_state import IdleResourceController
from trusted_ui.optional_workspace_manager import (
    OptionalWorkspaceManager,
    OptionalWorkspaceSpec,
)
from trusted_ui.plugin_manager import show_plugin_manager
from trusted_ui.thumbnail_loader import (
    cancel_thumbnail_clients,
    resume_thumbnail_clients,
)
from trusted_ui.theme import (
    UI_SCALE_VALUES,
    apply_application_theme,
    normalized_ui_scale,
)
from trusted_ui.workspace_navigation import install_workspace_navigation


def security_presentation(mode: object, reason: str | None) -> tuple[str, str, str]:
    value = str(mode)
    if value == "NORMAL":
        return "已驗證", "normal", "核心與發布檔案驗證通過"
    if value == "BLOCKED":
        return "已封鎖", "blocked", reason or "安全檢查已封鎖啟動"
    if value == "SAFE_MODE":
        return "安全模式", "safe", reason or "部分功能已依安全策略停用"
    return "狀態未知", "unknown", reason or value


def configure_workspace_tabs(tabs: object) -> None:
    """Apply the cross-platform tab settings used by the main workspace."""

    tabs.setObjectName("workspaceTabs")
    tabs.setDocumentMode(True)
    tabs.setMovable(False)
    tabs.setAccessibleName("MediaManager 工作區導覽")
    tabs.tabBar().setAccessibleName("工作區分頁")
    tabs.tabBar().setUsesScrollButtons(True)
    # Fusion/Windows can still paint the native tab-bar base even when the
    # pane border is removed by QSS. Against the dark background that base
    # becomes a bright horizontal artifact beside the selected workspace tab.
    tabs.tabBar().setDrawBase(False)


CORE_LANGUAGE_LABELS = tuple(
    (locale.display_name, locale.code) for locale in CORE_LOCALES
)


def populate_core_language_menu(
    menu: object, action_group: object, selected_language: object
) -> tuple[object, ...]:
    """Add the four locales owned by the trusted core to a menu."""

    selected = normalized_language(selected_language)
    menu.addSection("核心介面語言")
    actions = []
    for label, locale in CORE_LANGUAGE_LABELS:
        action = menu.addAction(label)
        action_group.addAction(action)
        action.setCheckable(True)
        action.setData(locale)
        action.setChecked(locale == selected)
        action.setToolTip("由可信核心保存並傳給 MOD；尚未翻譯的文字保留繁體中文")
        actions.append(action)
    return tuple(actions)


def apply_download_prefill(
    download_panel: object, tabs: object, payload: object
) -> bool:
    """Move a bounded trusted search result into the full download setup UI."""

    if not isinstance(payload, dict):
        return False
    raw_url = payload.get("url")
    if not isinstance(raw_url, str) or len(raw_url) > 4096:
        return False
    url = raw_url.strip()
    if not url or "\r" in url or "\n" in url:
        return False
    try:
        parsed = urlsplit(url)
        parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    route = classify_site_url(url)
    panel_family = getattr(download_panel, "site_family", None)
    if route is None or (
        isinstance(panel_family, str)
        and panel_family
        and route.site_family != panel_family
    ):
        return False

    urls = getattr(download_panel, "urls", None)
    preview = getattr(download_panel, "preview", None)
    update_site_options = getattr(download_panel, "update_site_options", None)
    if urls is None or preview is None or not callable(update_site_options):
        return False

    title = payload.get("title")
    provider_id = payload.get("provider_id")
    source = (
        title.strip()[:120]
        if isinstance(title, str) and title.strip()
        else provider_id.strip()[:80]
        if isinstance(provider_id, str) and provider_id.strip()
        else "搜尋結果"
    )
    urls.setPlainText(url)
    update_site_options()
    apply_search_result = getattr(
        download_panel, "apply_search_result_metadata", None
    )
    if callable(apply_search_result):
        apply_search_result(payload)
    preview.setText(
        f"已從「{source}」帶入；請確認格式、分段、字幕與網站專屬選項後再加入佇列。"
    )
    tabs.setCurrentWidget(download_panel)
    urls.setFocus()
    return True


def run_main_window(
    context: object,
    *,
    start_minimized: bool = False,
    initial_prefill: dict[str, str] | None = None,
) -> int:
    from PySide6.QtCore import QEvent, QObject, QTimer, Qt, QUrl, Signal
    from PySide6.QtGui import (
        QAction,
        QActionGroup,
        QDesktopServices,
        QIcon,
        QKeySequence,
        QShortcut,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QStyle,
        QSystemTrayIcon,
        QTabWidget,
        QVBoxLayout,
    )

    class NotificationBridge(QObject):
        changed = Signal(object)
        flush_requested = Signal()

        def __init__(self, parent: object = None) -> None:
            super().__init__(parent)
            self.coalescer = DownloadNotificationCoalescer()
            self.flush_timer = QTimer(self)
            self.flush_timer.setSingleShot(True)
            self.flush_timer.setInterval(100)
            self.flush_timer.setTimerType(Qt.TimerType.CoarseTimer)
            self.flush_timer.timeout.connect(self.flush_pending)
            self.flush_requested.connect(self.schedule_flush)

        def submit(self, task: object) -> None:
            decision = self.coalescer.submit(task)
            if decision.immediate is not None:
                self.changed.emit(decision.immediate)
            if decision.schedule_flush:
                self.flush_requested.emit()

        def schedule_flush(self) -> None:
            if not self.flush_timer.isActive():
                self.flush_timer.start()

        def flush_pending(self) -> None:
            for task in self.coalescer.flush():
                self.changed.emit(task)

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(application_display_name())
            self.setAccessibleName("MediaManager 主視窗")
            self.resize(1180, 780)
            self.setMinimumSize(940, 620)
            self.settings_root = Path(context.paths.settings)
            self.notification_tracker = DownloadCompletionTracker(
                context.download_queue.snapshots()
            )
            self.notification_bridge = NotificationBridge(self)
            self.notification_bridge.changed.connect(self.handle_download_change)
            context.download_queue.subscribe(self.notification_bridge.submit)
            self.system_tray = None
            self.tray_menu = None
            self.idle_resources = IdleResourceController()
            self._shutdown_started = False
            self._force_exit = False
            self.startup_registration = create_startup_registration(
                portable=context.settings.portable_mode
            )
            self.notice_output_dir: Path | None = None
            root = create_background_widget(load_background_path(self.settings_root))
            root.setObjectName("appRoot")
            page = QVBoxLayout(root)
            page.setContentsMargins(22, 18, 22, 14)
            page.setSpacing(14)

            top = QFrame()
            top.setObjectName("topBar")
            header = QHBoxLayout(top)
            header.setContentsMargins(16, 12, 14, 12)
            header.setSpacing(12)
            mark = QLabel("M")
            mark.setObjectName("appMark")
            header.addWidget(mark)
            names = QVBoxLayout()
            names.setSpacing(1)
            title = QLabel("MediaManager")
            title.setObjectName("title")
            subtitle = QLabel("媒體整理與模組化下載工作區")
            subtitle.setObjectName("subtitle")
            names.addWidget(title)
            names.addWidget(subtitle)
            header.addLayout(names)
            header.addStretch()

            mode_text, mode_state, mode_tip = security_presentation(
                context.security.mode,
                context.security.reason,
            )
            mode = QLabel(mode_text)
            mode.setObjectName("badge")
            mode.setProperty("securityState", mode_state)
            mode.setAccessibleName(f"安全狀態：{mode_text}")
            mode.setAccessibleDescription(mode_tip)
            mode.setToolTip(mode_tip)
            header.addWidget(mode)

            dependency_service = getattr(context, "dependencies", None)
            dependency_report = (
                dependency_service.snapshot().report
                if dependency_service is not None
                else check_dependencies(Path(context.paths.application))
            )
            dependency_text, dependency_state, dependency_tip = dependency_presentation(
                dependency_report
            )
            environment = QPushButton(dependency_text)
            environment.setObjectName("environment")
            environment.setProperty("dependencyState", dependency_state)
            environment.setToolTip(dependency_tip + "（Ctrl+E）")
            environment.clicked.connect(
                lambda: show_dependency_dialog(
                    Path(context.paths.application),
                    self,
                    snapshot_service=dependency_service,
                )
            )
            header.addWidget(environment)

            appearance = QPushButton("設定")
            appearance.setObjectName("ghost")
            appearance.setAccessibleName("MediaManager 設定")
            appearance.setToolTip("設定外觀、語言、通知與 Windows 啟動行為")
            appearance_menu = QMenu(appearance)
            choose_background = QAction("選擇背景圖片…", appearance_menu)
            reset_background = QAction("恢復預設背景", appearance_menu)
            appearance_menu.addAction(choose_background)
            appearance_menu.addAction(reset_background)
            appearance_menu.addSeparator()
            self.language_group = QActionGroup(appearance_menu)
            self.language_group.setExclusive(True)
            populate_core_language_menu(
                appearance_menu,
                self.language_group,
                context.settings.language,
            )
            appearance_menu.addSeparator()
            appearance_menu.addSection("介面大小")
            self.ui_scale_group = QActionGroup(appearance_menu)
            self.ui_scale_group.setExclusive(True)
            scale_labels = {
                "compact": "精簡",
                "standard": "標準",
                "large": "大字",
            }
            selected_scale = normalized_ui_scale(context.settings.ui_scale)
            for scale in UI_SCALE_VALUES:
                action = QAction(scale_labels[scale], self.ui_scale_group)
                action.setCheckable(True)
                action.setData(scale)
                action.setChecked(scale == selected_scale)
                appearance_menu.addAction(action)
            appearance_menu.addSeparator()
            self.in_app_notifications = QAction("程式內下載完成提示", appearance_menu)
            self.in_app_notifications.setCheckable(True)
            self.in_app_notifications.setChecked(
                context.settings.in_app_download_notifications is True
            )
            self.system_notifications = QAction("Windows 下載完成通知", appearance_menu)
            self.system_notifications.setCheckable(True)
            self.system_notifications.setChecked(
                context.settings.system_download_notifications is True
            )
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.system_notifications.setEnabled(False)
                self.system_notifications.setToolTip("目前系統通知區不可用")
            appearance_menu.addAction(self.in_app_notifications)
            appearance_menu.addAction(self.system_notifications)
            appearance_menu.addSeparator()
            appearance_menu.addSection("系統")
            self.start_with_windows_action = QAction(
                "Windows 登入後自動啟動（背景待機）",
                appearance_menu,
            )
            self.start_with_windows_action.setCheckable(True)
            if self.startup_registration is None:
                self.start_with_windows_action.setEnabled(False)
                self.start_with_windows_action.setToolTip(
                    "此選項只支援 Windows 使用者工作階段"
                )
            else:
                try:
                    registered = self.startup_registration.is_enabled()
                except OSError:
                    registered = False
                    self.start_with_windows_action.setToolTip(
                        "目前無法讀取 Windows 開機啟動設定"
                    )
                self.start_with_windows_action.setChecked(registered)
            appearance_menu.addAction(self.start_with_windows_action)
            appearance.setMenu(appearance_menu)
            header.addWidget(appearance)

            plugins = QPushButton("MOD 管理")
            plugins.setObjectName("ghost")
            plugins.setToolTip("統一管理內建與外部 MOD（Ctrl+M）")
            plugins.clicked.connect(lambda: show_plugin_manager(context, self))
            header.addWidget(plugins)
            page.addWidget(top)

            tabs = QTabWidget()
            configure_workspace_tabs(tabs)
            self.workspace_navigator = install_workspace_navigation(tabs)
            self.workspace_tabs = tabs

            def create_workspace_placeholder(
                workspace_id: str,
                label: str,
            ) -> object:
                placeholder = QFrame(self)
                placeholder.setObjectName("lazyWorkspacePlaceholder")
                placeholder.setProperty("workspaceId", workspace_id)
                placeholder.setAccessibleName(f"{label}：尚未載入")
                placeholder_layout = QVBoxLayout(placeholder)
                placeholder_layout.setContentsMargins(24, 24, 24, 24)
                title = QLabel(label)
                title.setObjectName("sectionTitle")
                placeholder_layout.addWidget(title)
                note = QLabel("首次開啟此工作區時才會建立介面與資源。")
                note.setObjectName("muted")
                note.setWordWrap(True)
                placeholder_layout.addWidget(note)
                placeholder_layout.addStretch()
                return placeholder

            self.download_panel = create_download_panel(
                context, self, site_family="youtube"
            )
            self.download_panel.setProperty("workspaceId", "youtube")
            tabs.addTab(self.download_panel, self.download_panel.workspace_title.text())
            tabs.setTabToolTip(0, "YouTube 搜尋、播放清單、批量與分段下載")

            self.bilibili_download_panel = None
            self.search_panel = None
            self.library_panel = None

            def create_search_workspace() -> object:
                from trusted_ui.search_panel import create_search_panel

                return create_search_panel(context, self)

            def create_library_workspace() -> object:
                from trusted_ui.library_panel import create_library_panel

                return create_library_panel(context, self)

            self.core_workspace_manager = OptionalWorkspaceManager(
                tabs,
                (
                    OptionalWorkspaceSpec(
                        "bilibili",
                        lambda: True,
                        lambda: True,
                        lambda: create_download_panel(
                            context, self, site_family="bilibili"
                        ),
                        lambda panel: panel.workspace_title.text(),
                        "Bilibili 影片、番劇、分段與彈幕下載",
                        "Bilibili 下載工作區",
                    ),
                    OptionalWorkspaceSpec(
                        "search",
                        lambda: True,
                        lambda: True,
                        create_search_workspace,
                        lambda _panel: "網站搜尋",
                        "單一網站搜尋、替代候選與相似內容",
                        "網站搜尋",
                    ),
                    OptionalWorkspaceSpec(
                        "library",
                        lambda: True,
                        lambda: True,
                        create_library_workspace,
                        lambda _panel: "本機媒體庫",
                        "掃描、篩選與開啟本機媒體",
                        "本機媒體庫",
                    ),
                ),
                placeholder_factory=create_workspace_placeholder,
            )
            self.core_workspace_manager.sync()

            self.site_download_panels: dict[str, object] = {
                "youtube": self.download_panel,
            }
            registered_downloads = {
                status.provider_id for status in context.download_providers.statuses()
            }

            def feature_enabled(provider_id: str) -> bool:
                return any(
                    status.provider_id == provider_id and status.enabled
                    for status in context.features.statuses()
                )

            def create_social_workspace(site_family: str) -> object:
                from trusted_ui.official_social_workspace import (
                    create_official_social_workspace,
                )

                return create_official_social_workspace(
                    context,
                    self,
                    site_family=site_family,
                )

            def create_facebook_workspace() -> object:
                return create_download_panel(context, self, site_family="facebook")

            def create_mega_panel() -> object:
                from trusted_ui.mega_workspace import create_mega_workspace

                return create_mega_workspace(context, self)

            def create_direct_http_panel() -> object:
                from trusted_ui.direct_http_workspace import (
                    create_direct_http_workspace,
                )

                return create_direct_http_workspace(context, self)

            def create_conversion_workspace() -> object:
                from trusted_ui.conversion_panel import create_conversion_panel

                return create_conversion_panel(context, self)

            def create_transfer_workspace() -> object:
                from trusted_ui.transfer_panel import create_transfer_panel

                return create_transfer_panel(context, self)

            def create_transcription_workspace() -> object:
                from trusted_ui.transcription_panel import (
                    create_transcription_panel,
                )

                return create_transcription_panel(context, self)

            def create_automation_workspace() -> object:
                from trusted_ui.automation_panel import create_automation_panel

                return create_automation_panel(context, self)

            self.optional_workspace_manager = OptionalWorkspaceManager(
                tabs,
                (
                    OptionalWorkspaceSpec(
                        "instagram",
                        lambda: feature_enabled("instagram"),
                        lambda: any(
                            status.provider_id == "instagram"
                            for status in context.features.statuses()
                        ),
                        lambda: create_social_workspace("instagram"),
                        lambda panel: panel.title.text(),
                        "Instagram 官方媒體頁與帳號資料匯出工具；不自動擷取內容",
                        "Instagram 官方工具",
                    ),
                    OptionalWorkspaceSpec(
                        "threads",
                        lambda: feature_enabled("threads"),
                        lambda: any(
                            status.provider_id == "threads"
                            for status in context.features.statuses()
                        ),
                        lambda: create_social_workspace("threads"),
                        lambda panel: panel.title.text(),
                        "Threads 官方貼文頁與帳號資料匯出工具；不自動擷取內容",
                        "Threads 官方工具",
                    ),
                    OptionalWorkspaceSpec(
                        "twitter",
                        lambda: feature_enabled("twitter"),
                        lambda: any(
                            status.provider_id == "twitter"
                            for status in context.features.statuses()
                        ),
                        lambda: create_social_workspace("twitter"),
                        lambda panel: panel.title.text(),
                        "X/Twitter 官方貼文頁與帳號資料封存工具；不使用網站自動化",
                        "X 官方工具",
                    ),
                    OptionalWorkspaceSpec(
                        "facebook",
                        lambda: context.download_providers.is_enabled("facebook"),
                        lambda: "facebook" in registered_downloads,
                        create_facebook_workspace,
                        lambda panel: panel.workspace_title.text(),
                        "Facebook 公開影片頁、縮圖與獨立分流下載",
                        "Facebook 下載工作區",
                    ),
                    OptionalWorkspaceSpec(
                        "mega",
                        lambda: context.download_providers.is_enabled("mega"),
                        lambda: "mega" in registered_downloads,
                        create_mega_panel,
                        lambda panel: panel.workspace_title.text(),
                        "MEGA 公開檔案、類型判定與官方 MEGAcmd 連線分流",
                        "MEGA 下載工作區",
                    ),
                    OptionalWorkspaceSpec(
                        "direct-http",
                        lambda: context.download_providers.is_enabled("direct-http"),
                        lambda: "direct-http" in registered_downloads,
                        create_direct_http_panel,
                        lambda panel: panel.title.text(),
                        "明確 HTTPS 檔案、續傳與 SHA-256 驗證；不接管網站 MOD",
                        "Direct HTTP 下載",
                    ),
                    OptionalWorkspaceSpec(
                        "media-convert",
                        lambda: feature_enabled("media-convert"),
                        lambda: context.conversion is not None,
                        create_conversion_workspace,
                        lambda _panel: "格式工廠",
                        "本機轉封裝、轉檔、壓縮、串接與切割",
                        "格式工廠",
                    ),
                    OptionalWorkspaceSpec(
                        "gopeed-transfer",
                        lambda: feature_enabled("gopeed-transfer"),
                        lambda: (
                            context.gopeed is not None
                            and context.p2p_transfer is not None
                        ),
                        create_transfer_workspace,
                        lambda _panel: "Gopeed / P2P",
                        "localhost Gopeed REST 橋接與明確 P2P 傳輸；不自動啟動或開埠",
                        "Gopeed / P2P",
                    ),
                    OptionalWorkspaceSpec(
                        "speech-to-text",
                        lambda: feature_enabled("speech-to-text"),
                        lambda: context.transcription is not None,
                        create_transcription_workspace,
                        lambda _panel: "Speech to Text",
                        "本機語音轉文字與 TXT、SRT、VTT 輸出",
                        "Speech to Text",
                    ),
                    OptionalWorkspaceSpec(
                        "automation",
                        lambda: feature_enabled("automation"),
                        lambda: context.automation is not None,
                        create_automation_workspace,
                        lambda _panel: "Automation",
                        "選用排程、監看資料夾與剪貼簿網址候選",
                        "Automation",
                    ),
                ),
                placeholder_factory=create_workspace_placeholder,
            )

            def sync_materialized_workspaces() -> None:
                self.bilibili_download_panel = (
                    self.core_workspace_manager.panels.get("bilibili")
                )
                self.search_panel = self.core_workspace_manager.panels.get("search")
                self.library_panel = self.core_workspace_manager.panels.get("library")
                for provider_id in ("bilibili", "facebook", "mega"):
                    panel = (
                        self.core_workspace_manager.panels.get(provider_id)
                        or self.optional_workspace_manager.panels.get(provider_id)
                    )
                    if panel is None:
                        self.site_download_panels.pop(provider_id, None)
                    else:
                        self.site_download_panels[provider_id] = panel

            def sync_optional_workspaces(payload: object = None) -> None:
                self.optional_workspace_manager.sync(payload)
                sync_materialized_workspaces()

            context.events.subscribe(
                "builtin_mod.changed", sync_optional_workspaces
            )
            sync_optional_workspaces()

            active_workspace = [tabs.currentWidget()]
            switching_workspace = [False]

            def ensure_selected_workspace(index: int) -> None:
                if self._shutdown_started or switching_workspace[0]:
                    return
                switching_workspace[0] = True
                try:
                    selected = tabs.widget(index) if index >= 0 else None
                    previous = active_workspace[0]
                    if previous is not None and previous is not selected:
                        cancel_thumbnail_clients(previous)
                    self.core_workspace_manager.ensure_current(index)
                    self.optional_workspace_manager.ensure_current(index)
                    sync_materialized_workspaces()
                    active_workspace[0] = tabs.currentWidget()
                    if active_workspace[0] is not None:
                        resume_thumbnail_clients(active_workspace[0])
                finally:
                    switching_workspace[0] = False

            tabs.currentChanged.connect(ensure_selected_workspace)

            def handle_download_prefill(payload: object) -> None:
                url = payload.get("url") if isinstance(payload, dict) else None
                route = classify_site_url(url)
                if route is not None:
                    self.core_workspace_manager.ensure(route.site_family)
                    self.optional_workspace_manager.ensure(route.site_family)
                    sync_materialized_workspaces()
                target = (
                    self.site_download_panels.get(route.site_family)
                    if route
                    else None
                )
                if target is not None:
                    apply_download_prefill(target, tabs, payload)

            context.events.subscribe("download.prefill", handle_download_prefill)

            def refresh_site_tab_titles(_payload: object = None) -> None:
                for panel in self.site_download_panels.values():
                    index = tabs.indexOf(panel)
                    if index >= 0:
                        tabs.setTabText(index, panel.workspace_title.text())

            context.events.subscribe("ui.language.changed", refresh_site_tab_titles)
            page.addWidget(tabs, 1)

            self.download_notice = QFrame()
            self.download_notice.setObjectName("downloadNotice")
            notice_layout = QHBoxLayout(self.download_notice)
            notice_layout.setContentsMargins(12, 8, 8, 8)
            self.download_notice_text = QLabel()
            self.download_notice_text.setObjectName("downloadNoticeText")
            notice_layout.addWidget(self.download_notice_text, 1)
            self.open_notice_folder = QPushButton("開啟資料夾")
            self.open_notice_folder.clicked.connect(self.open_completed_folder)
            notice_layout.addWidget(self.open_notice_folder)
            dismiss_notice = QPushButton("關閉")
            dismiss_notice.setObjectName("ghost")
            dismiss_notice.clicked.connect(self.download_notice.hide)
            notice_layout.addWidget(dismiss_notice)
            self.download_notice.hide()
            page.addWidget(self.download_notice)
            self.notice_timer = QTimer(self)
            self.notice_timer.setSingleShot(True)
            self.notice_timer.timeout.connect(self.download_notice.hide)

            footer = QFrame()
            footer.setObjectName("footerBar")
            footer_layout = QHBoxLayout(footer)
            footer_layout.setContentsMargins(4, 0, 4, 0)
            footer_layout.setSpacing(10)
            hint = QLabel("Ctrl+1／2／3 切換工作區　Ctrl+M 開啟 MOD 管理")
            hint.setObjectName("muted")
            footer_layout.addWidget(hint)
            footer_layout.addStretch()
            self.idle_status = QLabel("使用中")
            self.idle_status.setObjectName("muted")
            self.idle_status.setAccessibleName("應用程式狀態：使用中")
            self.idle_status.setToolTip(
                "背景待機會暫停不可見 UI 輪詢，但不中止下載或排程工作"
            )
            footer_layout.addWidget(self.idle_status)
            self.close_behavior_select = QComboBox()
            self.close_behavior_select.setObjectName("closeBehavior")
            self.close_behavior_select.setAccessibleName("關閉按鈕行為")
            self.close_behavior_select.setToolTip(
                "選擇按下視窗關閉按鈕時縮到系統匣或完全結束"
            )
            self.close_behavior_select.addItem(
                "關閉：縮到系統匣",
                "minimize-to-tray",
            )
            self.close_behavior_select.addItem("關閉：完全結束", "exit")
            selected_close_behavior = normalized_close_behavior(
                context.settings.close_behavior
            )
            self.close_behavior_select.setCurrentIndex(
                0 if selected_close_behavior == "minimize-to-tray" else 1
            )
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.close_behavior_select.setToolTip(
                    "目前系統匣不可用；縮到系統匣會安全退回完全結束"
                )
            footer_layout.addWidget(self.close_behavior_select)
            version = QLabel(application_display_name())
            version.setObjectName("muted")
            footer_layout.addWidget(version)
            page.addWidget(footer)

            def select_background() -> None:
                selected, _ = QFileDialog.getOpenFileName(
                    self,
                    "選擇背景圖片",
                    str(Path.home()),
                    "圖片 (*.jpg *.jpeg *.png *.webp *.bmp)",
                )
                if not selected:
                    return
                path = Path(selected)
                if not root.set_background(path):
                    QMessageBox.warning(
                        self,
                        "背景圖片",
                        "無法讀取圖片，請改用 JPG、PNG、WebP 或 BMP。",
                    )
                    return
                try:
                    stored = store_background_copy(self.settings_root, path)
                    if not root.set_background(stored):
                        raise ValueError("managed background copy cannot be decoded")
                except (OSError, ValueError) as error:
                    QMessageBox.warning(self, "背景圖片", f"無法保存設定：{error}")

            def restore_background() -> None:
                root.set_background(None)
                try:
                    clear_background_copy(self.settings_root)
                except OSError as error:
                    QMessageBox.warning(self, "背景圖片", f"無法保存設定：{error}")

            choose_background.triggered.connect(select_background)
            reset_background.triggered.connect(restore_background)

            def persist_settings(**changes: object) -> bool:
                try:
                    saved = SettingsService(
                        self.settings_root / "settings.json"
                    ).patch(
                        **changes
                    )
                except OSError as error:
                    detail = (
                        "設定檔目前受安全保護，變更已復原。"
                        if isinstance(error, SettingsWriteBlockedError)
                        else "設定檔目前無法寫入，變更已復原。"
                    )
                    QMessageBox.warning(
                        self,
                        "無法儲存設定",
                        f"{detail}\n{error}",
                    )
                    return False
                for name in changes:
                    setattr(context.settings, name, getattr(saved, name))
                return True

            def restore_checked_action(group: object, value: str) -> None:
                for candidate in group.actions():
                    candidate.setChecked(candidate.data() == value)

            def save_notification_settings() -> None:
                previous_in_app = context.settings.in_app_download_notifications
                previous_system = context.settings.system_download_notifications
                if not persist_settings(
                    in_app_download_notifications=(
                        self.in_app_notifications.isChecked()
                    ),
                    system_download_notifications=(
                        self.system_notifications.isChecked()
                    ),
                ):
                    self.in_app_notifications.blockSignals(True)
                    self.system_notifications.blockSignals(True)
                    try:
                        self.in_app_notifications.setChecked(previous_in_app)
                        self.system_notifications.setChecked(previous_system)
                    finally:
                        self.in_app_notifications.blockSignals(False)
                        self.system_notifications.blockSignals(False)
                    return
                if (
                    not self.system_notifications.isChecked()
                    and normalized_close_behavior(
                        context.settings.close_behavior
                    )
                    == "exit"
                    and not self.idle_resources.idle
                ):
                    self.remove_system_tray()

            def save_close_behavior(_index: int) -> None:
                previous = normalized_close_behavior(
                    context.settings.close_behavior
                )
                selected = normalized_close_behavior(
                    self.close_behavior_select.currentData()
                )
                if not persist_settings(close_behavior=selected):
                    self.close_behavior_select.blockSignals(True)
                    try:
                        self.close_behavior_select.setCurrentIndex(
                            0 if previous == "minimize-to-tray" else 1
                        )
                    finally:
                        self.close_behavior_select.blockSignals(False)
                    return
                application = QApplication.instance()
                if application is not None:
                    application.setQuitOnLastWindowClosed(selected == "exit")
                if (
                    selected == "exit"
                    and not self.system_notifications.isChecked()
                    and not self.idle_resources.idle
                ):
                    self.remove_system_tray()

            def save_startup_setting(enabled: bool) -> None:
                registration = self.startup_registration
                if registration is None:
                    return
                try:
                    previous_command = registration.registered_command()
                    registration.set_enabled(enabled)
                except OSError as error:
                    self.start_with_windows_action.blockSignals(True)
                    try:
                        self.start_with_windows_action.setChecked(not enabled)
                    finally:
                        self.start_with_windows_action.blockSignals(False)
                    QMessageBox.warning(
                        self,
                        "無法更新開機啟動",
                        f"Windows 使用者啟動設定未變更。\n{error}",
                    )
                    return
                if persist_settings(start_with_windows=enabled):
                    return
                rollback_error: OSError | None = None
                try:
                    registration.restore(previous_command)
                except OSError as error:
                    rollback_error = error
                self.start_with_windows_action.blockSignals(True)
                try:
                    self.start_with_windows_action.setChecked(
                        previous_command == registration.command
                    )
                finally:
                    self.start_with_windows_action.blockSignals(False)
                if rollback_error is not None:
                    QMessageBox.warning(
                        self,
                        "開機啟動回復失敗",
                        "設定檔未更新，Windows 啟動項也無法回復；"
                        "請再次切換此選項。\n"
                        f"{rollback_error}",
                    )

            def change_ui_scale(action: object) -> None:
                scale = normalized_ui_scale(action.data())
                previous_scale = normalized_ui_scale(context.settings.ui_scale)
                if not persist_settings(ui_scale=scale):
                    restore_checked_action(self.ui_scale_group, previous_scale)
                    return
                application = QApplication.instance()
                if application is not None:
                    apply_application_theme(application, scale)

            def change_core_language(action: object) -> None:
                locale = normalized_language(action.data())
                previous_locale = normalized_language(context.settings.language)
                if not persist_settings(language=locale):
                    restore_checked_action(self.language_group, previous_locale)
                    return
                context.plugin_ui.locale = locale
                context.events.publish("ui.language.changed", {"locale": locale})

            self.language_group.triggered.connect(change_core_language)
            self.ui_scale_group.triggered.connect(change_ui_scale)
            self.in_app_notifications.toggled.connect(save_notification_settings)
            self.system_notifications.toggled.connect(save_notification_settings)
            self.close_behavior_select.currentIndexChanged.connect(
                save_close_behavior
            )
            self.start_with_windows_action.toggled.connect(
                save_startup_setting
            )
            application = QApplication.instance()
            if application is not None:
                application.setQuitOnLastWindowClosed(
                    selected_close_behavior == "exit"
                )

            self.shortcuts: list[QShortcut] = []
            for sequence, index in (("Ctrl+1", 0), ("Ctrl+2", 1), ("Ctrl+3", 2)):
                shortcut = QShortcut(QKeySequence(sequence), self)
                shortcut.activated.connect(
                    lambda selected=index: tabs.setCurrentIndex(selected)
                )
                self.shortcuts.append(shortcut)
            mod_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
            mod_shortcut.activated.connect(plugins.click)
            self.shortcuts.append(mod_shortcut)
            environment_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
            environment_shortcut.activated.connect(environment.click)
            self.shortcuts.append(environment_shortcut)

            self.setCentralWidget(root)

        def ensure_system_tray(self) -> object | None:
            if self.system_tray is not None:
                return self.system_tray
            if not QSystemTrayIcon.isSystemTrayAvailable():
                return None
            icon = self.windowIcon()
            if icon.isNull():
                icon = self.style().standardIcon(
                    QStyle.StandardPixmap.SP_DriveHDIcon
                )
            tray = QSystemTrayIcon(icon, self)
            tray.setToolTip("MediaManager")
            menu = QMenu(self)
            restore_action = menu.addAction("開啟 MediaManager")
            restore_action.triggered.connect(self.restore_from_background)
            menu.addSeparator()
            exit_action = menu.addAction("完全結束")
            exit_action.triggered.connect(self.request_full_exit)
            tray.setContextMenu(menu)
            tray.activated.connect(self.handle_tray_activation)
            tray.show()
            self.tray_menu = menu
            self.system_tray = tray
            return tray

        def remove_system_tray(self) -> None:
            if self.system_tray is not None:
                self.system_tray.hide()
                self.system_tray.deleteLater()
                self.system_tray = None
            if self.tray_menu is not None:
                self.tray_menu.deleteLater()
                self.tray_menu = None

        def handle_tray_activation(self, reason: object) -> None:
            if reason in {
                QSystemTrayIcon.ActivationReason.Trigger,
                QSystemTrayIcon.ActivationReason.DoubleClick,
            }:
                self.restore_from_background()

        def set_idle_status(self, idle: bool) -> None:
            text = "背景待機" if idle else "使用中"
            self.idle_status.setText(text)
            self.idle_status.setAccessibleName(f"應用程式狀態：{text}")

        def enter_background_idle(self, *, hide: bool = True) -> bool:
            if hide and self.ensure_system_tray() is None:
                return False
            application = QApplication.instance()
            if hide and application is not None:
                application.setQuitOnLastWindowClosed(False)
            self.idle_resources.enter(self)
            self.set_idle_status(True)
            if hide:
                self.hide()
            return True

        def restore_from_background(self) -> None:
            self.showNormal()
            self.idle_resources.leave()
            self.set_idle_status(False)
            application = QApplication.instance()
            if application is not None:
                application.setQuitOnLastWindowClosed(
                    normalized_close_behavior(context.settings.close_behavior)
                    == "exit"
                )
            self.raise_()
            self.activateWindow()

        def request_full_exit(self) -> None:
            self._force_exit = True
            application = QApplication.instance()
            if application is not None:
                application.setQuitOnLastWindowClosed(True)
            self.close()
            if application is not None:
                application.quit()

        def shutdown_ui(self) -> None:
            if self._shutdown_started:
                return
            self._shutdown_started = True
            self.idle_resources.enter(self)
            self.idle_resources.discard()
            self.notice_timer.stop()
            self.core_workspace_manager.close_all()
            self.optional_workspace_manager.close_all()
            self.remove_system_tray()

        def handle_download_change(self, task: object) -> None:
            summary = self.notification_tracker.observe(task)
            if summary is None or not (summary.completed or summary.failed):
                return
            message = completion_message(summary)
            self.notice_output_dir = summary.output_dir
            if self.in_app_notifications.isChecked():
                self.download_notice_text.setText(message)
                self.open_notice_folder.setVisible(summary.output_dir is not None)
                self.download_notice.show()
                self.notice_timer.start(10_000)
            if self.system_notifications.isChecked():
                tray = self.ensure_system_tray()
                if tray is not None:
                    title = (
                        "下載完成"
                        if summary.failed == 0 and summary.cancelled == 0
                        else "下載工作已結束"
                    )
                    tray.showMessage(
                        title,
                        message,
                        QSystemTrayIcon.MessageIcon.Information,
                        8_000,
                    )

        def open_completed_folder(self) -> None:
            if self.notice_output_dir is not None:
                QDesktopServices.openUrl(
                    QUrl.fromLocalFile(str(self.notice_output_dir))
                )

        def changeEvent(self, event: object) -> None:
            super().changeEvent(event)
            if event.type() != QEvent.Type.WindowStateChange:
                return
            if self.windowState() & Qt.WindowState.WindowMinimized:
                QTimer.singleShot(
                    0,
                    self.enter_minimized_idle_if_still_minimized,
                )
            elif self.isVisible() and self.idle_resources.idle:
                self.idle_resources.leave()
                self.set_idle_status(False)

        def enter_minimized_idle_if_still_minimized(self) -> None:
            """Ignore a deferred minimize callback after the window was restored."""

            if (
                not self._shutdown_started
                and self.windowState() & Qt.WindowState.WindowMinimized
            ):
                self.enter_background_idle(hide=False)

        def closeEvent(self, event: object) -> None:
            close_behavior = normalized_close_behavior(
                context.settings.close_behavior
            )
            if (
                not self._force_exit
                and close_behavior == "minimize-to-tray"
                and self.enter_background_idle()
            ):
                event.ignore()
                return
            application = QApplication.instance()
            if application is not None:
                application.setQuitOnLastWindowClosed(True)
            self.shutdown_ui()
            super().closeEvent(event)

    if QApplication.instance() is None:
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_DontUseNativeDialogs,
            True,
        )
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("MediaManager")
    icon_path = app_icon_path()
    if icon_path is not None:
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)
    apply_application_theme(app, context.settings.ui_scale)
    # Startup stays non-modal.  MOD selection and dependency remediation remain
    # available through the visible MOD manager and environment status buttons.
    window = Window()
    effective_start_minimized = start_minimized and initial_prefill is None
    if not effective_start_minimized or not window.enter_background_idle():
        window.show()
        window.raise_()
        window.activateWindow()
    if initial_prefill is not None:
        context.events.publish("download.prefill", initial_prefill)
    return app.exec()
