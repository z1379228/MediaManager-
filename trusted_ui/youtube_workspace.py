"""Compact YouTube-only search workspace embedded in the download panel."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from itertools import chain
from urllib.parse import urlsplit

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from core.discovery.query_ranking import (
    matching_search_indices,
    prepare_search_query,
    rank_search_results,
)
from core.discovery.suggestions import (
    preference_search_queries,
    recent_history_queries,
)
from core.localization import normalized_core_locale
from core.mod_groups import load_builtin_mod_group
from core.site_routing import YOUTUBE_HOSTS, classify_site_url
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.media_preview_controls import (
    PreviewSource,
    create_media_preview_controls,
)
from trusted_ui.search_paging import merge_search_results, provider_next_cursor
from trusted_ui.thumbnail_loader import create_thumbnail_loader


YOUTUBE_SEARCH_PROVIDER_ID = "youtube-search"
YOUTUBE_SIMILAR_PROVIDER_ID = "youtube-similar"
YOUTUBE_RESULT_HOSTS = YOUTUBE_HOSTS
MAX_DOWNLOAD_URLS = 500


def is_official_youtube_url(value: object) -> bool:
    """Accept only bounded HTTPS URLs on exact official YouTube hosts."""

    route = classify_site_url(value)
    return route is not None and route.site_family == "youtube"


def youtube_host_label(url: str) -> str:
    """Return a short, user-facing label for an accepted result host."""

    host = (urlsplit(url).hostname or "").casefold()
    return {
        "youtube.com": "YouTube",
        "www.youtube.com": "YouTube",
        "m.youtube.com": "YouTube 行動版",
        "music.youtube.com": "YouTube Music",
        "youtu.be": "youtu.be",
        "www.youtube-nocookie.com": "YouTube 隱私嵌入",
        "youtubekids.com": "YouTube Kids",
        "www.youtubekids.com": "YouTube Kids",
    }.get(host, "—")


def is_youtube_playlist_url(value: object) -> bool:
    """Identify an exact-host YouTube URL with a bounded playlist id."""

    route = classify_site_url(value)
    return route is not None and route.resource_kind in {
        "playlist",
        "playlist-context",
    }


def is_youtube_video_url(value: object) -> bool:
    """Return whether a URL identifies one playable YouTube item."""

    route = classify_site_url(value)
    return route is not None and route.resource_kind in {
        "video",
        "playlist-context",
    }


def youtube_url_kind_label(value: object) -> str:
    """Describe an exact YouTube route without performing network I/O."""

    route = classify_site_url(value)
    if route is None or route.site_family != "youtube":
        return "無法辨識為受支援的 YouTube 網址"
    return {
        "video": "已確認：單一 YouTube 影片",
        "playlist": "已確認：YouTube 播放清單",
        "playlist-context": (
            "已確認：播放清單中的單一 YouTube 影片；"
            "可試聽／預覽，也可展開完整播放清單"
        ),
    }.get(route.resource_kind, "已確認：YouTube 網址")


def merge_download_urls(
    existing_text: str,
    selected_urls: Iterable[str],
    *,
    limit: int = MAX_DOWNLOAD_URLS,
) -> tuple[str, ...]:
    """Merge selected URLs into the current batch without duplicates."""

    bounded_limit = max(1, min(int(limit), MAX_DOWNLOAD_URLS))
    merged: list[str] = []
    seen: set[str] = set()
    for value in chain(existing_text.splitlines(), selected_urls):
        if not isinstance(value, str):
            continue
        url = value.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(url)
        if len(merged) >= bounded_limit:
            break
    return tuple(merged)


def _duration_label(duration: int | None) -> str:
    if duration is None:
        return "—"
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    return (
        f"{hours}:{minutes:02d}:{seconds:02d}"
        if hours
        else f"{minutes}:{seconds:02d}"
    )


def create_youtube_workspace(
    context: object,
    add_urls: Callable[[tuple[str, ...]], None],
    parent: object = None,
) -> object:
    """Create a bounded YouTube search surface that only prefills downloads."""

    from PySide6.QtCore import QObject, QSize, Qt, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMenu,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class SearchBridge(QObject):
        finished = Signal(int, object, str)

    class YouTubeWorkspace(QFrame):
        def __init__(self) -> None:
            super().__init__(parent)
            self.setObjectName("card")
            self.source_results: tuple[DiscoveryItemV1, ...] = ()
            self.results: tuple[DiscoveryItemV1, ...] = ()
            self.generation = 0
            self.active_generation = 0
            self.cancelled_generations: set[int] = set()
            self.busy = False
            self.closing = False
            self.last_query = ""
            self.last_content_type = "all"
            self.last_page_size = 20
            self.last_corrections: tuple[str, ...] = ()
            self.next_cursor = ""
            self.loading_more = False
            self.active_operation = ""
            self.result_mode = "search"
            self.selected_result_urls: set[str] = set()
            self.repopulating_results = False
            self.thumbnail_loader = create_thumbnail_loader(self)
            self.bridge = SearchBridge()
            self.bridge.finished.connect(self.show_results)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(8)

            heading = QHBoxLayout()
            labels = QVBoxLayout()
            labels.setSpacing(1)
            self.title = QLabel("YouTube 搜尋與批量選取")
            self.title.setObjectName("fieldLabel")
            self.subtitle = QLabel(
                "固定使用 YouTube 搜尋 MOD；支援 youtube.com、www、m、music 與 youtu.be。"
            )
            self.subtitle.setObjectName("sectionSubtitle")
            self.subtitle.setWordWrap(True)
            labels.addWidget(self.title)
            labels.addWidget(self.subtitle)
            heading.addLayout(labels, 1)
            self.toggle_button = QPushButton("展開搜尋")
            self.toggle_button.setObjectName("ghost")
            self.toggle_button.setCheckable(True)
            self.toggle_button.setAccessibleName("展開 YouTube 搜尋與批量選取")
            self.toggle_button.toggled.connect(self.toggle_body)
            heading.addWidget(self.toggle_button)
            layout.addLayout(heading)

            self.body = QWidget()
            body_layout = QVBoxLayout(self.body)
            body_layout.setContentsMargins(0, 4, 0, 0)
            body_layout.setSpacing(8)

            search_row = QHBoxLayout()
            self.enabled = QCheckBox("啟用 YouTube 搜尋 MOD")
            self.enabled.toggled.connect(self.toggle_search_mod)
            search_row.addWidget(self.enabled)
            self.query = QLineEdit()
            self.query.setAccessibleName("YouTube 搜尋文字或網址")
            self.query.setMaxLength(4096)
            self.query.setPlaceholderText("輸入影片／音樂關鍵字，或貼上 YouTube 網址")
            self.query.returnPressed.connect(self.search)
            search_row.addWidget(self.query, 1)
            self.search_button = QPushButton("搜尋 YouTube")
            self.search_button.setObjectName("primary")
            self.search_button.clicked.connect(self.search)
            search_row.addWidget(self.search_button)
            self.cancel_button = QPushButton("取消搜尋")
            self.cancel_button.setObjectName("ghost")
            self.cancel_button.clicked.connect(self.cancel_search)
            search_row.addWidget(self.cancel_button)
            body_layout.addLayout(search_row)

            self.status = QLabel("輸入關鍵字後搜尋；結果不會自動建立下載任務。")
            self.status.setObjectName("preview")
            self.status.setAccessibleName("YouTube 搜尋狀態")
            self.status.setWordWrap(True)
            body_layout.addWidget(self.status)

            options = QGridLayout()
            options.setSpacing(8)
            content_type_label = QLabel("內容")
            self.content_type = QComboBox()
            self.content_type.setAccessibleName("YouTube 搜尋內容類型")
            self.content_type.addItem("全部", "all")
            self.content_type.addItem("音樂", "music")
            self.content_type.addItem("影片", "video")
            content_type_label.setBuddy(self.content_type)
            options.addWidget(content_type_label, 0, 0)
            options.addWidget(self.content_type, 0, 1)
            page_size_label = QLabel("每頁")
            self.page_size = QComboBox()
            self.page_size.setAccessibleName("YouTube 每頁搜尋結果數量")
            for value in (12, 20, 30, 50):
                self.page_size.addItem(f"{value} 筆", value)
            self.page_size.setCurrentIndex(1)
            page_size_label.setBuddy(self.page_size)
            options.addWidget(page_size_label, 0, 2)
            options.addWidget(self.page_size, 0, 3)
            duration_label = QLabel("長度")
            self.duration_filter = QComboBox()
            self.duration_filter.setAccessibleName("YouTube 搜尋結果長度篩選")
            self.duration_filter.addItem("所有長度", (None, None))
            self.duration_filter.addItem("4 分鐘內", (None, 240))
            self.duration_filter.addItem("4–20 分鐘", (241, 1200))
            self.duration_filter.addItem("20 分鐘以上", (1201, None))
            duration_label.setBuddy(self.duration_filter)
            options.addWidget(duration_label, 1, 0)
            options.addWidget(self.duration_filter, 1, 1)
            sort_mode_label = QLabel("排序")
            self.sort_mode = QComboBox()
            self.sort_mode.setAccessibleName("YouTube 搜尋結果排序")
            self.sort_mode.addItem("YouTube 順序", "provider")
            self.sort_mode.addItem("本機相關度", "relevance")
            sort_mode_label.setBuddy(self.sort_mode)
            options.addWidget(sort_mode_label, 1, 2)
            options.addWidget(self.sort_mode, 1, 3)
            self.history_button = QPushButton("最近搜尋")
            self.history_button.setObjectName("ghost")
            self.history_button.setAccessibleName("YouTube 最近搜尋與本機建議")
            self.history_menu = QMenu(self.history_button)
            self.history_menu.aboutToShow.connect(self.populate_history_menu)
            self.history_button.setMenu(self.history_menu)
            options.addWidget(
                self.history_button,
                0,
                4,
                2,
                1,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            options.setColumnStretch(1, 1)
            options.setColumnStretch(3, 1)
            body_layout.addLayout(options)

            self.table = QTableWidget(0, 5)
            self.table.setAccessibleName("YouTube 搜尋結果")
            self.table.setAccessibleDescription(
                "可多選搜尋結果，再帶入同頁下載網址清單"
            )
            self.table.setHorizontalHeaderLabels(
                ["預覽", "標題", "作者", "長度", "網址來源"]
            )
            self.table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            self.table.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(False)
            self.table.verticalHeader().hide()
            self.table.setIconSize(QSize(96, 54))
            self.table.setMinimumHeight(210)
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 112)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self.table.itemSelectionChanged.connect(self.handle_selection_changed)
            self.table.itemDoubleClicked.connect(lambda *_: self.add_selected())
            body_layout.addWidget(self.table)

            self.preview_controls = create_media_preview_controls(
                self,
                source=self.selected_preview_source,
                audio_provider=lambda url: context.download_providers.provider_for(
                    url
                ),
                video_provider=lambda: context.discovery.video_preview_provider(),
                audio_available=self.audio_preview_available,
                video_available=self.video_preview_available,
                object_prefix="youtubeSearch",
            )
            body_layout.addWidget(self.preview_controls)

            actions = QHBoxLayout()
            self.more_button = QPushButton("載入更多")
            self.more_button.setObjectName("ghost")
            self.more_button.setAccessibleName("載入更多 YouTube 搜尋結果")
            self.more_button.clicked.connect(self.load_more)
            actions.addWidget(self.more_button)
            actions.addStretch()
            self.similar_button = QPushButton("搜尋相似音樂")
            self.similar_button.setObjectName("ghost")
            self.similar_button.setAccessibleName(
                "以選取的 YouTube 結果搜尋相似音樂"
            )
            self.similar_button.clicked.connect(self.find_similar_music)
            actions.addWidget(self.similar_button)
            self.add_button = QPushButton("將選取結果加入網址清單")
            self.add_button.setObjectName("primary")
            self.add_button.setAccessibleName("將選取的 YouTube 結果加入下載網址")
            self.add_button.clicked.connect(self.add_selected)
            actions.addWidget(self.add_button)
            body_layout.addLayout(actions)
            self.content_type.currentIndexChanged.connect(
                self.invalidate_network_options
            )
            self.page_size.currentIndexChanged.connect(
                self.invalidate_network_options
            )
            self.duration_filter.currentIndexChanged.connect(
                self.apply_local_result_options
            )
            self.sort_mode.currentIndexChanged.connect(
                self.apply_local_result_options
            )
            layout.addWidget(self.body)
            self.body.hide()
            self.apply_language(
                getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            self.refresh_availability()
            self.update_action_state()

        def apply_language(self, locale: object) -> None:
            selected = normalized_core_locale(locale)
            group = load_builtin_mod_group("youtube", locale=selected)
            module = next(
                item for item in group.modules if item.provider_id == "youtube-search"
            )
            suffix = {
                "zh-TW": "與批量選取",
                "zh-CN": "与批量选择",
                "en": "and Batch Selection",
                "ja": "と一括選択",
            }[selected]
            self.title.setText(f"{group.display_name} {module.display_name} {suffix}")
            self.subtitle.setText(module.purpose)
            self.more_button.setText(
                {
                    "zh-TW": "載入更多",
                    "zh-CN": "加载更多",
                    "en": "Load more",
                    "ja": "さらに読み込む",
                }[selected]
            )
            self.similar_button.setText(
                {
                    "zh-TW": "搜尋相似音樂",
                    "zh-CN": "搜索相似音乐",
                    "en": "Find Similar Music",
                    "ja": "類似音楽を検索",
                }[selected]
            )

        def history_enabled(self) -> bool:
            try:
                return context.discovery.is_enabled("youtube-history")
            except (AttributeError, KeyError, RuntimeError, ValueError):
                return False

        def populate_history_menu(self) -> None:
            self.history_menu.clear()
            if not self.history_enabled():
                unavailable = self.history_menu.addAction("YouTube 搜尋紀錄 MOD 未啟用")
                unavailable.setEnabled(False)
                return
            try:
                events = context.discovery.recent_history(limit=30)
                preferences = context.discovery.history_preferences()
            except (AttributeError, KeyError, RuntimeError, ValueError):
                unavailable = self.history_menu.addAction("暫時無法讀取本機搜尋紀錄")
                unavailable.setEnabled(False)
                return

            suggestions = preference_search_queries(
                preferences,
                events,
                limit=4,
            )
            queries = recent_history_queries(events, limit=8)
            if suggestions:
                heading = self.history_menu.addAction("依本機偏好建議")
                heading.setEnabled(False)
                for query in suggestions:
                    label = query if len(query) <= 52 else f"{query[:49]}…"
                    action = self.history_menu.addAction(f"建議：{label}")
                    action.setToolTip(query)
                    action.triggered.connect(
                        lambda _checked=False, value=query: self.search_from_history(
                            value
                        )
                    )
            if queries:
                if suggestions:
                    self.history_menu.addSeparator()
                heading = self.history_menu.addAction("最近搜尋")
                heading.setEnabled(False)
                for query in queries:
                    label = query if len(query) <= 60 else f"{query[:57]}…"
                    action = self.history_menu.addAction(label)
                    action.setToolTip(query)
                    action.triggered.connect(
                        lambda _checked=False, value=query: self.search_from_history(
                            value
                        )
                    )
            if not suggestions and not queries:
                empty = self.history_menu.addAction("尚無本機搜尋紀錄")
                empty.setEnabled(False)

        def search_from_history(self, query: str) -> None:
            self.query.setText(query)
            self.search()

        def invalidate_network_options(self) -> None:
            if self.busy or not self.last_query:
                return
            selected_content_type = str(self.content_type.currentData() or "all")
            selected_page_size = int(self.page_size.currentData() or 20)
            if (
                selected_content_type == self.last_content_type
                and selected_page_size == self.last_page_size
            ):
                return
            self.next_cursor = ""
            self.status.setText(
                "搜尋範圍或每頁筆數已變更；按「搜尋 YouTube」套用。"
                "現有結果仍保留。"
            )
            self.update_action_state()

        def ordered_visible_results(
            self,
        ) -> tuple[DiscoveryItemV1, ...]:
            minimum_duration, maximum_duration = self.duration_filter.currentData()
            matched = matching_search_indices(
                self.source_results,
                minimum_duration=minimum_duration,
                maximum_duration=maximum_duration,
            )
            visible = tuple(self.source_results[index] for index in matched)
            if (
                self.result_mode == "similar"
                or self.sort_mode.currentData() != "relevance"
            ):
                return visible
            rankings = rank_search_results(self.last_query, visible)
            return tuple(visible[ranking.index] for ranking in rankings)

        def apply_local_result_options(self) -> None:
            if self.busy:
                return
            self.selected_result_urls.update(self.selected_urls())
            self.results = self.ordered_visible_results()
            self.populate_results()
            self.restore_selected_urls(self.selected_result_urls)
            if self.source_results:
                self.status.setText(
                    f"本機篩選後顯示 {len(self.results)}／"
                    f"{len(self.source_results)} 筆結果；未重新連線。"
                )

        def toggle_body(self, expanded: bool) -> None:
            self.body.setVisible(expanded)
            self.toggle_button.setText("收合搜尋" if expanded else "展開搜尋")
            self.toggle_button.setAccessibleName(
                "收合 YouTube 搜尋與批量選取"
                if expanded
                else "展開 YouTube 搜尋與批量選取"
            )
            if expanded:
                self.query.setFocus()
            else:
                self.preview_controls.stop_all()
                self.preview_controls.refresh()

        def audio_preview_available(self) -> bool:
            return context.download_providers.is_enabled("youtube")

        def video_preview_available(self) -> bool:
            return self.audio_preview_available() and context.discovery.is_enabled(
                "youtube-player"
            )

        def selected_preview_source(self) -> PreviewSource | None:
            item = self.selected_item()
            if item is None:
                return None
            return PreviewSource(item.url, item.duration, item.title)

        def selected_item(self) -> DiscoveryItemV1 | None:
            row = self.table.currentRow()
            if not 0 <= row < len(self.results):
                return None
            return self.results[row]

        def single_selected_item(self) -> DiscoveryItemV1 | None:
            rows = {
                index.row()
                for index in self.table.selectionModel().selectedRows()
                if 0 <= index.row() < len(self.results)
            }
            if len(rows) != 1:
                return None
            return self.results[rows.pop()]

        def similar_music_available(self) -> bool:
            try:
                return (
                    context.download_providers.is_enabled("youtube")
                    and context.discovery.is_enabled(YOUTUBE_SEARCH_PROVIDER_ID)
                    and context.discovery.is_enabled(YOUTUBE_SIMILAR_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                return False

        def handle_selection_changed(self) -> None:
            if self.repopulating_results:
                return
            visible_urls = {item.url for item in self.results}
            self.selected_result_urls.difference_update(visible_urls)
            self.selected_result_urls.update(self.selected_urls())
            self.preview_controls.refresh()
            self.update_action_state()

        def refresh_availability(self) -> None:
            try:
                available = YOUTUBE_SEARCH_PROVIDER_ID in {
                    status.provider_id for status in context.discovery.statuses()
                }
                parent_enabled = context.download_providers.is_enabled("youtube")
                enabled = (
                    available
                    and parent_enabled
                    and context.discovery.is_enabled(YOUTUBE_SEARCH_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                available = False
                parent_enabled = False
                enabled = False
            previous = self.enabled.blockSignals(True)
            self.enabled.setEnabled(available and parent_enabled and not self.busy)
            self.enabled.setChecked(enabled)
            self.enabled.blockSignals(previous)
            if not available:
                self.enabled.setText("YouTube 搜尋 MOD 不可用")
                self.status.setText("YouTube 搜尋 MOD 未通過註冊或完整性檢查。")
            elif not parent_enabled:
                self.enabled.setText("先啟用 YouTube 主 MOD")
                self.status.setText("主 MOD 啟用後，才能個別啟用搜尋子 MOD。")
            else:
                self.enabled.setText("啟用 YouTube 搜尋 MOD")
                if not enabled and not self.busy:
                    self.status.setText("YouTube 搜尋 MOD 已停用；可在此直接啟用。")
            self.preview_controls.refresh()
            self.update_action_state()

        def toggle_search_mod(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(
                    context, YOUTUBE_SEARCH_PROVIDER_ID, enabled
                )
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as error:
                self.status.setText(f"無法變更 YouTube 搜尋 MOD：{str(error)[:240]}")
            self.refresh_availability()

        def search(self) -> None:
            query = " ".join(self.query.text().split())
            if not query:
                self.status.setText("請先輸入搜尋文字或 YouTube 網址。")
                return
            if is_official_youtube_url(query):
                add_urls((query,))
                self.status.setText(
                    f"已將 {youtube_host_label(query)} 網址帶入下載設定；"
                    "請確認格式、字幕或播放清單選項。"
                )
                return
            if len(query) > 200:
                self.status.setText("搜尋文字不可超過 200 個字元。")
                return
            prepared = prepare_search_query(query)
            try:
                enabled = (
                    context.download_providers.is_enabled("youtube")
                    and context.discovery.is_enabled(YOUTUBE_SEARCH_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                enabled = False
            if not enabled:
                self.status.setText("請先啟用 YouTube 搜尋 MOD。")
                return
            if self.busy or self.closing:
                return
            self.query.setText(prepared.query)
            self.last_query = prepared.query
            self.last_content_type = str(
                self.content_type.currentData() or "all"
            )
            self.last_page_size = int(self.page_size.currentData() or 20)
            self.last_corrections = prepared.corrections
            self.next_cursor = ""
            self.start_search(
                prepared.query,
                cursor="",
                append=False,
                content_type=self.last_content_type,
                page_size=self.last_page_size,
            )

        def load_more(self) -> None:
            if (
                self.busy
                or self.closing
                or (not self.source_results and not self.results)
                or not self.last_query
                or not self.next_cursor
            ):
                return
            self.start_search(
                self.last_query,
                cursor=self.next_cursor,
                append=True,
                content_type=self.last_content_type,
                page_size=self.last_page_size,
            )

        def start_search(
            self,
            query: str,
            *,
            cursor: str,
            append: bool,
            content_type: str,
            page_size: int,
        ) -> None:
            self.generation += 1
            generation = self.generation
            self.active_generation = generation
            self.active_operation = "search"
            self.busy = True
            self.loading_more = append
            if not append:
                self.result_mode = "search"
                self.source_results = ()
                self.results = ()
                self.selected_result_urls.clear()
                self.table.setRowCount(0)
            self.thumbnail_loader.cancel_pending()
            self.preview_controls.stop_all()
            if append:
                self.status.setText("正在載入更多 YouTube 結果…")
            else:
                correction_note = (
                    f"（已修正：{'、'.join(self.last_corrections)}）"
                    if self.last_corrections
                    else ""
                )
                self.status.setText(f"正在搜尋 YouTube…{correction_note}")
            self.update_action_state()

            def worker() -> None:
                try:
                    result = context.discovery.federated_search(
                        query,
                        provider_ids=(YOUTUBE_SEARCH_PROVIDER_ID,),
                        limit=page_size,
                        content_type=content_type,
                        cursor=cursor,
                    )
                    error = ""
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit(generation, result, error)

            threading.Thread(
                target=worker,
                name="youtube-workspace-search",
                daemon=True,
            ).start()

        def find_similar_music(self) -> None:
            original = self.single_selected_item()
            if original is None:
                self.status.setText("請先選擇一筆 YouTube 結果作為相似音樂來源。")
                return
            if not self.similar_music_available():
                self.status.setText(
                    "請先啟用 YouTube 主 MOD、搜尋 MOD 與相似內容 MOD。"
                )
                return
            if self.busy or self.closing:
                return

            page_size = min(20, int(self.page_size.currentData() or 20))
            self.generation += 1
            generation = self.generation
            self.active_generation = generation
            self.active_operation = "similar"
            self.busy = True
            self.loading_more = False
            self.selected_result_urls.update(self.selected_urls())
            self.thumbnail_loader.cancel_pending()
            self.preview_controls.stop_all()
            self.status.setText(
                f"正在根據「{original.title[:80]}」搜尋相似音樂…"
            )
            self.update_action_state()

            def worker() -> None:
                try:
                    selections = context.discovery.similar_candidates(
                        original,
                        limit=page_size,
                        content_type="music",
                        use_preferences=False,
                    )
                    items: list[DiscoveryItemV1] = []
                    seen: set[str] = {original.video_id}
                    for selection in selections:
                        item = selection.item
                        if item.video_id in seen:
                            continue
                        seen.add(item.video_id)
                        items.append(item)
                    result = FederatedSearchResult(
                        tuple(items),
                        (),
                        tuple(YOUTUBE_SEARCH_PROVIDER_ID for _ in items),
                    )
                    error = ""
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit(generation, result, error)

            threading.Thread(
                target=worker,
                name="youtube-similar-music-search",
                daemon=True,
            ).start()

        def cancel_search(self) -> None:
            if not self.busy:
                return
            self.cancelled_generations.add(self.active_generation)
            self.thumbnail_loader.cancel_pending()
            self.status.setText("已取消顯示；等待目前搜尋安全結束。")
            self.update_action_state()

        def show_results(
            self, generation: int, response: object, error: str
        ) -> None:
            if self.closing or generation != self.active_generation:
                return
            append = self.loading_more
            operation = self.active_operation or "search"
            self.loading_more = False
            self.active_operation = ""
            self.busy = False
            if generation in self.cancelled_generations:
                self.cancelled_generations.discard(generation)
                if operation == "similar":
                    self.populate_results()
                    self.restore_selected_urls(self.selected_result_urls)
                elif not append:
                    self.source_results = ()
                    self.results = ()
                    self.selected_result_urls.clear()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                if operation == "similar":
                    self.status.setText("相似音樂搜尋已取消。")
                else:
                    self.status.setText(
                        "已取消載入更多；原搜尋結果仍保留。"
                        if append
                        else "YouTube 搜尋已取消。"
                    )
                self.refresh_availability()
                return
            if error:
                if operation == "similar":
                    self.populate_results()
                    self.restore_selected_urls(self.selected_result_urls)
                elif not append:
                    self.source_results = ()
                    self.results = ()
                    self.selected_result_urls.clear()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                prefix = (
                    "相似音樂搜尋失敗"
                    if operation == "similar"
                    else ("載入更多失敗" if append else "YouTube 搜尋失敗")
                )
                self.status.setText(f"{prefix}：{error}")
                self.refresh_availability()
                return
            if not isinstance(response, FederatedSearchResult):
                if operation == "similar":
                    self.populate_results()
                    self.restore_selected_urls(self.selected_result_urls)
                elif not append:
                    self.source_results = ()
                    self.results = ()
                    self.selected_result_urls.clear()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                if operation == "similar":
                    self.status.setText("相似音樂搜尋失敗：回傳格式無效。")
                else:
                    self.status.setText(
                        "載入更多失敗：搜尋 MOD 回傳格式無效。"
                        if append
                        else "YouTube 搜尋失敗：搜尋 MOD 回傳格式無效。"
                    )
                self.refresh_availability()
                return

            if operation == "similar":
                self.result_mode = "similar"
                self.last_query = ""
                self.last_content_type = "music"
                self.last_corrections = ()
                self.next_cursor = ""

            accepted: list[DiscoveryItemV1] = []
            rejected = 0
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                if (
                    source != YOUTUBE_SEARCH_PROVIDER_ID
                    or not is_official_youtube_url(item.url)
                ):
                    rejected += 1
                    continue
                accepted.append(item)
            if append:
                self.selected_result_urls.update(self.selected_urls())
            else:
                self.selected_result_urls.clear()
            previous_count = len(self.source_results) if append else 0
            self.source_results = merge_search_results(
                self.source_results if append else (),
                accepted,
            )
            added_count = len(self.source_results) - previous_count
            self.results = self.ordered_visible_results()
            if not response.failures:
                self.next_cursor = provider_next_cursor(
                    response, YOUTUBE_SEARCH_PROVIDER_ID
                )
            self.populate_results()
            self.restore_selected_urls(self.selected_result_urls)
            if (
                not append
                and operation == "search"
                and not response.failures
                and self.history_enabled()
            ):
                try:
                    context.discovery.record_history("search", self.last_query)
                except (
                    AttributeError,
                    KeyError,
                    OSError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ):
                    pass
            if response.failures:
                message = response.failures[0].message[:240]
                self.status.setText(f"YouTube 搜尋失敗：{message}")
            elif self.source_results:
                suffix = f"；已略過 {rejected} 筆非官方來源" if rejected else ""
                paging = "；可繼續載入" if self.next_cursor else "；已到結果尾端"
                if operation == "similar":
                    self.status.setText(
                        f"找到 {len(self.results)} 筆相似音樂候選"
                        f"{suffix}；原始項目已排除。"
                    )
                elif append:
                    self.status.setText(
                        f"來源新增 {added_count} 筆，目前顯示 {len(self.results)}／"
                        f"{len(self.source_results)} 筆 YouTube 結果"
                        f"{suffix}{paging}。"
                    )
                else:
                    self.status.setText(
                        f"來源找到 {len(self.source_results)} 筆，目前顯示"
                        f" {len(self.results)} 筆 YouTube 結果{suffix}{paging}；"
                        "可按 Ctrl／Shift 多選。"
                    )
            else:
                self.status.setText(
                    "找不到相似音樂候選，請改選歌手或曲名較完整的結果。"
                    if operation == "similar"
                    else "找不到 YouTube 結果，請改用較短或不同關鍵字。"
                )
            self.refresh_availability()

        def populate_results(self) -> None:
            self.thumbnail_loader.cancel_pending()
            generation = self.active_generation
            self.repopulating_results = True
            try:
                self.table.setRowCount(len(self.results))
                for row, item in enumerate(self.results):
                    self.table.setRowHeight(row, 62)
                    preview = QTableWidgetItem(
                        "載入中" if item.thumbnail_url else "—"
                    )
                    preview.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 0, preview)
                    title = QTableWidgetItem(item.title)
                    title.setData(Qt.ItemDataRole.UserRole, item.url)
                    title.setToolTip(item.url)
                    self.table.setItem(row, 1, title)
                    self.table.setItem(
                        row, 2, QTableWidgetItem(item.artist or "—")
                    )
                    duration = QTableWidgetItem(_duration_label(item.duration))
                    duration.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 3, duration)
                    source = QTableWidgetItem(youtube_host_label(item.url))
                    source.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 4, source)
                    if item.thumbnail_url:
                        self.thumbnail_loader.load(
                            item.thumbnail_url,
                            lambda pixmap, generation=generation, row=row, item=item: (
                                self.show_thumbnail(generation, row, item, pixmap)
                            ),
                        )
            finally:
                self.repopulating_results = False
            self.update_action_state()

        def show_thumbnail(
            self,
            generation: int,
            row: int,
            item: DiscoveryItemV1,
            pixmap: object | None,
        ) -> None:
            if (
                self.closing
                or generation != self.active_generation
                or not 0 <= row < len(self.results)
                or self.results[row] != item
            ):
                return
            cell = self.table.item(row, 0)
            if cell is not None:
                cell.setText("" if pixmap is not None else "—")
                cell.setIcon(QIcon(pixmap) if pixmap is not None else QIcon())

        def selected_urls(self) -> tuple[str, ...]:
            rows = sorted({index.row() for index in self.table.selectedIndexes()})
            return tuple(
                self.results[row].url for row in rows if 0 <= row < len(self.results)
            )

        def restore_selected_urls(self, urls: set[str]) -> None:
            self.selected_result_urls.update(urls)
            previous = self.repopulating_results
            self.repopulating_results = True
            try:
                for row, item in enumerate(self.results):
                    if item.url not in urls:
                        continue
                    for column in range(self.table.columnCount()):
                        cell = self.table.item(row, column)
                        if cell is not None:
                            cell.setSelected(True)
            finally:
                self.repopulating_results = previous
            self.preview_controls.refresh()
            self.update_action_state()

        def add_selected(self) -> None:
            urls = self.selected_urls()
            if not urls:
                self.status.setText("請先選擇至少一筆 YouTube 搜尋結果。")
                return
            add_urls(urls)
            self.status.setText(
                f"已帶入 {len(urls)} 筆網址；請在同頁確認格式、字幕、"
                "播放清單與其他下載選項。"
            )

        def update_action_state(self) -> None:
            try:
                enabled = (
                    context.download_providers.is_enabled("youtube")
                    and context.discovery.is_enabled(YOUTUBE_SEARCH_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                enabled = False
            cancelled = self.active_generation in self.cancelled_generations
            if self.busy:
                self.enabled.setEnabled(False)
            self.query.setEnabled(not self.busy)
            self.search_button.setEnabled(enabled and not self.busy)
            self.cancel_button.setEnabled(self.busy and not cancelled)
            for control in (
                self.content_type,
                self.page_size,
                self.duration_filter,
            ):
                control.setEnabled(not self.busy)
            self.sort_mode.setEnabled(
                not self.busy and self.result_mode != "similar"
            )
            self.sort_mode.setToolTip(
                "相似音樂候選保留相似內容 MOD 的評分順序"
                if self.result_mode == "similar"
                else ""
            )
            history_available = self.history_enabled()
            self.history_button.setVisible(history_available)
            self.history_button.setEnabled(history_available and not self.busy)
            self.table.setEnabled(not self.busy)
            self.more_button.setEnabled(
                enabled
                and not self.busy
                and bool(self.source_results)
                and bool(self.next_cursor)
            )
            self.add_button.setEnabled(not self.busy and bool(self.selected_urls()))
            selected = self.single_selected_item()
            similar_available = self.similar_music_available()
            self.similar_button.setEnabled(
                not self.busy and selected is not None and similar_available
            )
            if not similar_available:
                self.similar_button.setToolTip(
                    "請先啟用 YouTube 搜尋與相似內容 MOD"
                )
            elif selected is None:
                self.similar_button.setToolTip("請先選擇一筆 YouTube 搜尋結果")
            else:
                self.similar_button.setToolTip(
                    "以目前選取項目為種子，透過公開搜尋建立相似音樂候選"
                )
            self.preview_controls.setEnabled(not self.busy)
            self.preview_controls.refresh()

        def shutdown(self) -> None:
            self.closing = True
            self.generation += 1
            self.thumbnail_loader.shutdown()
            self.preview_controls.shutdown()

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return YouTubeWorkspace()
