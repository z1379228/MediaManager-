"""Lightweight trusted UI for bounded search across enabled search MODs."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from core.discovery.adapters import FederatedSearchResult
from core.discovery.query_ranking import (
    matching_search_indices,
    prepare_search_query,
    rank_search_results,
)
from core.discovery.suggestions import preference_search_queries
from core.mod_groups import (
    SITE_MOD_PARENT,
    BuiltinModGroupError,
    load_builtin_mod_groups,
)
from core.settings import normalized_language
from core.site_routing import classify_site_url
from trusted_ui.empty_state import create_empty_state
from trusted_ui.builtin_mod_control import (
    builtin_mod_is_enabled,
    set_builtin_mod_enabled,
)
from trusted_ui.thumbnail_loader import create_thumbnail_loader


@dataclass(frozen=True, slots=True)
class _SearchResponse:
    generation: int
    value: object


@dataclass(frozen=True, slots=True)
class _PreviewResponse:
    generation: int
    provider: object | None
    path: Path | None


def download_workspace_name(provider_id: object) -> str:
    """Return the trusted workspace that owns a download provider."""

    return {
        "youtube": "YouTube 下載工作區",
        "bilibili": "Bilibili 下載工作區",
    }.get(provider_id, "對應網站下載工作區")


def localized_site_module_names(locale: object) -> dict[str, str]:
    try:
        return {
            module.provider_id: module.display_name
            for group in load_builtin_mod_groups(locale)
            for module in group.modules
        }
    except BuiltinModGroupError:
        return {}


def explicit_search_source_name(
    provider_id: object, locale: object, fallback: str = ""
) -> str:
    """Keep shared-search source labels distinct across website MODs."""

    labels = {
        "youtube-search": {
            "zh-TW": "YouTube 搜尋",
            "zh-CN": "YouTube 搜索",
            "ja": "YouTube 検索",
            "en": "YouTube Search",
        },
        "bilibili-search": {
            "zh-TW": "Bilibili 搜尋",
            "zh-CN": "Bilibili 搜索",
            "ja": "Bilibili 検索",
            "en": "Bilibili Search",
        },
        "ani-gamer-search": {
            "zh-TW": "動畫瘋官方搜尋",
            "zh-CN": "动画疯官方搜索",
            "ja": "AniGamer 公式検索",
            "en": "AniGamer Official Search",
        },
    }
    provider_labels = labels.get(str(provider_id))
    if provider_labels is None:
        return fallback or str(provider_id)
    return provider_labels[normalized_language(locale)]


def search_source_for_url(url: object) -> str:
    """Infer result provenance from the shared exact-host/path router."""

    route = classify_site_url(url)
    return route.search_provider_id if route is not None else ""


def recent_history_queries(
    events: object,
    *,
    limit: int = 8,
) -> tuple[str, ...]:
    """Return bounded, newest-first unique queries for the compact history UI."""

    if not isinstance(events, (list, tuple)):
        return ()
    bounded_limit = max(1, min(int(limit), 20))
    queries: list[str] = []
    seen: set[str] = set()
    for event in events:
        value = getattr(event, "query", "")
        query = " ".join(value.split()) if isinstance(value, str) else ""
        key = query.casefold()
        if not query or key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= bounded_limit:
            break
    return tuple(queries)


def history_preference_summary(preferences: object) -> str:
    """Build a short local-only preference summary without exposing raw history."""

    searches = max(0, int(getattr(preferences, "total_searches", 0)))
    selections = max(0, int(getattr(preferences, "total_selections", 0)))
    parts = [f"{searches} 次搜尋", f"{selections} 次選取"]
    for label, field in (("常選", "content_types"), ("語言", "languages")):
        values = getattr(preferences, field, {})
        if not isinstance(values, dict) or not values:
            continue
        value = max(values.items(), key=lambda item: (item[1], item[0]))[0]
        if field == "content_types":
            value = {"music": "音樂", "video": "影片"}.get(value, value)
        parts.append(f"{label} {value}")
    return " · ".join(parts)


def create_search_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import QObject, QSize, Qt, QUrl, Signal
    from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMenu,
        QMessageBox,
        QPushButton,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class SearchBridge(QObject):
        finished = Signal(object, str)

    class PreviewBridge(QObject):
        finished = Signal(object, str)

    class VideoPreviewBridge(QObject):
        finished = Signal(object, str)

    class SearchPanel(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.results = ()
            self.result_sources: tuple[str, ...] = ()
            self.last_query = ""
            self.recovery_meta = {}
            self.search_rank_meta = {}
            self.next_search_cursor = ""
            self.last_search_failures: tuple[object, ...] = ()
            self.busy_action = ""
            self.generation = 0
            self.results_generation = 0
            self.closing = False
            self.thumbnail_loader = create_thumbnail_loader(self)
            self.bridge = SearchBridge()
            self.bridge.finished.connect(self.show_results)
            self.preview_bridge = PreviewBridge()
            self.preview_bridge.finished.connect(self.show_audio_preview)
            self.video_preview_bridge = VideoPreviewBridge()
            self.video_preview_bridge.finished.connect(self.show_video_preview)
            self.preview_path: Path | None = None
            self.preview_provider = None
            self.video_preview_path: Path | None = None
            self.video_preview_provider = None
            self.video_dialog = None
            self.video_player = None
            self.audio_output = QAudioOutput(self)
            self.audio_output.setVolume(0.7)
            self.audio_player = QMediaPlayer(self)
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.mediaStatusChanged.connect(self.handle_audio_status)
            self.audio_player.errorOccurred.connect(self.handle_audio_error)
            page = QVBoxLayout(self)
            page.setContentsMargins(2, 4, 2, 2)
            page.setSpacing(12)

            heading = QHBoxLayout()
            titles = QVBoxLayout()
            titles.setSpacing(2)
            title = QLabel("網站搜尋")
            title.setObjectName("sectionTitle")
            subtitle = QLabel("輕量搜尋影片與音樂；顯示小縮圖協助辨識結果。")
            subtitle.setObjectName("sectionSubtitle")
            titles.addWidget(title)
            titles.addWidget(subtitle)
            heading.addLayout(titles)
            heading.addStretch()
            statuses = {status.provider_id for status in context.discovery.statuses()}
            module_names = localized_site_module_names(
                getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            current_locale = getattr(
                getattr(context, "settings", None), "language", "zh-TW"
            )
            feature_button = QPushButton()
            feature_button.setObjectName("ghost")
            feature_button.setToolTip("個別啟用或停用各網站搜尋與選用功能 MOD")
            feature_menu = QMenu(feature_button)

            def create_feature_action(label: str, provider_id: str) -> QAction:
                action = QAction(label, feature_menu)
                action.setCheckable(True)
                available = provider_id in statuses
                action.setEnabled(available)
                action.setChecked(
                    available and context.discovery.is_enabled(provider_id)
                )
                if not available:
                    action.setToolTip(f"{provider_id} MOD 不可用")
                action.toggled.connect(
                    lambda checked, selected=provider_id: set_builtin_mod_enabled(
                        context, selected, checked
                    )
                )
                feature_menu.addAction(action)
                return action

            self.enabled = create_feature_action(
                explicit_search_source_name(
                    "youtube-search",
                    current_locale,
                    module_names.get("youtube-search", "YouTube 搜尋"),
                ),
                "youtube-search",
            )
            self.bilibili_search_enabled = create_feature_action(
                explicit_search_source_name(
                    "bilibili-search",
                    current_locale,
                    module_names.get("bilibili-search", "Bilibili 搜尋"),
                ),
                "bilibili-search",
            )
            self.ani_gamer_search_enabled = create_feature_action(
                explicit_search_source_name(
                    "ani-gamer-search", current_locale, "動畫瘋官方搜尋"
                ),
                "ani-gamer-search",
            )
            self.history_enabled = create_feature_action(
                "記錄搜尋偏好", "youtube-history"
            )
            self.recovery_enabled = create_feature_action(
                "失效影片替換", "youtube-recovery"
            )
            self.similar_enabled = create_feature_action(
                "隨機尋找相似內容", "youtube-similar"
            )
            self.video_enabled = create_feature_action("播放影片預覽", "youtube-player")
            feature_actions = (
                self.enabled,
                self.bilibili_search_enabled,
                self.ani_gamer_search_enabled,
                self.history_enabled,
                self.recovery_enabled,
                self.similar_enabled,
                self.video_enabled,
            )
            self.feature_actions_by_id = dict(
                zip(
                    (
                        "youtube-search",
                        "bilibili-search",
                        "ani-gamer-search",
                        "youtube-history",
                        "youtube-recovery",
                        "youtube-similar",
                        "youtube-player",
                    ),
                    feature_actions,
                    strict=True,
                )
            )

            def parent_is_enabled(provider_id: str) -> bool:
                parent_id = SITE_MOD_PARENT.get(provider_id)
                if parent_id is None:
                    return True
                try:
                    return builtin_mod_is_enabled(context, parent_id)
                except (AttributeError, KeyError, RuntimeError):
                    if not hasattr(context, "download_providers"):
                        return True
                    return False

            def refresh_parent_visibility() -> None:
                for child_id, parent_id in SITE_MOD_PARENT.items():
                    action = self.feature_actions_by_id.get(child_id)
                    if action is None:
                        continue
                    parent_enabled = parent_is_enabled(child_id)
                    action.setVisible(parent_enabled)
                    action.setEnabled(parent_enabled and child_id in statuses)
                    action.setToolTip(
                        "" if parent_enabled else f"請先啟用 {parent_id} 主 MOD"
                    )

            self.parent_is_enabled = parent_is_enabled
            self.refresh_parent_visibility = refresh_parent_visibility
            refresh_parent_visibility()

            def refresh_feature_button() -> None:
                available = sum(
                    action.isVisible() and action.isEnabled()
                    for action in feature_actions
                )
                active = sum(
                    action.isVisible() and action.isChecked()
                    for action in feature_actions
                )
                feature_button.setText(f"搜尋 MOD  {active}/{available}")

            for action in feature_actions:
                action.toggled.connect(refresh_feature_button)
            self.refresh_feature_button = refresh_feature_button
            refresh_feature_button()
            feature_button.setMenu(feature_menu)
            heading.addWidget(feature_button)
            page.addLayout(heading)

            search_card = QFrame()
            search_card.setObjectName("card")
            search_layout = QVBoxLayout(search_card)
            search_layout.setContentsMargins(16, 14, 16, 14)
            search_layout.setSpacing(8)
            query_row = QHBoxLayout()
            filter_row = QHBoxLayout()
            self.query = QLineEdit()
            self.query.setAccessibleName("單一網站搜尋文字")
            self.query.setPlaceholderText("搜尋歌曲、歌手、影片名稱或語言…")
            self.query.setClearButtonEnabled(True)
            self.query.returnPressed.connect(self.search)
            self.limit = QComboBox()
            self.limit.setAccessibleName("搜尋結果數量")
            for value in (12, 20, 30, 50):
                self.limit.addItem(f"{value} 筆", value)
            self.limit.setCurrentIndex(1)
            self.search_scope = QComboBox()
            self.search_scope.setAccessibleName("搜尋內容類型")
            self.search_scope.addItem("全部", "all")
            self.search_scope.addItem("音樂", "music")
            self.search_scope.addItem("影片", "video")
            self.search_scope.setToolTip("指定搜尋範圍；只查詢已啟用的搜尋 MOD")
            self.duration_filter = QComboBox()
            self.duration_filter.setAccessibleName("搜尋結果長度篩選")
            self.duration_filter.addItem("所有長度", (None, None))
            self.duration_filter.addItem("4 分鐘內", (None, 240))
            self.duration_filter.addItem("4–20 分鐘", (241, 1200))
            self.duration_filter.addItem("20 分鐘以上", (1201, None))
            self.language_filter = QComboBox()
            self.language_filter.setAccessibleName("搜尋結果語言篩選")
            for label, value in (
                ("所有語言", ""),
                ("繁體中文", "zh-TW"),
                ("簡體中文", "zh-CN"),
                ("日文", "ja"),
                ("英文", "en"),
            ):
                self.language_filter.addItem(label, value)
            self.search_source = QComboBox()
            self.search_source.setAccessibleName("搜尋來源")
            self.search_source.setMinimumWidth(220)
            self.search_source_summary = QLabel()
            self.search_source_summary.setObjectName("searchSourceSummary")
            self.search_source_summary.setWordWrap(True)
            try:
                source_statuses = tuple(
                    status
                    for status in context.discovery.search_source_statuses()
                    if parent_is_enabled(status.provider_id)
                )
                self.search_provider_ids = tuple(
                    status.provider_id for status in source_statuses
                )
            except (AttributeError, RuntimeError, ValueError):
                source_statuses = ()
                self.search_provider_ids = ()
            self.search_source_labels = {
                status.provider_id: explicit_search_source_name(
                    status.provider_id,
                    current_locale,
                    status.display_name,
                )
                for status in source_statuses
            }

            def refresh_search_sources() -> None:
                selected = self.search_source.currentData()
                previous_block = self.search_source.blockSignals(True)
                try:
                    self.search_source.clear()
                    try:
                        all_statuses = tuple(
                            context.discovery.search_source_statuses()
                        )
                        statuses = tuple(
                            status
                            for status in all_statuses
                            if parent_is_enabled(status.provider_id)
                        )
                    except (AttributeError, RuntimeError, ValueError):
                        all_statuses = ()
                        statuses = ()
                    self.search_provider_ids = tuple(
                        status.provider_id for status in statuses
                    )
                    localized_names = localized_site_module_names(
                        getattr(
                            getattr(context, "settings", None),
                            "language",
                            "zh-TW",
                        )
                    )
                    for status in statuses:
                        display_name = explicit_search_source_name(
                            status.provider_id,
                            getattr(
                                getattr(context, "settings", None),
                                "language",
                                "zh-TW",
                            ),
                            localized_names.get(
                                status.provider_id, status.display_name
                            ),
                        )
                        self.search_source_labels[status.provider_id] = (
                            display_name
                        )
                        suffix = {
                            "ready": "正常",
                            "error": "錯誤",
                            "disabled": "停用",
                        }.get(status.health, status.health)
                        self.search_source.addItem(
                            f"{display_name}（{suffix}）", status.provider_id
                        )
                        index = self.search_source.count() - 1
                        if status.message:
                            self.search_source.setItemData(
                                index, status.message, Qt.ItemDataRole.ToolTipRole
                            )
                    source_names = [
                        self.search_source_labels.get(
                            status.provider_id, status.display_name
                        )
                        for status in statuses
                    ]
                    hidden_parent_sources = [
                        status
                        for status in all_statuses
                        if not parent_is_enabled(status.provider_id)
                    ]
                    hidden_hint = ""
                    if hidden_parent_sources:
                        hidden_labels = []
                        for status in hidden_parent_sources:
                            source_label = explicit_search_source_name(
                                status.provider_id,
                                getattr(
                                    getattr(context, "settings", None),
                                    "language",
                                    "zh-TW",
                                ),
                                status.display_name,
                            )
                            parent_id = SITE_MOD_PARENT.get(status.provider_id, "")
                            parent_label = {
                                "youtube": "YouTube",
                                "bilibili": "Bilibili",
                                "ani-gamer": "動畫瘋",
                            }.get(parent_id, parent_id)
                            hidden_labels.append(
                                f"{source_label}需先啟用 {parent_label} 主 MOD"
                            )
                        hidden_hint = "；未列出：" + "、".join(hidden_labels)
                    self.search_source_summary.setText(
                        "可選搜尋來源（一次查一個網站）："
                        + ("、".join(source_names) if source_names else "目前沒有可用來源")
                        + hidden_hint
                    )
                    index = self.search_source.findData(selected)
                    if index < 0:
                        index = self.search_source.findData("youtube-search")
                    if index < 0:
                        index = next(
                            (
                                item_index
                                for item_index, status in enumerate(statuses)
                                if status.enabled
                            ),
                            0 if statuses else -1,
                        )
                    self.search_source.setCurrentIndex(index)
                finally:
                    self.search_source.blockSignals(previous_block)

            self.refresh_search_sources = refresh_search_sources
            refresh_search_sources()
            self.history_button = QPushButton("最近搜尋")
            self.history_button.setObjectName("ghost")
            self.history_button.setToolTip("查看本機搜尋紀錄與偏好摘要")
            self.history_menu = QMenu(self.history_button)
            self.history_menu.aboutToShow.connect(self.populate_history_menu)
            self.history_button.setMenu(self.history_menu)
            self.search_button = QPushButton("搜尋")
            self.search_button.setAccessibleName("執行單一網站搜尋")
            self.search_button.setObjectName("primary")
            self.search_button.clicked.connect(self.search)
            self.next_page_button = QPushButton("下一頁")
            self.next_page_button.setObjectName("ghost")
            self.next_page_button.setAccessibleName("搜尋下一頁")
            self.next_page_button.clicked.connect(self.search_next_page)
            self.next_page_button.setEnabled(False)
            self.next_page_button.setToolTip("目前來源尚未回傳下一頁游標")
            query_row.addWidget(self.query, 1)
            query_row.addWidget(self.search_source)
            query_row.addWidget(self.search_scope)
            filter_row.addWidget(self.duration_filter)
            filter_row.addWidget(self.language_filter)
            filter_row.addWidget(self.limit)
            filter_row.addStretch()
            filter_row.addWidget(self.history_button)
            filter_row.addWidget(self.search_button)
            filter_row.addWidget(self.next_page_button)
            search_layout.addLayout(query_row)
            search_layout.addLayout(filter_row)
            search_layout.addWidget(self.search_source_summary)
            page.addWidget(search_card)

            self.status = QLabel("輸入關鍵字開始搜尋。")
            self.status.setObjectName("muted")
            status_row = QHBoxLayout()
            status_row.addWidget(self.status, 1)
            self.failure_button = QPushButton("查看來源錯誤")
            self.failure_button.setObjectName("ghost")
            self.failure_button.setAccessibleName("查看搜尋來源錯誤明細")
            self.failure_button.clicked.connect(self.show_search_failures)
            self.failure_button.hide()
            status_row.addWidget(self.failure_button)
            page.addLayout(status_row)

            self.table = QTableWidget(0, 7)
            self.table.setAccessibleName("單一網站搜尋結果")
            self.table.setAccessibleDescription(
                "顯示縮圖、標題、作者、長度、類型與來源"
            )
            self.table.setHorizontalHeaderLabels(
                ["預覽", "標題", "作者 / 頻道", "長度", "類型", "來源", "符合度"]
            )
            self.table.setIconSize(QSize(96, 54))
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(False)
            self.table.verticalHeader().hide()
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 112)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            for column in (3, 4, 5, 6):
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )
            self.table.itemDoubleClicked.connect(self.open_selected)
            self.table.itemSelectionChanged.connect(self.update_action_state)
            self.result_stack = QStackedWidget()
            self.result_empty = create_empty_state(
                "開始搜尋影片或音樂",
                "輸入歌曲、歌手、影片名稱或語言；結果只載入必要文字資訊。",
                "⌕",
            )
            self.result_stack.addWidget(self.result_empty)
            self.result_stack.addWidget(self.table)
            page.addWidget(self.result_stack, 1)

            actions = QHBoxLayout()
            self.recovery_button = QPushButton("尋找替代影片")
            self.recovery_button.clicked.connect(self.find_replacement)
            actions.addWidget(self.recovery_button)
            self.similar_button = QPushButton("隨機相似")
            self.similar_button.clicked.connect(self.find_similar)
            actions.addWidget(self.similar_button)
            self.download_button = QPushButton("前往下載設定")
            self.download_button.setObjectName("primary")
            self.download_button.clicked.connect(self.download_selected)
            self.open_button = QPushButton("在瀏覽器開啟")
            self.open_button.clicked.connect(self.open_selected)
            self.preview_button = QPushButton("試聽 30 秒")
            self.preview_button.clicked.connect(self.prepare_audio_preview)
            self.stop_preview_button = QPushButton("停止試聽")
            self.stop_preview_button.setObjectName("ghost")
            self.stop_preview_button.clicked.connect(self.stop_audio_preview)
            self.video_button = QPushButton("影片預覽 60 秒")
            self.video_button.clicked.connect(self.prepare_video_preview)
            actions.addWidget(self.download_button)
            actions.addWidget(self.open_button)
            actions.addWidget(self.preview_button)
            actions.addWidget(self.stop_preview_button)
            actions.addWidget(self.video_button)
            self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
            self.search_shortcut.activated.connect(self.query.setFocus)
            actions.addStretch()
            page.addLayout(actions)
            self.recovery_enabled.toggled.connect(self.update_action_state)
            self.similar_enabled.toggled.connect(self.update_action_state)
            self.history_enabled.toggled.connect(self.update_action_state)
            for search_action in (
                self.enabled,
                self.bilibili_search_enabled,
                self.ani_gamer_search_enabled,
            ):
                search_action.toggled.connect(self.refresh_search_sources)

            def invalidate_search_cursor() -> None:
                self.next_search_cursor = ""
                self.next_page_button.setToolTip(
                    "搜尋條件已變更；請先重新搜尋第一頁"
                )
                self.update_action_state()

            self.invalidate_search_cursor = invalidate_search_cursor
            self.search_source.currentIndexChanged.connect(invalidate_search_cursor)
            self.search_scope.currentIndexChanged.connect(invalidate_search_cursor)
            self.limit.currentIndexChanged.connect(invalidate_search_cursor)
            self.query.textEdited.connect(invalidate_search_cursor)
            self.video_enabled.toggled.connect(self.handle_video_toggle)
            self.update_action_state()
            events = getattr(context, "events", None)
            if events is not None:
                events.subscribe(
                    "builtin_mod.changed", self.handle_builtin_mod_changed
                )
                events.subscribe("ui.language.changed", self.handle_language_changed)

        def handle_builtin_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            provider_id = payload.get("provider_id")
            action = self.feature_actions_by_id.get(provider_id)
            if action is not None:
                action.blockSignals(True)
                action.setChecked(context.discovery.is_enabled(str(provider_id)))
                action.blockSignals(False)
            self.refresh_parent_visibility()
            if provider_id in self.search_provider_ids or provider_id in {
                "youtube",
                "bilibili",
                "youtube-search",
                "bilibili-search",
            }:
                self.refresh_search_sources()
            self.refresh_feature_button()
            self.update_action_state()

        def handle_language_changed(self, payload: object) -> None:
            locale = payload.get("locale") if isinstance(payload, dict) else "zh-TW"
            names = localized_site_module_names(locale)
            for provider_id in (
                "youtube-search",
                "bilibili-search",
                "ani-gamer-search",
                "youtube-player",
                "youtube-history",
                "youtube-recovery",
                "youtube-similar",
            ):
                name = names.get(provider_id)
                if provider_id in {
                    "youtube-search",
                    "bilibili-search",
                    "ani-gamer-search",
                }:
                    name = explicit_search_source_name(
                        provider_id, locale, name or provider_id
                    )
                action = self.feature_actions_by_id.get(provider_id)
                if name and action is not None:
                    action.setText(name)
            self.refresh_search_sources()
            self.refresh_feature_button()

        def update_action_state(self) -> None:
            selected_item = self.selected_result()
            selected = selected_item is not None
            selected_source = self.selected_result_source()
            download_provider = ""
            download_ready = False
            audio_preview_ready = False
            if selected_item is not None:
                try:
                    download_provider = context.download_providers.matching_provider_id(
                        selected_item.url
                    )
                    download_ready = bool(
                        download_provider
                        and context.download_providers.is_enabled(download_provider)
                    )
                except (AttributeError, KeyError, RuntimeError, ValueError):
                    download_ready = False
                if download_ready:
                    try:
                        capability = next(
                            (
                                item
                                for item in context.discovery.search_capabilities()
                                if item.provider_id == selected_source
                            ),
                            None,
                        )
                        audio_preview_ready = bool(
                            capability is not None and capability.audio_preview
                        )
                    except (AttributeError, RuntimeError, ValueError):
                        audio_preview_ready = selected_source == "youtube-search"
            busy = bool(self.busy_action)
            self.query.setEnabled(not busy)
            self.search_scope.setEnabled(not busy)
            self.duration_filter.setEnabled(not busy)
            self.language_filter.setEnabled(not busy)
            self.search_source.setEnabled(not busy)
            self.limit.setEnabled(not busy)
            self.history_button.setEnabled(
                not busy
                and self.history_enabled.isChecked()
                and self.search_uses_youtube_only()
            )
            self.search_button.setEnabled(not busy)
            self.next_page_button.setEnabled(
                not busy and bool(self.next_search_cursor)
            )
            self.download_button.setEnabled(selected and download_ready)
            self.download_button.setToolTip(
                f"前往 {download_workspace_name(download_provider)}"
                "確認格式、分段、字幕與網站專屬選項"
                if download_ready
                else "此結果只允許開啟官方頁，或對應下載 MOD 尚未啟用"
            )
            self.open_button.setEnabled(selected)
            self.preview_button.setEnabled(selected and audio_preview_ready and not busy)
            self.stop_preview_button.setEnabled(
                self.busy_action == "preview" or self.preview_path is not None
            )
            self.video_button.setVisible(self.video_enabled.isChecked())
            self.video_button.setEnabled(
                selected
                and selected_source == "youtube-search"
                and not busy
                and self.video_enabled.isChecked()
            )
            self.recovery_button.setEnabled(
                selected
                and selected_source == "youtube-search"
                and self.recovery_enabled.isChecked()
                and not busy
            )
            self.similar_button.setEnabled(
                selected
                and selected_source == "youtube-search"
                and self.similar_enabled.isChecked()
                and not busy
            )

        def search_uses_youtube_only(self) -> bool:
            return self.search_source.currentData() == "youtube-search"

        def populate_history_menu(self) -> None:
            self.history_menu.clear()
            if not self.history_enabled.isChecked():
                unavailable = self.history_menu.addAction("搜尋紀錄 MOD 已關閉")
                unavailable.setEnabled(False)
                return
            try:
                events = context.discovery.recent_history(limit=30)
                preferences = context.discovery.history_preferences()
            except Exception as error:
                unavailable = self.history_menu.addAction("暫時無法讀取搜尋紀錄")
                unavailable.setEnabled(False)
                unavailable.setToolTip(str(error))
                return

            summary = self.history_menu.addAction(
                history_preference_summary(preferences)
            )
            summary.setEnabled(False)
            queries = recent_history_queries(events)
            suggestions = preference_search_queries(preferences, events, limit=4)
            if suggestions:
                self.history_menu.addSeparator()
                suggestion_heading = self.history_menu.addAction("依本機偏好建議")
                suggestion_heading.setEnabled(False)
                for query in suggestions:
                    label = query if len(query) <= 52 else f"{query[:49]}…"
                    action = self.history_menu.addAction(f"建議：{label}")
                    action.setToolTip("只填入並執行一次搜尋，不會背景推薦")
                    action.triggered.connect(
                        lambda _checked=False, value=query: self.search_from_history(
                            value
                        )
                    )
            if not queries:
                empty = self.history_menu.addAction("尚無搜尋紀錄")
                empty.setEnabled(False)
                return
            self.history_menu.addSeparator()
            for query in queries:
                label = query if len(query) <= 60 else f"{query[:57]}…"
                action = self.history_menu.addAction(label)
                action.setToolTip(query)
                action.triggered.connect(
                    lambda _checked=False, value=query: self.search_from_history(
                        value
                    )
                )

        def search_from_history(self, query: str) -> None:
            self.query.setText(query)
            self.search()

        def begin_action(self, action: str) -> int | None:
            if self.closing or self.busy_action:
                return None
            self.generation += 1
            if action in {"search", "recovery", "similar"}:
                self.results_generation += 1
                self.thumbnail_loader.cancel_pending()
            self.busy_action = action
            self.update_action_state()
            return self.generation

        def search(self) -> None:
            self.next_search_cursor = ""
            self.run_search("")

        def search_next_page(self) -> None:
            if self.next_search_cursor:
                self.run_search(self.next_search_cursor)

        def run_search(self, cursor: str) -> None:
            query = " ".join(self.query.text().split())
            if not query:
                QMessageBox.information(self, "網站搜尋", "請輸入搜尋文字。")
                return
            prepared = prepare_search_query(query)
            query = prepared.query
            selected_source = str(self.search_source.currentData() or "")
            if not selected_source:
                QMessageBox.information(
                    self, "搜尋來源", "目前沒有可選擇的網站搜尋 MOD。"
                )
                return
            if not context.discovery.is_enabled(selected_source):
                QMessageBox.information(
                    self, "搜尋來源", f"請先啟用 {selected_source} MOD。"
                )
                return
            generation = self.begin_action("search")
            if generation is None:
                return
            self.last_query = query
            content_type = str(self.search_scope.currentData())
            content_label = self.search_scope.currentText()
            history_enabled = (
                self.history_enabled.isChecked() and self.search_uses_youtube_only()
            )
            provider_ids = (selected_source,)
            correction_label = (
                f"（已在本機修正：{'、'.join(prepared.corrections)}）"
                if prepared.corrections
                else ""
            )
            self.status.setText(f"正在搜尋{content_label}內容…{correction_label}")
            self.set_search_failures(())

            def worker() -> None:
                try:
                    results = context.discovery.federated_search(
                        query,
                        provider_ids=provider_ids,
                        limit=int(self.limit.currentData()),
                        content_type=content_type,
                        cursor=cursor,
                    )
                    if history_enabled:
                        try:
                            context.discovery.record_history("search", query)
                        except Exception:
                            pass
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(generation, results), ""
                        )
                except Exception as error:
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(generation, None), str(error)
                        )

            threading.Thread(target=worker, daemon=True).start()

        def find_replacement(self) -> None:
            row = self.table.currentRow()
            if not 0 <= row < len(self.results):
                QMessageBox.information(self, "尋找替代影片", "請先選擇原始影片。")
                return
            if not self.recovery_enabled.isChecked():
                QMessageBox.information(
                    self, "尋找替代影片", "請先啟用 youtube-recovery MOD。"
                )
                return
            source = self.selected_result_source()
            if source != "youtube-search":
                QMessageBox.information(
                    self,
                    "尋找替代影片",
                    "替代搜尋目前只屬於 YouTube MOD，不會把其他網站結果轉送到 YouTube。",
                )
                return
            original = self.results[row]
            limit = int(self.limit.currentData())
            generation = self.begin_action("recovery")
            if generation is None:
                return
            self.last_query = original.title
            self.status.setText("正在尋找替代候選…")

            def worker() -> None:
                try:
                    candidates = context.discovery.replacement_candidates(
                        original,
                        limit=limit,
                    )
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(
                                generation,
                                {
                                    "items": tuple(
                                        candidate.item for candidate in candidates
                                    ),
                                    "candidates": candidates,
                                    "mode": "recovery",
                                    "source": source,
                                },
                            ),
                            "",
                        )
                except Exception as error:
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(generation, None), str(error)
                        )

            threading.Thread(target=worker, daemon=True).start()

        def find_similar(self) -> None:
            row = self.table.currentRow()
            if not 0 <= row < len(self.results):
                QMessageBox.information(self, "隨機相似", "請先選擇一個原始影片。")
                return
            if not self.similar_enabled.isChecked():
                QMessageBox.information(
                    self, "隨機相似", "請先啟用 youtube-similar MOD。"
                )
                return
            source = self.selected_result_source()
            if source != "youtube-search":
                QMessageBox.information(
                    self,
                    "隨機相似",
                    "相似搜尋目前只屬於 YouTube MOD，不會把其他網站結果轉送到 YouTube。",
                )
                return
            original = self.results[row]
            limit = int(self.limit.currentData())
            generation = self.begin_action("similar")
            if generation is None:
                return
            self.last_query = f"similar {original.title}"[:200]
            self.status.setText("正在建立有限相似候選池…")

            def worker() -> None:
                try:
                    selections = context.discovery.similar_candidates(
                        original,
                        limit=limit,
                    )
                    candidates = tuple(selections)
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(
                                generation,
                                {
                                    "items": tuple(
                                        candidate.item for candidate in candidates
                                    ),
                                    "candidates": candidates,
                                    "mode": "similar",
                                    "source": source,
                                },
                            ),
                            "",
                        )
                except Exception as error:
                    if not self.closing:
                        self.bridge.finished.emit(
                            _SearchResponse(generation, None), str(error)
                        )

            threading.Thread(target=worker, daemon=True).start()

        def set_search_failures(self, failures: object) -> None:
            self.last_search_failures = (
                tuple(failures)[:16] if isinstance(failures, (list, tuple)) else ()
            )
            self.failure_button.setVisible(bool(self.last_search_failures))
            self.status.setToolTip(
                "\n".join(
                    f"{getattr(failure, 'provider_id', 'unknown')}: "
                    f"{getattr(failure, 'message', '未知錯誤')} "
                    f"[{getattr(failure, 'category', 'error')}]"
                    for failure in self.last_search_failures
                )
            )

        def show_search_failures(self) -> None:
            if not self.last_search_failures:
                return
            category_labels = {
                "timeout": "逾時",
                "invalid-response": "回應格式錯誤",
                "unavailable": "來源無法連線",
                "error": "執行錯誤",
            }
            lines = []
            for failure in self.last_search_failures:
                provider_id = str(getattr(failure, "provider_id", "unknown"))
                source = self.search_source_labels.get(provider_id, provider_id)
                category = str(getattr(failure, "category", "error"))
                label = category_labels.get(category, category)
                message = str(getattr(failure, "message", "未知錯誤"))[:300]
                lines.append(f"{source}（{label}）\n{message}")
            QMessageBox.warning(self, "搜尋來源錯誤", "\n\n".join(lines))

        def show_results(self, results: object, error: str) -> None:
            if self.closing:
                return
            if isinstance(results, _SearchResponse):
                if results.generation != self.generation:
                    return
                results = results.value
            self.thumbnail_loader.cancel_pending()
            self.busy_action = ""
            if error:
                self.set_search_failures(())
                self.results = ()
                self.result_sources = ()
                self.last_query = ""
                self.recovery_meta = {}
                self.search_rank_meta = {}
                self.table.setRowCount(0)
                self.result_stack.setCurrentWidget(self.result_empty)
                self.status.setText(f"搜尋失敗：{error}")
                self.update_action_state()
                return
            self.recovery_meta = {}
            self.search_rank_meta = {}
            if isinstance(results, dict):
                self.set_search_failures(())
                items = results.get("items")
                candidates = results.get("candidates")
                self.results = tuple(items) if isinstance(items, tuple) else ()
                source = results.get("source")
                self.result_sources = (
                    tuple(str(source) for _ in self.results)
                    if isinstance(source, str) and source
                    else ()
                )
                if isinstance(candidates, tuple):
                    self.recovery_meta = {
                        candidate.item.video_id: candidate for candidate in candidates
                    }
                mode = results.get("mode")
                label = "隨機相似結果" if mode == "similar" else "替代候選"
                self.status.setText(f"找到 {len(self.results)} 筆{label}")
            elif isinstance(results, FederatedSearchResult):
                self.set_search_failures(results.failures)
                minimum_duration, maximum_duration = self.duration_filter.currentData()
                matched = matching_search_indices(
                    results.items,
                    minimum_duration=minimum_duration,
                    maximum_duration=maximum_duration,
                    language=str(self.language_filter.currentData() or ""),
                )
                filtered_items = tuple(results.items[index] for index in matched)
                filtered_sources = tuple(results.sources[index] for index in matched)
                rankings = rank_search_results(self.last_query, filtered_items)
                self.results = tuple(
                    filtered_items[item.index] for item in rankings
                )
                self.result_sources = tuple(
                    filtered_sources[item.index] for item in rankings
                )
                self.search_rank_meta = {
                    (
                        self.result_sources[index],
                        self.results[index].video_id,
                    ): ranking
                    for index, ranking in enumerate(rankings)
                }
                cursors = dict(results.next_cursors)
                selected_source = str(self.search_source.currentData() or "")
                self.next_search_cursor = cursors.get(selected_source, "")
                if self.next_search_cursor:
                    self.next_page_button.setToolTip("載入此來源的下一頁")
                else:
                    try:
                        capabilities = context.discovery.search_capabilities()
                    except (AttributeError, RuntimeError, ValueError):
                        capabilities = ()
                    capability = next(
                        (
                            item
                            for item in capabilities
                            if item.provider_id == selected_source
                        ),
                        None,
                    )
                    self.next_page_button.setToolTip(
                        "此來源不支援分頁"
                        if capability is not None
                        and capability.pagination == "none"
                        else "目前沒有下一頁"
                    )
                if results.failures:
                    self.status.setText(
                        f"找到 {len(self.results)} 筆結果；"
                        f"{len(results.failures)} 個來源失敗"
                    )
                else:
                    self.status.setText(f"找到 {len(self.results)} 筆結果")
            else:
                self.set_search_failures(())
                self.result_sources = ()
                self.results = tuple(results) if isinstance(results, tuple) else ()
                self.status.setText(f"找到 {len(self.results)} 筆結果")
            self.refresh_search_sources()
            self.table.setRowCount(len(self.results))
            self.result_stack.setCurrentWidget(
                self.table if self.results else self.result_empty
            )
            reason_names = {
                "title": "標題",
                "artist": "歌手",
                "language": "語言",
                "category": "類別",
                "related": "相關",
                "preference": "偏好",
            }
            for row, item in enumerate(self.results):
                self.table.setRowHeight(row, 66)
                preview = QTableWidgetItem("載入中" if item.thumbnail_url else "—")
                preview.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, preview)
                title = QTableWidgetItem(item.title)
                title.setData(Qt.ItemDataRole.UserRole, item.url)
                title.setToolTip(item.url)
                self.table.setItem(row, 1, title)
                self.table.setItem(row, 2, QTableWidgetItem(item.artist or "—"))
                duration = (
                    f"{item.duration // 60}:{item.duration % 60:02d}"
                    if item.duration is not None
                    else "—"
                )
                duration_item = QTableWidgetItem(duration)
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, duration_item)
                category = QTableWidgetItem(
                    "音樂" if item.category == "music" else "影片"
                )
                category.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, category)
                source = (
                    self.result_sources[row]
                    if row < len(self.result_sources)
                    else "—"
                )
                source_item = QTableWidgetItem(
                    self.search_source_labels.get(source, source)
                )
                source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, source_item)
                candidate = self.recovery_meta.get(item.video_id)
                ranking = self.search_rank_meta.get((source, item.video_id))
                score = QTableWidgetItem(
                    f"{candidate.score}%"
                    if candidate is not None
                    else f"{ranking.score}%"
                    if ranking is not None
                    else "—"
                )
                if candidate is not None:
                    score.setToolTip(
                        "、".join(
                            reason_names.get(reason, reason)
                            for reason in candidate.reasons
                        )
                    )
                elif ranking is not None:
                    score.setToolTip("、".join(ranking.reasons) or "無直接文字符合")
                score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 6, score)
                if item.thumbnail_url:
                    self.thumbnail_loader.load(
                        item.thumbnail_url,
                        lambda pixmap, generation=self.results_generation, row=row, item=item: (
                            self.show_thumbnail(generation, row, item, pixmap)
                        ),
                    )
            self.update_action_state()

        def show_thumbnail(
            self,
            generation: int,
            row: int,
            item: object,
            pixmap: object | None,
        ) -> None:
            if (
                self.closing
                or generation != self.results_generation
                or not 0 <= row < len(self.results)
                or self.results[row] != item
            ):
                return
            cell = self.table.item(row, 0)
            if cell is not None:
                cell.setText("" if pixmap is not None else "—")
                cell.setIcon(QIcon(pixmap) if pixmap is not None else QIcon())

        def selected_result(self) -> object | None:
            row = self.table.currentRow()
            return self.results[row] if 0 <= row < len(self.results) else None

        def selected_result_source(self) -> str:
            row = self.table.currentRow()
            if 0 <= row < len(self.result_sources):
                return self.result_sources[row]
            selected = self.selected_result()
            return search_source_for_url(
                selected.url if selected is not None else ""
            )

        def selected_url(self) -> str | None:
            selected = self.selected_result()
            return selected.url if selected is not None else None

        def cleanup_audio_preview(self) -> None:
            provider = self.preview_provider
            path = self.preview_path
            self.preview_provider = None
            self.preview_path = None
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            if provider is not None and path is not None:
                try:
                    provider.cleanup_audio_preview(path)
                except OSError:
                    pass

        def stop_audio_preview(self) -> None:
            was_active = (
                self.busy_action == "preview" or self.preview_path is not None
            )
            if self.busy_action == "preview":
                self.generation += 1
                self.busy_action = ""
            self.cleanup_audio_preview()
            if was_active and not self.closing:
                self.status.setText("試聽已停止，暫存音訊已清除。")
            self.update_action_state()

        def handle_audio_status(self, status: object) -> None:
            if (
                status == QMediaPlayer.MediaStatus.EndOfMedia
                and self.preview_path is not None
            ):
                self.cleanup_audio_preview()
                if not self.closing:
                    self.status.setText("30 秒試聽已結束。")
                    self.update_action_state()

        def handle_audio_error(self, *_error: object) -> None:
            if self.preview_path is None:
                return
            message = self.audio_player.errorString() or "無法播放音訊"
            self.cleanup_audio_preview()
            if not self.closing:
                self.status.setText(f"試聽播放失敗：{message}")
                self.update_action_state()

        def cleanup_video_preview(self) -> None:
            player = self.video_player
            self.video_player = None
            if player is not None:
                player.stop()
                player.setSource(QUrl())
            dialog = self.video_dialog
            self.video_dialog = None
            if dialog is not None:
                dialog.close()
            if (
                self.video_preview_provider is not None
                and self.video_preview_path is not None
            ):
                try:
                    self.video_preview_provider.cleanup_video_preview(
                        self.video_preview_path
                    )
                except OSError:
                    pass
            self.video_preview_provider = None
            self.video_preview_path = None

        def handle_video_toggle(self, enabled: bool) -> None:
            if not enabled:
                self.cleanup_video_preview()
            self.update_action_state()

        def shutdown(self) -> None:
            if self.closing:
                return
            self.closing = True
            self.generation += 1
            self.results_generation += 1
            self.thumbnail_loader.cancel_pending()
            self.cleanup_audio_preview()
            self.cleanup_video_preview()

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

        def prepare_video_preview(self) -> None:
            selected = self.selected_result()
            if selected is None or not self.video_enabled.isChecked():
                return
            if self.selected_result_source() != "youtube-search":
                QMessageBox.information(
                    self,
                    "影片預覽",
                    "YouTube Player MOD 不會開啟其他網站的搜尋結果。",
                )
                return
            self.cleanup_video_preview()
            generation = self.begin_action("video_preview")
            if generation is None:
                return
            self.status.setText("正在準備 480p、60 秒影片預覽…")

            def worker() -> None:
                try:
                    provider = context.discovery.video_preview_provider()
                    path = provider.prepare_video_preview(
                        selected.url,
                        duration=float(selected.duration or 60),
                        preview_length=60,
                    )
                    if self.closing or generation != self.generation:
                        provider.cleanup_video_preview(path)
                        return
                    self.video_preview_bridge.finished.emit(
                        _PreviewResponse(generation, provider, path), ""
                    )
                except Exception as error:
                    if not self.closing and generation == self.generation:
                        self.video_preview_bridge.finished.emit(
                            _PreviewResponse(generation, None, None), str(error)
                        )

            threading.Thread(target=worker, daemon=True).start()

        def show_video_preview(self, result: object, error: str) -> None:
            if self.closing:
                if (
                    isinstance(result, _PreviewResponse)
                    and result.provider is not None
                    and result.path is not None
                ):
                    result.provider.cleanup_video_preview(result.path)
                return
            if (
                isinstance(result, _PreviewResponse)
                and result.generation != self.generation
            ):
                if result.provider is not None and result.path is not None:
                    result.provider.cleanup_video_preview(result.path)
                return
            self.busy_action = ""
            if (
                error
                or not isinstance(result, _PreviewResponse)
                or result.provider is None
                or result.path is None
            ):
                self.status.setText(f"影片預覽失敗：{error or '未知錯誤'}")
                self.update_action_state()
                return
            if not self.video_enabled.isChecked():
                result.provider.cleanup_video_preview(result.path)
                self.update_action_state()
                return
            self.video_preview_provider = result.provider
            self.video_preview_path = result.path
            dialog = QDialog(self)
            dialog.setWindowTitle("影片預覽（最多 60 秒）")
            dialog.resize(720, 480)
            layout = QVBoxLayout(dialog)
            video = QVideoWidget(dialog)
            layout.addWidget(video, 1)
            player = QMediaPlayer(dialog)
            audio = QAudioOutput(dialog)
            audio.setVolume(0.7)
            player.setAudioOutput(audio)
            player.setVideoOutput(video)
            player.setSource(QUrl.fromLocalFile(str(self.video_preview_path)))
            dialog._player = player
            dialog._audio = audio
            dialog.finished.connect(lambda _result: self.cleanup_video_preview())
            self.video_dialog = dialog
            self.video_player = player
            dialog.show()
            player.play()
            self.status.setText("正在播放本機暫存影片；關閉視窗後會自動清除。")
            self.update_action_state()

        def prepare_audio_preview(self) -> None:
            selected = self.selected_result()
            if selected is None:
                return
            self.cleanup_audio_preview()
            generation = self.begin_action("preview")
            if generation is None:
                return
            self.status.setText("正在準備 30 秒音訊試聽…")

            def worker() -> None:
                try:
                    provider = context.download_providers.provider_for(selected.url)
                    path = provider.prepare_audio_preview(
                        selected.url,
                        duration=float(selected.duration or 30),
                        preview_length=30,
                    )
                    if self.closing or generation != self.generation:
                        provider.cleanup_audio_preview(path)
                        return
                    self.preview_bridge.finished.emit(
                        _PreviewResponse(generation, provider, path), ""
                    )
                except Exception as error:
                    if not self.closing and generation == self.generation:
                        self.preview_bridge.finished.emit(
                            _PreviewResponse(generation, None, None), str(error)
                        )

            threading.Thread(target=worker, daemon=True).start()

        def show_audio_preview(self, result: object, error: str) -> None:
            if self.closing:
                if (
                    isinstance(result, _PreviewResponse)
                    and result.provider is not None
                    and result.path is not None
                ):
                    result.provider.cleanup_audio_preview(result.path)
                return
            if (
                isinstance(result, _PreviewResponse)
                and result.generation != self.generation
            ):
                if result.provider is not None and result.path is not None:
                    result.provider.cleanup_audio_preview(result.path)
                return
            self.busy_action = ""
            if (
                error
                or not isinstance(result, _PreviewResponse)
                or result.provider is None
                or result.path is None
            ):
                self.status.setText(f"試聽失敗：{error or '沒有音訊'}")
                self.update_action_state()
                return
            self.preview_provider = result.provider
            self.preview_path = result.path
            self.audio_player.setSource(QUrl.fromLocalFile(str(self.preview_path)))
            self.audio_player.play()
            self.status.setText("正在播放 30 秒試聽；再次試聽會自動清理前一個暫存。")
            self.update_action_state()

        def record_selected(self) -> None:
            row = self.table.currentRow()
            if (
                self.history_enabled.isChecked()
                and 0 <= row < len(self.results)
                and row < len(self.result_sources)
                and self.result_sources[row] == "youtube-search"
                and self.last_query
            ):
                try:
                    context.discovery.record_history(
                        "selection", self.last_query, self.results[row]
                    )
                except Exception:
                    pass

        def download_selected(self) -> None:
            selected = self.selected_result()
            if selected is None:
                QMessageBox.information(self, "下載設定", "請先選擇一個結果。")
                return
            provider_id = context.download_providers.matching_provider_id(selected.url)
            if not provider_id or not context.download_providers.is_enabled(provider_id):
                QMessageBox.information(
                    self,
                    "下載設定",
                    "此結果只允許開啟官方頁，或對應網站的下載 MOD 尚未啟用。",
                )
                return
            events = getattr(context, "events", None)
            workspace_name = download_workspace_name(provider_id)
            if events is None:
                QMessageBox.information(
                    self,
                    "下載設定",
                    f"目前無法開啟 {workspace_name}，請稍後再試。",
                )
                return
            events.publish(
                "download.prefill",
                {
                    "url": selected.url,
                    "provider_id": provider_id,
                    "video_id": selected.video_id,
                    "title": selected.title,
                    "artist": selected.artist,
                    "duration": selected.duration,
                    "language": selected.language,
                    "category": selected.category,
                    "thumbnail_url": selected.thumbnail_url,
                },
            )
            self.record_selected()
            self.status.setText(f"已帶入 {workspace_name}；請確認網站專屬選項。")

        def open_selected(self, *_: object) -> None:
            url = self.selected_url()
            if url:
                self.record_selected()
                QDesktopServices.openUrl(QUrl(url))

    return SearchPanel()
