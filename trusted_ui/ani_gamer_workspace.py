"""Trusted AniGamer catalog workspace with official-page-only boundaries."""

from __future__ import annotations

import threading
from urllib.parse import urlencode

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from core.localization import normalized_core_locale
from core.mod_groups import load_builtin_mod_group
from core.site_routing import classify_site_url
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.thumbnail_loader import create_thumbnail_loader


ANI_GAMER_SEARCH_PROVIDER_ID = "ani-gamer-search"
ANI_GAMER_HOME = "https://ani.gamer.com.tw/"
ANI_GAMER_LIST = "https://ani.gamer.com.tw/animeList.php"
ANI_GAMER_FILTER_TAGS = (
    "全部",
    "動作",
    "冒險",
    "奇幻",
    "異世界",
    "魔法",
    "超能力",
    "科幻",
    "機甲",
    "校園",
    "喜劇",
    "戀愛",
    "青春",
    "勵志",
    "溫馨",
    "悠閒",
    "料理",
    "親情",
    "感人",
    "運動",
    "競技",
    "偶像",
    "音樂",
    "職場",
    "推理",
    "懸疑",
    "時間穿越",
    "歷史",
    "戰爭",
    "血腥暴力",
    "靈異神怪",
    "黑暗",
    "特攝",
    "BL",
    "GL",
)
ANI_GAMER_FILTER_TYPES = ("全部", "電影", "OVA", "雙語", "泡麵番", "真人演出")
ANI_GAMER_FILTER_TARGETS = ("全部", "闔家觀賞", "付費會員", "年齡限制")
ANI_GAMER_SORTS = (("依年份排列", 1), ("依月人氣排序", 2))


def ani_gamer_catalog_url(
    tag: str = "全部",
    category: str = "全部",
    target: str = "全部",
    sort: int = 1,
) -> str:
    """Build only the official, browser-visible AniGamer filter contract."""

    if (
        tag not in ANI_GAMER_FILTER_TAGS
        or category not in ANI_GAMER_FILTER_TYPES
        or target not in ANI_GAMER_FILTER_TARGETS
        or sort not in {1, 2}
    ):
        raise ValueError("AniGamer catalog filter is invalid")
    query = urlencode(
        {
            "tags": tag,
            "category": category,
            "target": target,
            "sort": str(sort),
        }
    )
    return f"{ANI_GAMER_LIST}?{query}"


def is_official_ani_gamer_url(value: object) -> bool:
    route = classify_site_url(value)
    return route is not None and route.site_family == "ani-gamer"


