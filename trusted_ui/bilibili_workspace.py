"""Compact Bilibili-only search and uploader batch workspace."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from itertools import chain
from urllib.parse import urlencode, urlsplit

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.playlist_v1 import PlaylistEntryV1
from core.discovery.adapters import FederatedSearchResult
from core.localization import normalized_core_locale
from core.mod_groups import load_builtin_mod_group
from core.site_routing import classify_site_url
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.search_paging import merge_search_results, provider_next_cursor
from trusted_ui.thumbnail_loader import create_thumbnail_loader


BILIBILI_SEARCH_PROVIDER_ID = "bilibili-search"
BILIBILI_DANMAKU_PROVIDER_ID = "bilibili-danmaku"
MAX_DOWNLOAD_URLS = 500


def filter_bilibili_playlist_entries(
    entries: tuple[PlaylistEntryV1, ...], query: str
) -> tuple[PlaylistEntryV1, ...]:
    """Filter a bounded UP/multipart list without changing its order."""

    normalized = " ".join(str(query).casefold().split())[:100]
    if not normalized:
        return entries
    return tuple(
        entry
        for entry in entries
        if normalized
        in " ".join(
            (entry.title, entry.artist, entry.entry_id)
        ).casefold()
    )


def is_official_bilibili_url(value: object) -> bool:
    route = classify_site_url(value)
    return route is not None and route.download_provider_id == "bilibili"


def bilibili_host_label(url: str) -> str:
    host = (urlsplit(url).hostname or "").casefold()
    return {
        "bilibili.com": "Bilibili",
        "www.bilibili.com": "Bilibili",
        "m.bilibili.com": "Bilibili 行動版",
        "space.bilibili.com": "UP 主空間",
        "b23.tv": "b23.tv",
    }.get(host, "—")


def bilibili_url_kind_label(value: object) -> str:
    route = classify_site_url(value)
    if route is None or route.site_family != "bilibili":
        return "無法辨識為受支援的 Bilibili 網址"
    return {
        "video": "已確認：Bilibili 影片；讀取後可確認是否含分 P",
        "episode": "已確認：Bilibili 番劇單集",
        "creator": "已確認：Bilibili UP 主影片清單；請使用展開清單批量選取",
        "short-link": "已確認：Bilibili b23.tv 短網址；讀取後確認實際內容",
    }.get(route.resource_kind, "已確認：Bilibili 網址")


def bilibili_search_page_url(query: str) -> str:
    normalized = " ".join(str(query).split())[:200]
    return "https://search.bilibili.com/all?" + urlencode({"keyword": normalized})


def merge_bilibili_download_urls(
    existing_text: str,
    selected_urls: Iterable[str],
    *,
    limit: int = MAX_DOWNLOAD_URLS,
) -> tuple[str, ...]:
    bounded_limit = max(1, min(int(limit), MAX_DOWNLOAD_URLS))
    merged: list[str] = []
    seen: set[str] = set()
    for value in chain(existing_text.splitlines(), selected_urls):
        if not isinstance(value, str):
            continue
        url = value.strip()
        if not url or url in seen or not is_official_bilibili_url(url):
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


def create_bilibili_workspace(
    context: object,
    add_urls: Callable[[tuple[str, ...]], None],
    parent: object = None,
) -> object:
    """Create a Bilibili search surface with explicit uploader filtering."""

    from PySide6.QtCore import QObject, QSize, Qt, QUrl, Signal
    from PySide6.QtGui import QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QComboBox,
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

    class BilibiliWorkspace(QFrame):
        def __init__(self) -> None:
            super().__init__(parent)
            self.setObjectName("card")
            self.all_results: tuple[DiscoveryItemV1, ...] = ()
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
            self.bridge = SearchBridge(self)
            self.bridge.finished.connect(self.show_results)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(8)

            heading = QHBoxLayout()
            labels = QVBoxLayout()
            labels.setSpacing(1)
            self.title = QLabel("Bilibili 搜尋與 UP 主批量")
            self.title.setObjectName("fieldLabel")
            self.subtitle = QLabel(
                "固定使用 Bilibili 搜尋 MOD；縮圖只讀取官方 CDN，可依目前結果的 UP 主鎖定批量。"
                "貼上 UP 主空間網址時可展開最近 50 支影片。"
            )
            self.subtitle.setObjectName("sectionSubtitle")
            self.subtitle.setWordWrap(True)
            labels.addWidget(self.title)
            labels.addWidget(self.subtitle)
            heading.addLayout(labels, 1)
            self.toggle_button = QPushButton("展開搜尋")
            self.toggle_button.setObjectName("ghost")
            self.toggle_button.setCheckable(True)
            self.toggle_button.setAccessibleName("展開 Bilibili 搜尋與 UP 主批量")
            self.toggle_button.toggled.connect(self.toggle_body)
            heading.addWidget(self.toggle_button)
            layout.addLayout(heading)

            self.body = QWidget()
            body_layout = QVBoxLayout(self.body)
            body_layout.setContentsMargins(0, 4, 0, 0)
            body_layout.setSpacing(8)

            search_row = QHBoxLayout()
            self.enabled = QCheckBox("啟用 Bilibili 搜尋子 MOD")
            self.enabled.toggled.connect(self.toggle_search_mod)
            search_row.addWidget(self.enabled)
            self.danmaku_enabled = QCheckBox("啟用 Bilibili 彈幕子 MOD")
            self.danmaku_enabled.setAccessibleName("Bilibili 彈幕子 MOD 啟用狀態")
            self.danmaku_enabled.setToolTip(
                "停用後仍可下載影片，但不顯示 XML、ASS 或 MKV 彈幕選項"
            )
            self.danmaku_enabled.toggled.connect(self.toggle_danmaku_mod)
            search_row.addWidget(self.danmaku_enabled)
            self.query = QLineEdit()
            self.query.setAccessibleName("Bilibili 搜尋文字或網址")
            self.query.setMaxLength(4096)
            self.query.setPlaceholderText("輸入影片／音樂／UP 主名稱，或貼上 Bilibili 網址")
            self.query.returnPressed.connect(self.search)
            search_row.addWidget(self.query, 1)
            self.search_button = QPushButton("搜尋 Bilibili")
            self.search_button.setObjectName("primary")
            self.search_button.clicked.connect(self.search)
            search_row.addWidget(self.search_button)
            self.cancel_button = QPushButton("取消搜尋")
            self.cancel_button.setObjectName("ghost")
            self.cancel_button.clicked.connect(self.cancel_search)
            search_row.addWidget(self.cancel_button)
            self.official_search = QPushButton("官網搜尋／驗證")
            self.official_search.setObjectName("ghost")
            self.official_search.setAccessibleName("在瀏覽器開啟 Bilibili 官方搜尋")
            self.official_search.setToolTip(
                "官方要求驗證時在瀏覽器完成；MediaManager 不讀取或保存瀏覽器 Cookie"
            )
            self.official_search.clicked.connect(self.open_official_search)
            search_row.addWidget(self.official_search)
            body_layout.addLayout(search_row)

            filter_row = QHBoxLayout()
            filter_label = QLabel("UP 主篩選")
            filter_label.setObjectName("fieldLabel")
            filter_row.addWidget(filter_label)
            self.up_filter = QComboBox()
            self.up_filter.setAccessibleName("Bilibili UP 主篩選")
            self.up_filter.addItem("全部 UP 主", "")
            self.up_filter.currentIndexChanged.connect(self.apply_up_filter)
            filter_row.addWidget(self.up_filter)
            self.lock_selected_up = QPushButton("鎖定選取的 UP 主")
            self.lock_selected_up.setObjectName("ghost")
            self.lock_selected_up.clicked.connect(self.filter_selected_uploader)
            filter_row.addWidget(self.lock_selected_up)
            self.select_visible = QPushButton("選取目前全部")
            self.select_visible.setObjectName("ghost")
            self.select_visible.clicked.connect(self.table_select_all)
            filter_row.addWidget(self.select_visible)
            filter_row.addStretch()
            body_layout.addLayout(filter_row)

            self.status = QLabel("輸入關鍵字後搜尋；結果不會自動建立下載任務。")
            self.status.setObjectName("preview")
            self.status.setAccessibleName("Bilibili 搜尋狀態")
            self.status.setWordWrap(True)
            body_layout.addWidget(self.status)

            self.table = QTableWidget(0, 5)
            self.table.setAccessibleName("Bilibili 搜尋結果")
            self.table.setAccessibleDescription(
                "顯示官方縮圖、標題與 UP 主；可多選後帶入下載網址清單"
            )
            self.table.setHorizontalHeaderLabels(
                ["縮圖", "標題", "UP 主", "長度", "網址來源"]
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
            self.table.itemSelectionChanged.connect(self.update_action_state)
            self.table.itemDoubleClicked.connect(lambda *_: self.add_selected())
            body_layout.addWidget(self.table)

            actions = QHBoxLayout()
            self.more_button = QPushButton("載入更多")
            self.more_button.setObjectName("ghost")
            self.more_button.setAccessibleName("載入更多 Bilibili 搜尋結果")
            self.more_button.clicked.connect(self.load_more)
            actions.addWidget(self.more_button)
            actions.addStretch()
            self.add_button = QPushButton("將選取結果加入網址清單")
            self.add_button.setObjectName("primary")
            self.add_button.setAccessibleName("將選取的 Bilibili 結果加入下載網址")
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
            group = load_builtin_mod_group("bilibili", locale=selected)
            module = next(
                item for item in group.modules if item.provider_id == "bilibili-search"
            )
            danmaku_module = next(
                item
                for item in group.modules
                if item.provider_id == BILIBILI_DANMAKU_PROVIDER_ID
            )
            suffix = {
                "zh-TW": "與 UP 主批量",
                "zh-CN": "与 UP 主批量",
                "en": "and UP Creator Batch",
                "ja": "と UP 主一括選択",
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
            child_prefix = {
                "zh-TW": "啟用",
                "zh-CN": "启用",
                "en": "Enable",
                "ja": "有効化",
            }[selected]
            self.enabled.setText(f"{child_prefix} {module.display_name}")
            self.danmaku_enabled.setText(
                f"{child_prefix} {danmaku_module.display_name}"
            )

        def toggle_body(self, expanded: bool) -> None:
            self.body.setVisible(expanded)
            self.toggle_button.setText("收合搜尋" if expanded else "展開搜尋")
            if expanded:
                self.query.setFocus()

        def refresh_availability(self) -> None:
            try:
                available = BILIBILI_SEARCH_PROVIDER_ID in {
                    status.provider_id for status in context.discovery.statuses()
                }
                parent_enabled = context.download_providers.is_enabled("bilibili")
                enabled = (
                    available
                    and parent_enabled
                    and context.discovery.is_enabled(BILIBILI_SEARCH_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                available = False
                parent_enabled = False
                enabled = False
            try:
                danmaku_available = BILIBILI_DANMAKU_PROVIDER_ID in {
                    status.provider_id for status in context.features.statuses()
                }
                danmaku_enabled = (
                    danmaku_available
                    and parent_enabled
                    and context.features.is_enabled(BILIBILI_DANMAKU_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                danmaku_available = False
                danmaku_enabled = False
            previous = self.enabled.blockSignals(True)
            self.enabled.setEnabled(available and parent_enabled and not self.busy)
            self.enabled.setChecked(enabled)
            self.enabled.blockSignals(previous)
            previous_danmaku = self.danmaku_enabled.blockSignals(True)
            self.danmaku_enabled.setEnabled(danmaku_available and parent_enabled)
            self.danmaku_enabled.setChecked(danmaku_enabled)
            self.danmaku_enabled.blockSignals(previous_danmaku)
            if not available:
                self.enabled.setText("Bilibili 搜尋子 MOD 不可用")
                self.status.setText("Bilibili 搜尋子 MOD 未通過註冊或完整性檢查。")
            elif not parent_enabled:
                self.enabled.setText("先啟用 Bilibili 主 MOD")
                self.status.setText("主 MOD 啟用後，才能個別啟用搜尋子 MOD。")
            else:
                self.enabled.setText("啟用 Bilibili 搜尋子 MOD")
                if not enabled and not self.busy:
                    self.status.setText("Bilibili 搜尋子 MOD 已停用；可在此直接啟用。")
            if not danmaku_available:
                self.danmaku_enabled.setText("Bilibili 彈幕子 MOD 不可用")
            elif not parent_enabled:
                self.danmaku_enabled.setText("先啟用 Bilibili 主 MOD")
            elif not danmaku_enabled:
                self.danmaku_enabled.setText("啟用 Bilibili 彈幕子 MOD")
            self.update_action_state()

        def toggle_search_mod(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(
                    context, BILIBILI_SEARCH_PROVIDER_ID, enabled
                )
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as error:
                self.status.setText(f"無法變更 Bilibili 搜尋 MOD：{str(error)[:240]}")
            self.refresh_availability()

        def toggle_danmaku_mod(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(
                    context, BILIBILI_DANMAKU_PROVIDER_ID, enabled
                )
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as error:
                self.status.setText(f"無法變更 Bilibili 彈幕 MOD：{str(error)[:240]}")
            self.refresh_availability()

        def search(self) -> None:
            query = " ".join(self.query.text().split())
            if not query:
                self.status.setText("請先輸入搜尋文字或 Bilibili 網址。")
                return
            if is_official_bilibili_url(query):
                add_urls((query,))
                self.status.setText(
                    f"已將 {bilibili_host_label(query)} 網址帶入下載設定。"
                )
                return
            if len(query) > 200:
                self.status.setText("搜尋文字不可超過 200 個字元。")
                return
            try:
                enabled = context.discovery.is_enabled(BILIBILI_SEARCH_PROVIDER_ID)
            except (AttributeError, KeyError, RuntimeError, ValueError):
                enabled = False
            if not enabled:
                self.status.setText("請先啟用 Bilibili 主 MOD 與搜尋子 MOD。")
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
                or not self.all_results
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
                self.all_results = ()
                self.results = ()
                self.table.setRowCount(0)
                self.up_filter.setCurrentIndex(0)
            self.thumbnail_loader.cancel_pending()
            self.status.setText(
                "正在載入更多 Bilibili 結果…" if append else "正在搜尋 Bilibili…"
            )
            self.update_action_state()

            def worker() -> None:
                try:
                    result = context.discovery.federated_search(
                        query,
                        provider_ids=(BILIBILI_SEARCH_PROVIDER_ID,),
                        limit=50,
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
                name="bilibili-workspace-search",
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
            self.loading_more = False
            self.busy = False
            if generation in self.cancelled_generations:
                self.cancelled_generations.discard(generation)
                if not append:
                    self.all_results = ()
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                self.status.setText(
                    "已取消載入更多；原搜尋結果仍保留。"
                    if append
                    else "Bilibili 搜尋已取消。"
                )
                self.refresh_availability()
                return
            if error:
                if not append:
                    self.all_results = ()
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                prefix = "載入更多失敗" if append else "Bilibili 搜尋失敗"
                self.status.setText(
                    f"{prefix}：{error}；可按「官網搜尋／驗證」後貼回影片網址。"
                )
                self.refresh_availability()
                return
            if not isinstance(response, FederatedSearchResult):
                if not append:
                    self.all_results = ()
                    self.results = ()
                    self.table.setRowCount(0)
                    self.next_cursor = ""
                self.status.setText(
                    "載入更多失敗：搜尋 MOD 回傳格式無效。"
                    if append
                    else "Bilibili 搜尋失敗：搜尋 MOD 回傳格式無效。"
                )
                self.refresh_availability()
                return
            accepted: list[DiscoveryItemV1] = []
            rejected = 0
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                if (
                    source != BILIBILI_SEARCH_PROVIDER_ID
                    or not is_official_bilibili_url(item.url)
                ):
                    rejected += 1
                    continue
                accepted.append(item)
            selected_urls = set(self.selected_urls()) if append else set()
            previous_count = len(self.all_results) if append else 0
            self.all_results = merge_search_results(
                self.all_results if append else (),
                accepted,
            )
            added_count = len(self.all_results) - previous_count
            if not response.failures:
                self.next_cursor = provider_next_cursor(
                    response, BILIBILI_SEARCH_PROVIDER_ID
                )
            self.populate_uploader_filter()
            self.apply_up_filter()
            self.restore_selected_urls(selected_urls)
            if response.failures:
                self.status.setText(
                    f"Bilibili 搜尋失敗：{response.failures[0].message[:240]}"
                )
            elif self.results:
                uploader_count = len(
                    {item.artist for item in self.all_results if item.artist}
                )
                suffix = f"；略過 {rejected} 筆非官方來源" if rejected else ""
                paging = "；可繼續載入" if self.next_cursor else "；已到結果尾端"
                if append:
                    self.status.setText(
                        f"新增 {added_count} 筆，目前共 {len(self.all_results)} 筆、"
                        f"{uploader_count} 位 UP 主{suffix}{paging}。"
                    )
                else:
                    self.status.setText(
                        f"找到 {len(self.all_results)} 筆、{uploader_count} 位 UP 主"
                        f"{suffix}{paging}；可先鎖定 UP 主，再批量選取。"
                    )
            else:
                self.status.setText("找不到 Bilibili 結果，請改用較短或不同關鍵字。")
            self.refresh_availability()

        def populate_uploader_filter(self) -> None:
            current = str(self.up_filter.currentData() or "")
            uploaders = tuple(
                sorted({item.artist for item in self.all_results if item.artist})
            )
            previous = self.up_filter.blockSignals(True)
            self.up_filter.clear()
            self.up_filter.addItem("全部 UP 主", "")
            for uploader in uploaders:
                self.up_filter.addItem(uploader, uploader)
            index = self.up_filter.findData(current)
            self.up_filter.setCurrentIndex(max(0, index))
            self.up_filter.blockSignals(previous)

        def apply_up_filter(self, *_: object) -> None:
            uploader = str(self.up_filter.currentData() or "")
            self.results = tuple(
                item
                for item in self.all_results
                if not uploader or item.artist == uploader
            )
            self.populate_results()
            self.update_action_state()

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
                source = QTableWidgetItem(bilibili_host_label(item.url))
                source.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, source)
                if item.thumbnail_url:
                    self.thumbnail_loader.load(
                        item.thumbnail_url,
                        lambda pixmap, row=row, item=item, generation=generation: (
                            self.show_thumbnail(generation, row, item, pixmap)
                        ),
                    )

        def show_thumbnail(
            self,
            generation: int,
            row: int,
            item: DiscoveryItemV1,
            pixmap: object,
        ) -> None:
            if (
                self.closing
                or generation != self.active_generation
                or not 0 <= row < len(self.results)
                or self.results[row] != item
            ):
                return
            cell = self.table.item(row, 0)
            if cell is None:
                return
            if pixmap is None:
                cell.setText("無縮圖")
                return
            cell.setText("")
            cell.setIcon(QIcon(pixmap))

        def filter_selected_uploader(self) -> None:
            row = self.table.currentRow()
            if not 0 <= row < len(self.results):
                return
            uploader = self.results[row].artist
            if not uploader:
                return
            index = self.up_filter.findData(uploader)
            if index >= 0:
                self.up_filter.setCurrentIndex(index)

        def table_select_all(self) -> None:
            if self.results:
                self.table.selectAll()
            self.update_action_state()

        def open_official_search(self) -> None:
            query = " ".join(self.query.text().split())
            target = query if is_official_bilibili_url(query) else bilibili_search_page_url(query)
            QDesktopServices.openUrl(QUrl(target))

        def selected_urls(self) -> tuple[str, ...]:
            rows = sorted(
                {index.row() for index in self.table.selectionModel().selectedRows()}
            )
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
                self.status.setText("請至少選取一筆 Bilibili 結果。")
                return
            add_urls(urls)
            uploader = str(self.up_filter.currentData() or "")
            qualifier = f"（UP 主：{uploader}）" if uploader else ""
            self.status.setText(
                f"已帶入 {len(urls)} 筆 Bilibili 網址{qualifier}；"
                "請確認格式、字幕與分 P；彈幕選項只在彈幕子 MOD 啟用時顯示。"
            )

        def update_action_state(self) -> None:
            try:
                parent_enabled = context.download_providers.is_enabled("bilibili")
                search_enabled = context.discovery.is_enabled(
                    BILIBILI_SEARCH_PROVIDER_ID
                )
            except (AttributeError, KeyError, RuntimeError, ValueError):
                parent_enabled = False
                search_enabled = False
            can_search = parent_enabled and search_enabled and not self.busy
            self.query.setEnabled(not self.busy)
            self.search_button.setEnabled(can_search)
            self.cancel_button.setEnabled(self.busy)
            self.official_search.setEnabled(not self.busy)
            has_results = bool(self.results) and not self.busy
            self.up_filter.setEnabled(bool(self.all_results) and not self.busy)
            self.lock_selected_up.setEnabled(
                has_results and self.table.currentRow() >= 0
            )
            self.select_visible.setEnabled(has_results)
            self.more_button.setEnabled(
                can_search and bool(self.all_results) and bool(self.next_cursor)
            )
            self.add_button.setEnabled(bool(self.selected_urls()) and not self.busy)

        def shutdown(self) -> None:
            self.closing = True
            self.generation += 1
            self.thumbnail_loader.cancel_pending()

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return BilibiliWorkspace()
