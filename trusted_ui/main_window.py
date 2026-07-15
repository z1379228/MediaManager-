"""MediaManager trusted desktop shell."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from core.dependency_health import check_dependencies
from core.localization import CORE_LOCALES
from core.downloads.notifications import (
    DownloadCompletionTracker,
    completion_message,
)
from core.settings import SettingsService, normalized_language
from core.site_routing import classify_site_url
from core.version import display_version
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
    startup_dependency_prompt_required,
)
from trusted_ui.download_panel import create_download_panel
from trusted_ui.conversion_panel import create_conversion_panel
from trusted_ui.transcription_panel import create_transcription_panel
from trusted_ui.automation_panel import create_automation_panel
from trusted_ui.library_panel import create_library_panel
from trusted_ui.plugin_manager import show_plugin_manager
from trusted_ui.search_panel import create_search_panel
from trusted_ui.theme import (
    UI_SCALE_VALUES,
    apply_application_theme,
    normalized_ui_scale,
)


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
    preview.setText(
        f"已從「{source}」帶入；請確認格式、分段、字幕與網站專屬選項後再加入佇列。"
    )
    tabs.setCurrentWidget(download_panel)
    urls.setFocus()
    return True


def run_main_window(context: object) -> int:
    from PySide6.QtCore import QObject, QTimer, Qt, QUrl, Signal
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

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"MediaManager {display_version()}")
            self.setAccessibleName("MediaManager 主視窗")
            self.resize(1180, 780)
            self.setMinimumSize(940, 620)
            self.settings_root = Path(context.paths.settings)
            self.notification_tracker = DownloadCompletionTracker(
                context.download_queue.snapshots()
            )
            self.notification_bridge = NotificationBridge(self)
            self.notification_bridge.changed.connect(self.handle_download_change)
            context.download_queue.subscribe(self.notification_bridge.changed.emit)
            self.system_tray = None
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
            mode.setAccessibleName("安全狀態")
            mode.setToolTip(mode_tip)
            header.addWidget(mode)

            dependency_report = check_dependencies(Path(context.paths.application))
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
                )
            )
            header.addWidget(environment)

            appearance = QPushButton("外觀")
            appearance.setObjectName("ghost")
            appearance.setToolTip("設定背景、大小、核心介面語言與通知")
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
            self.download_panel = create_download_panel(
                context, self, site_family="youtube"
            )
            self.bilibili_download_panel = create_download_panel(
                context, self, site_family="bilibili"
            )
            self.search_panel = create_search_panel(context, self)
            tabs.addTab(self.download_panel, self.download_panel.workspace_title.text())
            tabs.addTab(
                self.bilibili_download_panel,
                self.bilibili_download_panel.workspace_title.text(),
            )
            tabs.addTab(self.search_panel, "網站搜尋")
            self.library_panel = create_library_panel(context, self)
            tabs.addTab(self.library_panel, "本機媒體庫")
            tabs.setTabToolTip(0, "YouTube 搜尋、播放清單、批量與分段下載")
            tabs.setTabToolTip(1, "Bilibili 影片、番劇、分段與彈幕下載")
            tabs.setTabToolTip(2, "單一網站搜尋、替代候選與相似內容")
            tabs.setTabToolTip(3, "掃描、篩選與開啟本機媒體")

            def handle_download_prefill(payload: object) -> None:
                url = payload.get("url") if isinstance(payload, dict) else None
                route = classify_site_url(url)
                panels = {
                    "youtube": self.download_panel,
                    "bilibili": self.bilibili_download_panel,
                }
                target = panels.get(route.site_family) if route else None
                if target is not None:
                    apply_download_prefill(target, tabs, payload)

            context.events.subscribe("download.prefill", handle_download_prefill)

            def refresh_site_tab_titles(_payload: object = None) -> None:
                tabs.setTabText(0, self.download_panel.workspace_title.text())
                tabs.setTabText(
                    1, self.bilibili_download_panel.workspace_title.text()
                )

            context.events.subscribe("ui.language.changed", refresh_site_tab_titles)
            self.optional_panels: dict[str, object] = {}

            def sync_optional_panel(payload: object = None) -> None:
                if isinstance(payload, dict) and payload.get("provider_id") != "media-convert":
                    return
                enabled = any(
                    status.provider_id == "media-convert" and status.enabled
                    for status in context.features.statuses()
                )
                existing = self.optional_panels.get("media-convert")
                if enabled and existing is None and context.conversion is not None:
                    conversion_panel = create_conversion_panel(context, self)
                    self.optional_panels["media-convert"] = conversion_panel
                    tabs.addTab(conversion_panel, "Media Convert")
                    tabs.setTabToolTip(
                        tabs.indexOf(conversion_panel),
                        "本機轉封裝、轉檔、壓縮、串接與切割",
                    )
                elif not enabled and existing is not None:
                    index = tabs.indexOf(existing)
                    if index >= 0:
                        tabs.removeTab(index)
                    existing.shutdown()
                    existing.deleteLater()
                    self.optional_panels.pop("media-convert", None)

            context.events.subscribe("builtin_mod.changed", sync_optional_panel)
            sync_optional_panel()

            def sync_transcription_panel(payload: object = None) -> None:
                if isinstance(payload, dict) and payload.get("provider_id") != "speech-to-text":
                    return
                enabled = any(
                    status.provider_id == "speech-to-text" and status.enabled
                    for status in context.features.statuses()
                )
                existing = self.optional_panels.get("speech-to-text")
                if enabled and existing is None and context.transcription is not None:
                    transcription_panel = create_transcription_panel(context, self)
                    self.optional_panels["speech-to-text"] = transcription_panel
                    tabs.addTab(transcription_panel, "Speech to Text")
                    tabs.setTabToolTip(
                        tabs.indexOf(transcription_panel),
                        "本機語音轉文字與 TXT、SRT、VTT 輸出",
                    )
                elif not enabled and existing is not None:
                    index = tabs.indexOf(existing)
                    if index >= 0:
                        tabs.removeTab(index)
                    existing.shutdown()
                    existing.deleteLater()
                    self.optional_panels.pop("speech-to-text", None)

            context.events.subscribe("builtin_mod.changed", sync_transcription_panel)
            sync_transcription_panel()

            def sync_automation_panel(payload: object = None) -> None:
                if isinstance(payload, dict) and payload.get("provider_id") != "automation":
                    return
                enabled = any(
                    status.provider_id == "automation" and status.enabled
                    for status in context.features.statuses()
                )
                existing = self.optional_panels.get("automation")
                if enabled and existing is None and context.automation is not None:
                    automation_panel = create_automation_panel(context, self)
                    self.optional_panels["automation"] = automation_panel
                    tabs.addTab(automation_panel, "Automation")
                    tabs.setTabToolTip(
                        tabs.indexOf(automation_panel),
                        "選用排程、監看資料夾與剪貼簿網址候選",
                    )
                elif not enabled and existing is not None:
                    index = tabs.indexOf(existing)
                    if index >= 0:
                        tabs.removeTab(index)
                    existing.shutdown()
                    existing.deleteLater()
                    self.optional_panels.pop("automation", None)

            context.events.subscribe("builtin_mod.changed", sync_automation_panel)
            sync_automation_panel()
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
            version = QLabel(f"核心 {display_version()}")
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

            def save_settings() -> None:
                context.settings.in_app_download_notifications = (
                    self.in_app_notifications.isChecked()
                )
                context.settings.system_download_notifications = (
                    self.system_notifications.isChecked()
                )
                SettingsService(self.settings_root / "settings.json").save(
                    context.settings
                )
                if not self.system_notifications.isChecked():
                    self.remove_system_tray()

            def change_ui_scale(action: object) -> None:
                scale = normalized_ui_scale(action.data())
                context.settings.ui_scale = scale
                application = QApplication.instance()
                if application is not None:
                    apply_application_theme(application, scale)
                save_settings()

            def change_core_language(action: object) -> None:
                locale = normalized_language(action.data())
                context.settings.language = locale
                context.plugin_ui.locale = locale
                save_settings()
                context.events.publish("ui.language.changed", {"locale": locale})

            self.language_group.triggered.connect(change_core_language)
            self.ui_scale_group.triggered.connect(change_ui_scale)
            self.in_app_notifications.toggled.connect(save_settings)
            self.system_notifications.toggled.connect(save_settings)

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
            if startup_dependency_prompt_required(dependency_report):
                QTimer.singleShot(
                    0,
                    lambda: show_dependency_dialog(
                        Path(context.paths.application),
                        self,
                    ),
                )

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
            tray.show()
            self.system_tray = tray
            return tray

        def remove_system_tray(self) -> None:
            if self.system_tray is not None:
                self.system_tray.hide()
                self.system_tray.deleteLater()
                self.system_tray = None

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

        def closeEvent(self, event: object) -> None:
            self.search_panel.shutdown()
            for optional_panel in self.optional_panels.values():
                optional_panel.shutdown()
            self.remove_system_tray()
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
    window = Window()
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