def create_ani_gamer_workspace(context: object, parent: object = None) -> object:
    """Create a catalog/search surface that never downloads AniGamer streams."""

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
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class SearchBridge(QObject):
        finished = Signal(int, object, str)

    class AniGamerWorkspace(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.results: tuple[DiscoveryItemV1, ...] = ()
            self.generation = 0
            self.active_generation = 0
            self.busy = False
            self.closing = False
            self.thumbnail_loader = create_thumbnail_loader(self)
            self.bridge = SearchBridge(self)
            self.bridge.finished.connect(self.show_results)

            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            scroll = QScrollArea()
            scroll.setObjectName("workspaceScroll")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            content = QWidget()
            layout = QVBoxLayout(content)
            layout.setContentsMargins(2, 4, 2, 2)
            layout.setSpacing(12)
            scroll.setWidget(content)
            outer.addWidget(scroll)

            self.title = QLabel()
            self.title.setObjectName("sectionTitle")
            self.subtitle = QLabel()
            self.subtitle.setObjectName("sectionSubtitle")
            self.subtitle.setWordWrap(True)
            layout.addWidget(self.title)
            layout.addWidget(self.subtitle)

            boundary = QLabel(
                "安全界線：只讀取公開作品目錄與封面，並在系統瀏覽器開啟官方頁。"
                "不下載影片、不匯出彈幕、不讀取 Cookie，也不繞過登入、付費、地區或廣告。"
            )
            boundary.setObjectName("dependencySummary")
            boundary.setProperty("dependencyState", "ready")
            boundary.setWordWrap(True)
            layout.addWidget(boundary)

            browse_card = QFrame()
            browse_card.setObjectName("card")
            browse_layout = QVBoxLayout(browse_card)
            browse_layout.setContentsMargins(16, 12, 16, 12)
            browse_layout.setSpacing(8)
            quick = QHBoxLayout()
            for label, url, hint in (
                ("近期熱播", ANI_GAMER_HOME, "官網首頁的近期熱播區"),
                ("新上架", ANI_GAMER_HOME, "官網首頁的新上架區"),
                ("所有動畫", ani_gamer_catalog_url(), "官網完整作品目錄"),
                (
                    "人氣排序",
                    ani_gamer_catalog_url(sort=2),
                    "官網依月人氣排序的作品目錄",
                ),
            ):
                button = QPushButton(label)
                button.setObjectName("ghost")
                button.setToolTip(hint)
                button.clicked.connect(
                    lambda _checked=False, target_url=url, name=label: self.open_official(
                        target_url, name
                    )
                )
                quick.addWidget(button)
            quick.addStretch()
            browse_layout.addLayout(quick)

            filters = QHBoxLayout()
            filters.addWidget(QLabel("屬性"))
            self.tag_filter = QComboBox()
            self.tag_filter.setAccessibleName("動畫瘋屬性篩選")
            self.tag_filter.addItems(ANI_GAMER_FILTER_TAGS)
            filters.addWidget(self.tag_filter)
            filters.addWidget(QLabel("類型"))
            self.type_filter = QComboBox()
            self.type_filter.setAccessibleName("動畫瘋類型篩選")
            self.type_filter.addItems(ANI_GAMER_FILTER_TYPES)
            filters.addWidget(self.type_filter)
            filters.addWidget(QLabel("對象"))
            self.target_filter = QComboBox()
            self.target_filter.setAccessibleName("動畫瘋對象篩選")
            self.target_filter.addItems(ANI_GAMER_FILTER_TARGETS)
            filters.addWidget(self.target_filter)
            filters.addWidget(QLabel("排序"))
            self.sort_filter = QComboBox()
            self.sort_filter.setAccessibleName("動畫瘋目錄排序")
            for label, value in ANI_GAMER_SORTS:
                self.sort_filter.addItem(label, value)
            filters.addWidget(self.sort_filter)
            self.open_filter = QPushButton("在官網套用篩選")
            self.open_filter.setObjectName("primary")
            self.open_filter.clicked.connect(self.open_catalog_filter)
            filters.addWidget(self.open_filter)
            browse_layout.addLayout(filters)
            filter_note = QLabel(
                "介面提供單一快速篩選；需要同時選擇最多 5 個屬性時，請在開啟的官網頁面繼續複選。"
            )
            filter_note.setObjectName("sectionSubtitle")
            filter_note.setWordWrap(True)
            browse_layout.addWidget(filter_note)
            layout.addWidget(browse_card)

            search_card = QFrame()
            search_card.setObjectName("card")
            search_layout = QVBoxLayout(search_card)
            search_layout.setContentsMargins(16, 12, 16, 12)
            search_layout.setSpacing(8)
            search_row = QHBoxLayout()
            self.search_enabled = QCheckBox("啟用動畫瘋搜尋子 MOD")
            self.search_enabled.toggled.connect(self.toggle_search_mod)
            search_row.addWidget(self.search_enabled)
            self.query = QLineEdit()
            self.query.setAccessibleName("動畫瘋作品搜尋")
            self.query.setPlaceholderText("輸入作品名稱，例如：幼女戰記 2")
            self.query.setMaxLength(200)
            self.query.returnPressed.connect(self.search)
            search_row.addWidget(self.query, 1)
            self.search_button = QPushButton("搜尋官方目錄")
            self.search_button.setObjectName("primary")
            self.search_button.clicked.connect(self.search)
            search_row.addWidget(self.search_button)
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setObjectName("ghost")
            self.cancel_button.clicked.connect(self.cancel_search)
            search_row.addWidget(self.cancel_button)
            search_layout.addLayout(search_row)

            self.status = QLabel("輸入作品名稱後搜尋；結果只會開啟動畫瘋官方頁。")
            self.status.setObjectName("preview")
            self.status.setWordWrap(True)
            search_layout.addWidget(self.status)

            self.table = QTableWidget(0, 3)
            self.table.setObjectName("aniGamerResults")
            self.table.setAccessibleName("動畫瘋官方作品搜尋結果")
            self.table.setHorizontalHeaderLabels(("封面", "作品名稱", "官方頁"))
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(False)
            self.table.verticalHeader().hide()
            self.table.setIconSize(QSize(96, 54))
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 112)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self.table.itemSelectionChanged.connect(self.update_action_state)
            self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())
            search_layout.addWidget(self.table)

            actions = QHBoxLayout()
            actions.addStretch()
            self.open_selected_button = QPushButton("開啟選取作品官網")
            self.open_selected_button.clicked.connect(self.open_selected)
            actions.addWidget(self.open_selected_button)
            search_layout.addLayout(actions)
            layout.addWidget(search_card, 1)

            self.events = getattr(context, "events", None)
            if self.events is not None:
                self.events.subscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.subscribe("ui.language.changed", self.apply_language)
            self.apply_language(
                getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            self.refresh_availability()

        def apply_language(self, locale: object) -> None:
            group = load_builtin_mod_group(
                "ani-gamer", locale=normalized_core_locale(locale)
            )
            search_module = next(
                module
                for module in group.modules
                if module.provider_id == ANI_GAMER_SEARCH_PROVIDER_ID
            )
            self.title.setText(group.workspace["title"])
            self.subtitle.setText(group.workspace["subtitle"])
            self.search_enabled.setText(search_module.display_name)

        def handle_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            if payload.get("provider_id") in {"ani-gamer", ANI_GAMER_SEARCH_PROVIDER_ID}:
                self.refresh_availability()

        def refresh_availability(self) -> None:
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
                available = ANI_GAMER_SEARCH_PROVIDER_ID in {
                    status.provider_id for status in context.discovery.statuses()
                }
                enabled = (
                    parent_enabled
                    and available
                    and context.discovery.is_enabled(ANI_GAMER_SEARCH_PROVIDER_ID)
                )
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
                available = False
                enabled = False
            previous = self.search_enabled.blockSignals(True)
            self.search_enabled.setEnabled(parent_enabled and available and not self.busy)
            self.search_enabled.setChecked(enabled)
            self.search_enabled.blockSignals(previous)
            if not available:
                self.search_enabled.setText("動畫瘋搜尋子 MOD 不可用")
            elif not parent_enabled:
                self.search_enabled.setText("先啟用動畫瘋主 MOD")
            self.update_action_state()

        def toggle_search_mod(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(context, ANI_GAMER_SEARCH_PROVIDER_ID, enabled)
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as error:
                self.status.setText(f"無法變更動畫瘋搜尋 MOD：{str(error)[:240]}")
            self.refresh_availability()

        def open_official(self, url: str, label: str) -> None:
            if url not in {ANI_GAMER_HOME, ANI_GAMER_LIST} and not url.startswith(
                f"{ANI_GAMER_LIST}?"
            ):
                self.status.setText("拒絕開啟非動畫瘋官方目錄網址。")
                return
            QDesktopServices.openUrl(QUrl(url))
            self.status.setText(f"已在系統瀏覽器開啟動畫瘋「{label}」。")

        def open_catalog_filter(self) -> None:
            try:
                url = ani_gamer_catalog_url(
                    self.tag_filter.currentText(),
                    self.type_filter.currentText(),
                    self.target_filter.currentText(),
                    int(self.sort_filter.currentData()),
                )
            except (TypeError, ValueError):
                self.status.setText("動畫瘋分類條件無效。")
                return
            self.open_official(url, "所有動畫篩選")

        def search(self) -> None:
            query = " ".join(self.query.text().split())
            if not query:
                self.status.setText("請先輸入作品名稱。")
                return
            try:
                enabled = context.discovery.is_enabled(ANI_GAMER_SEARCH_PROVIDER_ID)
            except (AttributeError, KeyError, RuntimeError):
                enabled = False
            if not enabled:
                self.status.setText("請先啟用動畫瘋主 MOD 與搜尋子 MOD。")
                return
            if self.busy or self.closing:
                return
            self.generation += 1
            self.active_generation = self.generation
            generation = self.active_generation
            self.busy = True
            self.results = ()
            self.table.setRowCount(0)
            self.thumbnail_loader.cancel_pending()
            self.status.setText("正在搜尋動畫瘋官方目錄…")
            self.update_action_state()

            def worker() -> None:
                try:
                    result = context.discovery.federated_search(
                        query,
                        provider_ids=(ANI_GAMER_SEARCH_PROVIDER_ID,),
                        limit=50,
                        content_type="video",
                    )
                    error = ""
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit(generation, result, error)

            threading.Thread(
                target=worker,
                name="ani-gamer-catalog-search",
                daemon=True,
            ).start()

        def cancel_search(self) -> None:
            if not self.busy:
                return
            self.generation += 1
            self.active_generation = self.generation
            self.busy = False
            self.thumbnail_loader.cancel_pending()
            self.status.setText("已取消顯示動畫瘋搜尋結果。")
            self.update_action_state()

        def show_results(self, generation: int, response: object, error: str) -> None:
            if self.closing or generation != self.active_generation:
                return
            self.busy = False
            if error:
                self.status.setText(f"動畫瘋搜尋失敗：{error}")
                self.update_action_state()
                return
            if not isinstance(response, FederatedSearchResult):
                self.status.setText("動畫瘋搜尋失敗：搜尋 MOD 回傳格式無效。")
                self.update_action_state()
                return
            accepted = []
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                route = classify_site_url(item.url)
                if (
                    source == ANI_GAMER_SEARCH_PROVIDER_ID
                    and route is not None
                    and route.site_family == "ani-gamer"
                    and route.resource_kind == "series"
                ):
                    accepted.append(item)
            self.results = tuple(accepted)
            self.populate_results()
            if response.failures:
                self.status.setText(
                    f"動畫瘋搜尋失敗：{response.failures[0].message[:240]}"
                )
            elif self.results:
                self.status.setText(
                    f"找到 {len(self.results)} 筆官方作品；雙擊或按下按鈕開啟官網。"
                )
            else:
                self.status.setText("找不到官方作品，請改用較短或不同關鍵字。")
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
                self.table.setItem(row, 2, QTableWidgetItem("ani.gamer.com.tw"))
                if item.thumbnail_url:
                    self.thumbnail_loader.load(
                        item.thumbnail_url,
                        lambda pixmap, selected_row=row, selected=item, token=generation: self.show_thumbnail(
                            token, selected_row, selected, pixmap
                        ),
                    )
            self.update_action_state()

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
                cell.setText("無封面")
            else:
                cell.setText("")
                cell.setIcon(QIcon(pixmap))

        def selected_result(self) -> DiscoveryItemV1 | None:
            row = self.table.currentRow()
            return self.results[row] if 0 <= row < len(self.results) else None

        def open_selected(self) -> None:
            selected = self.selected_result()
            if selected is None or not is_official_ani_gamer_url(selected.url):
                self.status.setText("請先選取一筆動畫瘋官方作品。")
                return
            QDesktopServices.openUrl(QUrl(selected.url))
            self.status.setText(f"已在系統瀏覽器開啟《{selected.title}》。")

        def update_action_state(self) -> None:
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
                child_enabled = context.discovery.is_enabled(
                    ANI_GAMER_SEARCH_PROVIDER_ID
                )
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
                child_enabled = False
            self.query.setEnabled(not self.busy)
            self.search_button.setEnabled(
                parent_enabled and child_enabled and not self.busy
            )
            self.cancel_button.setEnabled(self.busy)
            self.open_filter.setEnabled(parent_enabled and not self.busy)
            self.open_selected_button.setEnabled(
                self.selected_result() is not None and not self.busy
            )

        def shutdown(self) -> None:
            if self.closing:
                return
            self.closing = True
            self.generation += 1
            self.thumbnail_loader.cancel_pending()
            if self.events is not None:
                self.events.unsubscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.unsubscribe("ui.language.changed", self.apply_language)

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return AniGamerWorkspace()
