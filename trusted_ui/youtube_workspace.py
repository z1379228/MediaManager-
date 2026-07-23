"""Compact YouTube-only search workspace embedded in the download panel."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from itertools import chain
from urllib.parse import urlsplit

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
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
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
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
            self.results: tuple[DiscoveryItemV1, ...] = ()
            self.generation = 0
            self.active_generation = 0
            self.cancelled_generations: set[int] = set()
            self.busy = False
            self.closing = False
            self.last_query = ""
            self.next_cursor = ""
            self.loading_more = False
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
            self.add_button = QPushButton("將選取結果加入網址清單")
            self.add_button.setObjectName("primary")
            self.add_button.setAccessibleName("將選取的 YouTube 結果加入下載網址")
            self.add_button.clicked.connect(self.add_selected)
            actions.addWidget(self.add_button)
            body_layout.addLayout(actions)
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
            row = self.table.currentRow()
            if not 0 <= row < len(self.results):
                return None
            item = self.results[row]
            return PreviewSource(item.url, item.duration, item.title)

        def handle_selection_changed(self) -> None:
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
            self.last_query = query
            self.next_cursor = ""
            self.start_search(query, cursor="", append=False)

        def load_more(self) -> None:
            if (
                self.busy
                or self.closing
                or not self.results
                or not self.last_query
                or not self.next_cursor
            ):
                return
            self.start_search(
                self.last_query,
                cursor=self.next_cursor,
                append=True,
            )

        def start_search(self, query: str, *, cursor: str, append: bool) -> None:
            self.generation += 1
            generation = self.generation
            self.active_generation = generation
            self.busy = True
            self.loading_more = append
            if not append:
                self.results = ()
                self.table.setRowCount(0)
            self.thumbnail_loader.cancel_pending()
            self.preview_controls.stop_all()
            self.status.setText(
                "正在載入更多 YouTube 結果…" if append else "正在搜尋 YouTube…"
            )
            self.update_action_state()

            def worker() -> None:
                try:
                    result = context.discovery.federated_search(
                        query,
                        provider_ids=(YOUTUBE_SEARCH_PROVIDER_ID,),
                        limit=24,
                        content_type="all",
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

        def cancel_search(self) -> None:
            if not self.busy:
                return
            self.cancelled_generations.add(self.active_generation)
            self.thumbnail_loader.shutdown()
            self.status.setText("已取消顯示；等待目前搜尋安全結束。")
            self.update_action_state()

        def show_results(
            self, generation: int, response: object, error: str
        ) -> None:
            if self.closing or generation != self.active_generation:
                return
            append = self.loading_more
            self.loading_more = False
            self.busy = False
            if generation in self.cancelled_generations:
                self.cancelled_generations.discard(generation)
                if not append:
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                self.status.setText(
                    "已取消載入更多；原搜尋結果仍保留。"
                    if append
                    else "YouTube 搜尋已取消。"
                )
                self.refresh_availability()
                return
            if error:
                if not append:
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                prefix = "載入更多失敗" if append else "YouTube 搜尋失敗"
                self.status.setText(f"{prefix}：{error}")
                self.refresh_availability()
                return
            if not isinstance(response, FederatedSearchResult):
                if not append:
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                self.status.setText(
                    "載入更多失敗：搜尋 MOD 回傳格式無效。"
                    if append
                    else "YouTube 搜尋失敗：搜尋 MOD 回傳格式無效。"
                )
                self.refresh_availability()
                return

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
            selected_urls = set(self.selected_urls()) if append else set()
            previous_count = len(self.results) if append else 0
            self.results = merge_search_results(
                self.results if append else (),
                accepted,
            )
            added_count = len(self.results) - previous_count
            if not response.failures:
                self.next_cursor = provider_next_cursor(
                    response, YOUTUBE_SEARCH_PROVIDER_ID
                )
            self.populate_results()
            self.restore_selected_urls(selected_urls)
            if response.failures:
                message = response.failures[0].message[:240]
                self.status.setText(f"YouTube 搜尋失敗：{message}")
            elif self.results:
                suffix = f"；已略過 {rejected} 筆非官方來源" if rejected else ""
                paging = "；可繼續載入" if self.next_cursor else "；已到結果尾端"
                if append:
                    self.status.setText(
                        f"新增 {added_count} 筆，目前共 {len(self.results)} 筆"
                        f" YouTube 結果{suffix}{paging}。"
                    )
                else:
                    self.status.setText(
                        f"找到 {len(self.results)} 筆 YouTube 結果{suffix}{paging}；"
                        "可按 Ctrl／Shift 多選。"
                    )
            else:
                self.status.setText("找不到 YouTube 結果，請改用較短或不同關鍵字。")
            self.refresh_availability()

        def populate_results(self) -> None:
            self.thumbnail_loader.cancel_pending()
            generation = self.active_generation
            self.table.setRowCount(len(self.results))
            for row, item in enumerate(self.results):
                self.table.setRowHeight(row, 62)
                preview = QTableWidgetItem("載入中" if item.thumbnail_url else "—")
                preview.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, preview)
                title = QTableWidgetItem(item.title)
                title.setData(Qt.ItemDataRole.UserRole, item.url)
                title.setToolTip(item.url)
                self.table.setItem(row, 1, title)
                self.table.setItem(row, 2, QTableWidgetItem(item.artist or "—"))
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
            for row, item in enumerate(self.results):
                if item.url not in urls:
                    continue
                for column in range(self.table.columnCount()):
                    cell = self.table.item(row, column)
                    if cell is not None:
                        cell.setSelected(True)

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
            self.table.setEnabled(not self.busy)
            self.more_button.setEnabled(
                enabled and not self.busy and bool(self.results) and bool(self.next_cursor)
            )
            self.add_button.setEnabled(not self.busy and bool(self.selected_urls()))
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
