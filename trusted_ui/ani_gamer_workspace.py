"""Trusted AniGamer catalog and episode-guide workspace."""

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
ANI_GAMER_EPISODES_PROVIDER_ID = "ani-gamer-episodes"
ANI_GAMER_HOME = "https://ani.gamer.com.tw/"
ANI_GAMER_LIST = "https://ani.gamer.com.tw/animeList.php"
ANI_GAMER_RECENT_QUERY = f"{ANI_GAMER_HOME}#recent"
ANI_GAMER_NEW_QUERY = f"{ANI_GAMER_HOME}#new"
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
    """Create a catalog/episode surface that never downloads AniGamer streams."""

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
        finished = Signal(str, int, object, str)

    class AniGamerWorkspace(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.results: tuple[DiscoveryItemV1, ...] = ()
            self.episodes: tuple[DiscoveryItemV1, ...] = ()
            self.episode_query = ""
            self.episode_cursor = ""
            self.generation = 0
            self.active_generation = 0
            self.operation = ""
            self.busy = False
            self.closing = False
            self.text: dict[str, str] = {}
            self.module_names: dict[str, str] = {}
            self.thumbnail_loader = create_thumbnail_loader(self)
            self.bridge = SearchBridge(self)
            self.bridge.finished.connect(self.show_response)

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

            self.boundary = QLabel()
            self.boundary.setObjectName("dependencySummary")
            self.boundary.setProperty("dependencyState", "ready")
            self.boundary.setWordWrap(True)
            layout.addWidget(self.boundary)

            browse_card = QFrame()
            browse_card.setObjectName("card")
            browse_layout = QVBoxLayout(browse_card)
            browse_layout.setContentsMargins(16, 12, 16, 12)
            browse_layout.setSpacing(8)
            quick = QHBoxLayout()
            self.quick_buttons: dict[str, QPushButton] = {}
            for key, catalog_query in (
                ("recent", ANI_GAMER_RECENT_QUERY),
                ("new_titles", ANI_GAMER_NEW_QUERY),
                ("all_titles", ani_gamer_catalog_url()),
                ("popular", ani_gamer_catalog_url(sort=2)),
            ):
                button = QPushButton()
                button.setObjectName("ghost")
                button.clicked.connect(
                    lambda _checked=False, query=catalog_query: self.browse_catalog(
                        query
                    )
                )
                quick.addWidget(button)
                self.quick_buttons[key] = button
            quick.addStretch()
            browse_layout.addLayout(quick)

            filters = QHBoxLayout()
            self.tag_label = QLabel()
            filters.addWidget(self.tag_label)
            self.tag_filter = QComboBox()
            self.tag_filter.addItems(ANI_GAMER_FILTER_TAGS)
            filters.addWidget(self.tag_filter)
            self.type_label = QLabel()
            filters.addWidget(self.type_label)
            self.type_filter = QComboBox()
            self.type_filter.addItems(ANI_GAMER_FILTER_TYPES)
            filters.addWidget(self.type_filter)
            self.target_label = QLabel()
            filters.addWidget(self.target_label)
            self.target_filter = QComboBox()
            self.target_filter.addItems(ANI_GAMER_FILTER_TARGETS)
            filters.addWidget(self.target_filter)
            self.sort_label = QLabel()
            filters.addWidget(self.sort_label)
            self.sort_filter = QComboBox()
            for label, value in ANI_GAMER_SORTS:
                self.sort_filter.addItem(label, value)
            filters.addWidget(self.sort_filter)
            self.open_filter = QPushButton()
            self.open_filter.setObjectName("primary")
            self.open_filter.clicked.connect(self.open_catalog_filter)
            filters.addWidget(self.open_filter)
            browse_layout.addLayout(filters)
            self.filter_note = QLabel()
            self.filter_note.setObjectName("sectionSubtitle")
            self.filter_note.setWordWrap(True)
            browse_layout.addWidget(self.filter_note)
            layout.addWidget(browse_card)

            search_card = QFrame()
            search_card.setObjectName("card")
            search_layout = QVBoxLayout(search_card)
            search_layout.setContentsMargins(16, 12, 16, 12)
            search_layout.setSpacing(8)

            mod_row = QHBoxLayout()
            self.search_enabled = QCheckBox()
            self.search_enabled.toggled.connect(self.toggle_search_mod)
            mod_row.addWidget(self.search_enabled)
            self.episodes_enabled = QCheckBox()
            self.episodes_enabled.toggled.connect(self.toggle_episodes_mod)
            mod_row.addWidget(self.episodes_enabled)
            mod_row.addStretch()
            search_layout.addLayout(mod_row)

            search_row = QHBoxLayout()
            self.query = QLineEdit()
            self.query.setMaxLength(200)
            self.query.returnPressed.connect(self.search)
            search_row.addWidget(self.query, 1)
            self.search_button = QPushButton()
            self.search_button.setObjectName("primary")
            self.search_button.clicked.connect(self.search)
            search_row.addWidget(self.search_button)
            self.cancel_button = QPushButton()
            self.cancel_button.setObjectName("ghost")
            self.cancel_button.clicked.connect(self.cancel_operation)
            search_row.addWidget(self.cancel_button)
            search_layout.addLayout(search_row)

            self.status = QLabel()
            self.status.setObjectName("preview")
            self.status.setWordWrap(True)
            search_layout.addWidget(self.status)

            self.table = QTableWidget(0, 3)
            self.table.setObjectName("aniGamerResults")
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
            self.table.itemSelectionChanged.connect(self.series_selection_changed)
            self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())
            search_layout.addWidget(self.table)

            actions = QHBoxLayout()
            actions.addStretch()
            self.load_episodes_button = QPushButton()
            self.load_episodes_button.setObjectName("primary")
            self.load_episodes_button.clicked.connect(self.load_episodes)
            actions.addWidget(self.load_episodes_button)
            self.open_selected_button = QPushButton()
            self.open_selected_button.clicked.connect(self.open_selected)
            actions.addWidget(self.open_selected_button)
            search_layout.addLayout(actions)

            self.episode_heading = QLabel()
            self.episode_heading.setObjectName("sectionTitle")
            search_layout.addWidget(self.episode_heading)
            self.episode_table = QTableWidget(0, 2)
            self.episode_table.setObjectName("aniGamerEpisodes")
            self.episode_table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            self.episode_table.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )
            self.episode_table.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
            )
            self.episode_table.setAlternatingRowColors(True)
            self.episode_table.setShowGrid(False)
            self.episode_table.verticalHeader().hide()
            episode_header = self.episode_table.horizontalHeader()
            episode_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            episode_header.setSectionResizeMode(
                1, QHeaderView.ResizeMode.ResizeToContents
            )
            self.episode_table.itemSelectionChanged.connect(self.update_action_state)
            self.episode_table.itemDoubleClicked.connect(
                lambda *_: self.open_selected_episode()
            )
            search_layout.addWidget(self.episode_table)

            episode_actions = QHBoxLayout()
            episode_actions.addStretch()
            self.load_more_button = QPushButton()
            self.load_more_button.clicked.connect(lambda: self.load_episodes(append=True))
            episode_actions.addWidget(self.load_more_button)
            self.open_episode_button = QPushButton()
            self.open_episode_button.clicked.connect(self.open_selected_episode)
            episode_actions.addWidget(self.open_episode_button)
            search_layout.addLayout(episode_actions)
            layout.addWidget(search_card, 1)

            self.events = getattr(context, "events", None)
            if self.events is not None:
                self.events.subscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.subscribe("ui.language.changed", self.apply_language)
            self.apply_language(
                getattr(getattr(context, "settings", None), "language", "zh-TW")
            )
            self.refresh_availability()

        def t(self, key: str, **values: object) -> str:
            template = self.text.get(key, key.replace("_", " "))
            try:
                return template.format(**values)
            except (KeyError, ValueError):
                return template

        def apply_language(self, locale: object) -> None:
            group = load_builtin_mod_group(
                "ani-gamer", locale=normalized_core_locale(locale)
            )
            modules = {module.provider_id: module for module in group.modules}
            self.text = dict(group.ui)
            self.module_names = {
                provider_id: modules[provider_id].display_name
                for provider_id in (
                    ANI_GAMER_SEARCH_PROVIDER_ID,
                    ANI_GAMER_EPISODES_PROVIDER_ID,
                )
            }
            self.title.setText(group.workspace["title"])
            self.subtitle.setText(group.workspace["subtitle"])
            self.boundary.setText(self.t("boundary"))
            for key, button in self.quick_buttons.items():
                button.setText(self.t(key))
                button.setToolTip(self.t(key))
            self.tag_label.setText(self.t("tag"))
            self.type_label.setText(self.t("category"))
            self.target_label.setText(self.t("audience"))
            self.sort_label.setText(self.t("sort"))
            self.tag_filter.setAccessibleName(self.t("tag"))
            self.type_filter.setAccessibleName(self.t("category"))
            self.target_filter.setAccessibleName(self.t("audience"))
            self.sort_filter.setAccessibleName(self.t("sort"))
            self.open_filter.setText(self.t("open_filter"))
            self.filter_note.setText(self.t("filter_note"))
            self.search_enabled.setText(
                modules[ANI_GAMER_SEARCH_PROVIDER_ID].display_name
            )
            self.episodes_enabled.setText(
                modules[ANI_GAMER_EPISODES_PROVIDER_ID].display_name
            )
            self.query.setAccessibleName(self.t("search"))
            self.query.setPlaceholderText(self.t("query_placeholder"))
            self.search_button.setText(self.t("search"))
            self.cancel_button.setText(self.t("cancel"))
            if not self.status.text() or not self.busy:
                self.status.setText(self.t("initial_status"))
            self.table.setAccessibleName(self.t("title"))
            self.table.setHorizontalHeaderLabels(
                (self.t("cover"), self.t("title"), self.t("official_site"))
            )
            self.load_episodes_button.setText(self.t("load_episodes"))
            self.open_selected_button.setText(self.t("open_series"))
            self.episode_heading.setText(self.t("episode_section"))
            self.episode_table.setAccessibleName(self.t("episode_section"))
            self.episode_table.setHorizontalHeaderLabels(
                (self.t("episode"), self.t("official_site"))
            )
            self.load_more_button.setText(self.t("load_more"))
            self.open_episode_button.setText(self.t("open_episode"))
            self.refresh_availability()

        def handle_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            if payload.get("provider_id") in {
                "ani-gamer",
                ANI_GAMER_SEARCH_PROVIDER_ID,
                ANI_GAMER_EPISODES_PROVIDER_ID,
            }:
                self.refresh_availability()

        def provider_state(self, provider_id: str) -> tuple[bool, bool]:
            try:
                statuses = {
                    status.provider_id: status for status in context.discovery.statuses()
                }
                status = statuses.get(provider_id)
                return status is not None, bool(status.enabled) if status else False
            except (AttributeError, KeyError, RuntimeError):
                return False, False

        def refresh_availability(self) -> None:
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
            search_available, search_enabled = self.provider_state(
                ANI_GAMER_SEARCH_PROVIDER_ID
            )
            episodes_available, episodes_enabled = self.provider_state(
                ANI_GAMER_EPISODES_PROVIDER_ID
            )
            self.search_enabled.setText(
                self.module_names.get(
                    ANI_GAMER_SEARCH_PROVIDER_ID, ANI_GAMER_SEARCH_PROVIDER_ID
                )
            )
            self.episodes_enabled.setText(
                self.module_names.get(
                    ANI_GAMER_EPISODES_PROVIDER_ID, ANI_GAMER_EPISODES_PROVIDER_ID
                )
            )
            for checkbox, available, enabled in (
                (self.search_enabled, search_available, search_enabled),
                (self.episodes_enabled, episodes_available, episodes_enabled),
            ):
                previous = checkbox.blockSignals(True)
                checkbox.setEnabled(parent_enabled and available and not self.busy)
                checkbox.setChecked(parent_enabled and available and enabled)
                checkbox.blockSignals(previous)
            if not search_available:
                self.search_enabled.setText(self.t("search_unavailable"))
            elif not parent_enabled:
                self.search_enabled.setText(self.t("parent_required"))
            if not episodes_available:
                self.episodes_enabled.setText(self.t("episodes_unavailable"))
            elif not parent_enabled:
                self.episodes_enabled.setText(self.t("parent_required"))
            self.update_action_state()

        def toggle_mod(self, provider_id: str, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(context, provider_id, enabled)
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as error:
                self.status.setText(f"{provider_id}: {str(error)[:240]}")
            self.refresh_availability()

        def toggle_search_mod(self, enabled: bool) -> None:
            self.toggle_mod(ANI_GAMER_SEARCH_PROVIDER_ID, enabled)

        def toggle_episodes_mod(self, enabled: bool) -> None:
            self.toggle_mod(ANI_GAMER_EPISODES_PROVIDER_ID, enabled)

        def open_official(self, url: str, label: str) -> None:
            if url not in {ANI_GAMER_HOME, ANI_GAMER_LIST} and not url.startswith(
                f"{ANI_GAMER_LIST}?"
            ):
                self.status.setText(self.t("catalog_rejected"))
                return
            QDesktopServices.openUrl(QUrl(url))
            self.status.setText(self.t("catalog_opened", label=label))

        def open_catalog_filter(self) -> None:
            try:
                url = ani_gamer_catalog_url(
                    self.tag_filter.currentText(),
                    self.type_filter.currentText(),
                    self.target_filter.currentText(),
                    int(self.sort_filter.currentData()),
                )
            except (TypeError, ValueError):
                self.status.setText(self.t("filter_invalid"))
                return
            self.browse_catalog(url)

        def begin_operation(self, operation: str) -> int:
            self.generation += 1
            self.active_generation = self.generation
            self.operation = operation
            self.busy = True
            self.update_action_state()
            return self.active_generation

        def search(self) -> None:
            query = " ".join(self.query.text().split())
            if not query:
                self.status.setText(self.t("enter_query"))
                return
            self.start_search(query, "search_running")

        def browse_catalog(self, query: str) -> None:
            self.start_search(query, "catalog_running")

        def start_search(self, query: str, status_key: str) -> None:
            _available, enabled = self.provider_state(ANI_GAMER_SEARCH_PROVIDER_ID)
            if not enabled:
                self.status.setText(self.t("enable_search"))
                return
            if self.busy or self.closing:
                return
            generation = self.begin_operation("search")
            self.results = ()
            self.clear_episodes()
            self.table.setRowCount(0)
            self.thumbnail_loader.cancel_pending()
            self.status.setText(self.t(status_key))

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
                    self.bridge.finished.emit("search", generation, result, error)

            threading.Thread(
                target=worker,
                name="ani-gamer-catalog-search",
                daemon=True,
            ).start()

        def load_episodes(self, _checked: bool = False, *, append: bool = False) -> None:
            selected = self.selected_result()
            if append:
                query = self.episode_query
            elif selected is not None:
                query = selected.url
            else:
                query = ""
            if not query or not is_official_ani_gamer_url(query):
                self.status.setText(self.t("select_series"))
                return
            _available, enabled = self.provider_state(ANI_GAMER_EPISODES_PROVIDER_ID)
            if not enabled:
                self.status.setText(self.t("enable_episodes"))
                return
            if self.busy or self.closing or (append and not self.episode_cursor):
                return
            cursor = self.episode_cursor if append else ""
            if not append:
                self.episodes = ()
                self.episode_table.setRowCount(0)
                self.episode_query = query
                self.episode_cursor = ""
            generation = self.begin_operation("episodes")
            self.status.setText(self.t("episodes_running"))

            def worker() -> None:
                try:
                    result = context.discovery.federated_search(
                        query,
                        provider_ids=(ANI_GAMER_EPISODES_PROVIDER_ID,),
                        limit=50,
                        content_type="video",
                        cursor=cursor,
                    )
                    error = ""
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit("episodes", generation, result, error)

            threading.Thread(
                target=worker,
                name="ani-gamer-episode-guide",
                daemon=True,
            ).start()

        def cancel_operation(self) -> None:
            if not self.busy:
                return
            cancelled_operation = self.operation
            self.generation += 1
            self.active_generation = self.generation
            self.operation = ""
            self.busy = False
            self.thumbnail_loader.cancel_pending()
            self.status.setText(
                self.t(
                    "episodes_cancelled"
                    if cancelled_operation == "episodes"
                    else "search_cancelled"
                )
            )
            self.refresh_availability()

        def show_response(
            self, operation: str, generation: int, response: object, error: str
        ) -> None:
            if self.closing or generation != self.active_generation:
                return
            self.busy = False
            self.operation = ""
            if operation == "search":
                self.show_search_results(response, error)
            else:
                self.show_episode_results(response, error)
            self.refresh_availability()

        def show_search_results(self, response: object, error: str) -> None:
            if error:
                self.status.setText(self.t("search_failed", error=error))
                return
            if not isinstance(response, FederatedSearchResult):
                self.status.setText(self.t("search_invalid"))
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
                    self.t("search_failed", error=response.failures[0].message[:240])
                )
            elif self.results:
                self.status.setText(self.t("search_found", count=len(self.results)))
            else:
                self.status.setText(self.t("search_empty"))

        def show_episode_results(self, response: object, error: str) -> None:
            if error:
                self.status.setText(self.t("episodes_failed", error=error))
                return
            if not isinstance(response, FederatedSearchResult):
                self.status.setText(self.t("episodes_invalid"))
                return
            accepted = []
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                route = classify_site_url(item.url)
                if (
                    source == ANI_GAMER_EPISODES_PROVIDER_ID
                    and route is not None
                    and route.site_family == "ani-gamer"
                    and route.resource_kind == "episode"
                ):
                    accepted.append(item)
            known = {item.video_id for item in self.episodes}
            self.episodes = self.episodes + tuple(
                item for item in accepted if item.video_id not in known
            )
            self.episode_cursor = dict(response.next_cursors).get(
                ANI_GAMER_EPISODES_PROVIDER_ID, ""
            )
            self.populate_episodes()
            if response.failures:
                self.status.setText(
                    self.t("episodes_failed", error=response.failures[0].message[:240])
                )
            elif self.episodes and self.episode_cursor:
                self.status.setText(self.t("episodes_more", count=len(self.episodes)))
            elif self.episodes:
                self.status.setText(self.t("episodes_found", count=len(self.episodes)))
            else:
                self.status.setText(self.t("episodes_empty"))

        def populate_results(self) -> None:
            self.thumbnail_loader.cancel_pending()
            generation = self.active_generation
            self.table.setRowCount(len(self.results))
            for row, item in enumerate(self.results):
                self.table.setRowHeight(row, 62)
                preview = QTableWidgetItem(self.t("loading") if item.thumbnail_url else "—")
                preview.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, preview)
                title = QTableWidgetItem(item.title)
                title.setData(Qt.ItemDataRole.UserRole, item.url)
                title.setToolTip(item.url)
                self.table.setItem(row, 1, title)
                self.table.setItem(row, 2, QTableWidgetItem(self.t("site_name")))
                if item.thumbnail_url:
                    self.thumbnail_loader.load(
                        item.thumbnail_url,
                        lambda pixmap, selected_row=row, selected=item, token=generation: self.show_thumbnail(
                            token, selected_row, selected, pixmap
                        ),
                    )
            self.update_action_state()

        def populate_episodes(self) -> None:
            self.episode_table.setRowCount(len(self.episodes))
            for row, item in enumerate(self.episodes):
                title = QTableWidgetItem(item.title)
                title.setData(Qt.ItemDataRole.UserRole, item.url)
                title.setToolTip(item.url)
                self.episode_table.setItem(row, 0, title)
                self.episode_table.setItem(
                    row, 1, QTableWidgetItem(self.t("site_name"))
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
                cell.setText(self.t("no_cover"))
            else:
                cell.setText("")
                cell.setIcon(QIcon(pixmap))

        def selected_result(self) -> DiscoveryItemV1 | None:
            row = self.table.currentRow()
            return self.results[row] if 0 <= row < len(self.results) else None

        def selected_episode(self) -> DiscoveryItemV1 | None:
            row = self.episode_table.currentRow()
            return self.episodes[row] if 0 <= row < len(self.episodes) else None

        def series_selection_changed(self) -> None:
            selected = self.selected_result()
            if selected is None or selected.url != self.episode_query:
                self.clear_episodes()
            self.update_action_state()

        def clear_episodes(self) -> None:
            self.episodes = ()
            self.episode_query = ""
            self.episode_cursor = ""
            self.episode_table.setRowCount(0)

        def open_selected(self) -> None:
            selected = self.selected_result()
            route = classify_site_url(selected.url) if selected is not None else None
            if (
                selected is None
                or route is None
                or route.site_family != "ani-gamer"
                or route.resource_kind != "series"
            ):
                self.status.setText(self.t("select_series"))
                return
            QDesktopServices.openUrl(QUrl(selected.url))
            self.status.setText(self.t("series_opened", title=selected.title))

        def open_selected_episode(self) -> None:
            selected = self.selected_episode()
            route = classify_site_url(selected.url) if selected is not None else None
            if (
                selected is None
                or route is None
                or route.site_family != "ani-gamer"
                or route.resource_kind != "episode"
            ):
                self.status.setText(self.t("select_episode"))
                return
            QDesktopServices.openUrl(QUrl(selected.url))
            self.status.setText(self.t("episode_opened", title=selected.title))

        def update_action_state(self) -> None:
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
            _search_available, search_enabled = self.provider_state(
                ANI_GAMER_SEARCH_PROVIDER_ID
            )
            _episodes_available, episodes_enabled = self.provider_state(
                ANI_GAMER_EPISODES_PROVIDER_ID
            )
            selected = self.selected_result()
            selected_episode = self.selected_episode()
            self.query.setEnabled(not self.busy)
            self.search_button.setEnabled(
                parent_enabled and search_enabled and not self.busy
            )
            for button in self.quick_buttons.values():
                button.setEnabled(
                    parent_enabled and search_enabled and not self.busy
                )
            self.cancel_button.setEnabled(self.busy)
            self.open_filter.setEnabled(
                parent_enabled and search_enabled and not self.busy
            )
            self.load_episodes_button.setEnabled(
                parent_enabled
                and episodes_enabled
                and selected is not None
                and not self.busy
            )
            self.open_selected_button.setEnabled(selected is not None and not self.busy)
            self.load_more_button.setEnabled(
                parent_enabled
                and episodes_enabled
                and bool(self.episode_cursor)
                and not self.busy
            )
            self.open_episode_button.setEnabled(
                selected_episode is not None and not self.busy
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
