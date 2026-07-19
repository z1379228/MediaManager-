"""Trusted AniGamer catalog and episode-guide workspace."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from enum import Enum
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from core.localization import normalized_core_locale
from core.mod_groups import load_builtin_mod_group
from core.site_routing import classify_site_url
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.ani_gamer_offline import (
    ALLOWED_LOCAL_MEDIA_SUFFIXES,
    ALLOWED_LOCAL_SUBTITLE_SUFFIXES,
    AniGamerArchiveVerification,
    LocalMediaPlaybackCapability,
    LocalMediaRuntimeSupport,
    OfflineImportCancelled,
    classify_local_media_playback_selection,
    classify_local_media_player_error,
    create_episode_archive,
    import_local_media,
    import_local_subtitles,
    local_media_playback_status_key,
    local_media_runtime_support,
    safe_local_media_display_name,
    validate_local_media_selection,
    verify_episode_archive,
)
from trusted_ui.ani_gamer_history import (
    AniGamerHistoryEntry,
    clear_history,
    export_history,
    history_path,
    load_history,
    record_history,
)
from trusted_ui.thumbnail_loader import create_thumbnail_loader


ANI_GAMER_SEARCH_PROVIDER_ID = "ani-gamer-search"
ANI_GAMER_EPISODES_PROVIDER_ID = "ani-gamer-episodes"
ANI_GAMER_OFFLINE_PROVIDER_ID = "ani-gamer-offline"
ANI_GAMER_PLAYER_PROVIDER_ID = "ani-gamer-player"
ANI_GAMER_HOME = "https://ani.gamer.com.tw/"
ANI_GAMER_LIST = "https://ani.gamer.com.tw/animeList.php"
ANI_GAMER_RECENT_QUERY = f"{ANI_GAMER_HOME}#recent"
ANI_GAMER_NEW_QUERY = f"{ANI_GAMER_HOME}#new"
ANI_GAMER_BROWSER_VERIFICATION_ERROR = (
    "ani-gamer-browser-verification-required"
)


class WebEngineMediaCapability(str, Enum):
    """Locally observable WebEngine media capability, not site playability."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


ANI_GAMER_MEDIA_CAPABILITY_PROBE = r"""
(() => {
  const video = document.createElement("video");
  const canPlay = typeof video.canPlayType === "function";
  const hasMse = typeof MediaSource !== "undefined" &&
    typeof MediaSource.isTypeSupported === "function";
  const h264 = canPlay && Boolean(
    video.canPlayType('video/mp4; codecs="avc1.42E01E"')
  );
  const aac = canPlay && Boolean(
    video.canPlayType('audio/mp4; codecs="mp4a.40.2"')
  );
  const hls = canPlay && Boolean(
    video.canPlayType('application/vnd.apple.mpegurl') ||
    video.canPlayType('application/x-mpegURL')
  );
  const mseH264Aac = hasMse && Boolean(
    MediaSource.isTypeSupported(
      'video/mp4; codecs="avc1.42E01E, mp4a.40.2"'
    )
  );
  return JSON.stringify({
    html5Video: canPlay,
    mse: hasMse,
    h264: h264,
    aac: aac,
    hls: hls,
    mseH264Aac: mseH264Aac
  });
})()
""".strip()
ANI_GAMER_MEDIA_PROBE_WORLD_ID = 1  # QWebEngineScript.ApplicationWorld


def classify_webengine_media_capability(
    value: object,
) -> WebEngineMediaCapability:
    """Classify an offline capability probe without inspecting site content."""

    if isinstance(value, str):
        if len(value) > 1_024:
            return WebEngineMediaCapability.UNKNOWN
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return WebEngineMediaCapability.UNKNOWN
    if not isinstance(value, Mapping):
        return WebEngineMediaCapability.UNKNOWN
    fields = ("html5Video", "mse", "h264", "aac", "hls", "mseH264Aac")
    observations = tuple(value.get(field) for field in fields)
    if not all(isinstance(observation, bool) for observation in observations):
        return WebEngineMediaCapability.UNKNOWN
    html5_video, mse, h264, aac, hls, mse_h264_aac = observations
    if html5_video and h264 and aac and (hls or (mse and mse_h264_aac)):
        return WebEngineMediaCapability.SUPPORTED
    return WebEngineMediaCapability.UNSUPPORTED


def wire_ani_gamer_web_view_diagnostics(
    view: object,
    *,
    on_page_loaded: Callable[[], None],
    on_load_failed: Callable[[], None],
    on_capability: Callable[[WebEngineMediaCapability], None],
    on_renderer_terminated: Callable[[], None],
) -> None:
    """Wire testable WebEngine diagnostics without reading page data or cookies."""

    def handle_load_finished(ok: bool) -> None:
        if not ok:
            on_load_failed()
            return
        on_page_loaded()
        try:
            page = view.page()
            page.runJavaScript(
                ANI_GAMER_MEDIA_CAPABILITY_PROBE,
                ANI_GAMER_MEDIA_PROBE_WORLD_ID,
                lambda result: on_capability(
                    classify_webengine_media_capability(result)
                ),
            )
        except (AttributeError, RuntimeError, TypeError):
            on_capability(WebEngineMediaCapability.UNKNOWN)

    view.loadFinished.connect(handle_load_finished)
    try:
        view.renderProcessTerminated.connect(
            lambda *_details: on_renderer_terminated()
        )
    except (AttributeError, RuntimeError, TypeError):
        # Older Qt bindings may not expose this signal. Load/probe diagnostics
        # remain available and the system-browser fallback is unaffected.
        pass


def open_ani_gamer_system_browser(
    url: str,
    opener: Callable[[str], object],
) -> bool:
    """Open only a credential-free official HTTPS URL via a supplied opener."""

    try:
        parsed = urlsplit(url)
        allowed = (
            parsed.scheme == "https"
            and (parsed.hostname or "").casefold() == "ani.gamer.com.tw"
            and not parsed.username
            and not parsed.password
            and parsed.port in {None, 443}
        )
        return bool(opener(url)) if allowed else False
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def detect_qt_local_media_runtime_support(
    media_format_class: object,
) -> LocalMediaRuntimeSupport:
    """Read bounded Qt Multimedia enum names without probing any media file."""

    try:
        decode = media_format_class.ConversionMode.Decode
        media_format = media_format_class()
        file_formats = {
            value.name for value in media_format.supportedFileFormats(decode)
        }
        audio_codecs = {
            value.name for value in media_format.supportedAudioCodecs(decode)
        }
    except (AttributeError, RuntimeError, TypeError):
        return LocalMediaRuntimeSupport(
            frozenset(),
            frozenset(),
            frozenset(ALLOWED_LOCAL_MEDIA_SUFFIXES),
        )
    return local_media_runtime_support(file_formats, audio_codecs)
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


def is_ani_gamer_navigation_allowed(url: object, is_main_frame: bool) -> bool:
    """Keep top-level navigation official while allowing page subresources."""

    if not is_main_frame:
        return True
    try:
        return (
            url.scheme() == "https"
            and (url.host() or "").casefold() == "ani.gamer.com.tw"
            and not url.userName()
            and not url.password()
            and url.port() in {-1, 443}
        )
    except (AttributeError, RuntimeError, TypeError):
        return False


def manual_official_episode(value: str, title: str) -> DiscoveryItemV1 | None:
    route = classify_site_url(value)
    if (
        route is None
        or route.site_family != "ani-gamer"
        or route.resource_kind != "episode"
    ):
        return None
    values = parse_qs(urlsplit(value).query, keep_blank_values=True)
    serials = values.get("sn", ())
    if len(serials) != 1 or not serials[0].isdecimal():
        return None
    serial = serials[0]
    return DiscoveryItemV1(
        f"ani-episode-{serial}",
        f"https://ani.gamer.com.tw/animeVideo.php?sn={serial}",
        title[:300],
        "動畫瘋官方集數",
        None,
        "",
        "video",
        "",
    )


def configure_ani_gamer_web_view(view: object) -> bool:
    """Apply playback-friendly settings without bypassing site controls."""

    try:
        from PySide6.QtWebEngineCore import QWebEngineSettings

        settings = view.settings()
        attributes = QWebEngineSettings.WebAttribute
        for attribute in (
            attributes.JavascriptEnabled,
            attributes.LocalStorageEnabled,
            attributes.FullScreenSupportEnabled,
        ):
            settings.setAttribute(attribute, True)
        settings.setAttribute(attributes.PlaybackRequiresUserGesture, False)
    except (AttributeError, ImportError, RuntimeError, TypeError):
        return False
    return True


def create_ani_gamer_workspace(context: object, parent: object = None) -> object:
    """Create a catalog/episode surface that never downloads AniGamer streams."""

    from PySide6.QtCore import QBuffer, QIODevice, QObject, QSize, Qt, QTimer, QUrl, Signal
    from PySide6.QtGui import QAction, QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QFrame,
        QFileDialog,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLayout,
        QLineEdit,
        QMessageBox,
        QMenu,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        QWebEnginePage = None
        QWebEngineView = None

    try:
        from PySide6.QtMultimedia import QAudioOutput, QMediaFormat, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
    except ImportError:
        QAudioOutput = None
        QMediaFormat = None
        QMediaPlayer = None
        QVideoWidget = None

    class SearchBridge(QObject):
        finished = Signal(str, int, object, str)

    if QWebEnginePage is not None:

        class OfficialPage(QWebEnginePage):
            """Allow top-level navigation only inside AniGamer official pages."""

            def acceptNavigationRequest(
                self, url, navigation_type, is_main_frame
            ):
                return is_ani_gamer_navigation_allowed(url, is_main_frame)

    else:
        OfficialPage = None

    class AniGamerWorkspace(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.results: tuple[DiscoveryItemV1, ...] = ()
            self.episodes: tuple[DiscoveryItemV1, ...] = ()
            self.episode_query = ""
            self.episode_cursor = ""
            self.episode_replace_pending = False
            self.retry_kind = ""
            self.retry_query = ""
            self.retry_status_key = ""
            self.retry_episode_append = False
            self.generation = 0
            self.active_generation = 0
            self.operation = ""
            self.busy = False
            self.closing = False
            self.offline_cancel_event = threading.Event()
            self.offline_archive_root: Path | None = None
            self.history_file = history_path(Path(context.paths.data))
            self.text: dict[str, str] = {}
            self.module_names: dict[str, str] = {}
            self._browser_dialogs: list[object] = []
            self.embedded_web_engine_available = (
                QWebEngineView is not None and OfficialPage is not None
            )
            self.local_media_dialog: object | None = None
            self.local_media_player: object | None = None
            self.local_media_queue: tuple[Path, ...] = ()
            self.local_media_index = -1
            self.thumbnail_loader = create_thumbnail_loader(self)
            self.bridge = SearchBridge(self)
            self.bridge.finished.connect(self.show_response)

            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            self.scroll_area = QScrollArea()
            self.scroll_area.setObjectName("workspaceScroll")
            self.scroll_area.setAccessibleName("動畫瘋目錄與集數捲動內容")
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            self.scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.scroll_content = QWidget()
            layout = QVBoxLayout(self.scroll_content)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            layout.setContentsMargins(2, 4, 2, 2)
            layout.setSpacing(12)
            self.scroll_area.setWidget(self.scroll_content)
            outer.addWidget(self.scroll_area)

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

            filters = QGridLayout()
            filters.setHorizontalSpacing(8)
            filters.setVerticalSpacing(8)
            self.tag_label = QLabel()
            filters.addWidget(self.tag_label, 0, 0)
            self.tag_filter = QComboBox()
            self.tag_filter.addItems(ANI_GAMER_FILTER_TAGS)
            filters.addWidget(self.tag_filter, 0, 1)
            self.type_label = QLabel()
            filters.addWidget(self.type_label, 0, 2)
            self.type_filter = QComboBox()
            self.type_filter.addItems(ANI_GAMER_FILTER_TYPES)
            filters.addWidget(self.type_filter, 0, 3)
            self.target_label = QLabel()
            filters.addWidget(self.target_label, 1, 0)
            self.target_filter = QComboBox()
            self.target_filter.addItems(ANI_GAMER_FILTER_TARGETS)
            filters.addWidget(self.target_filter, 1, 1)
            self.sort_label = QLabel()
            filters.addWidget(self.sort_label, 1, 2)
            self.sort_filter = QComboBox()
            for label, value in ANI_GAMER_SORTS:
                self.sort_filter.addItem(label, value)
            filters.addWidget(self.sort_filter, 1, 3)
            self.open_filter = QPushButton()
            self.open_filter.setObjectName("primary")
            self.open_filter.clicked.connect(self.open_catalog_filter)
            filters.setColumnStretch(1, 1)
            filters.setColumnStretch(3, 1)
            browse_layout.addLayout(filters)
            filter_actions = QVBoxLayout()
            filter_actions.setSpacing(8)
            self.open_catalog_embedded = QPushButton("在軟體內搜尋官方目錄")
            self.open_catalog_embedded.setObjectName("ghost")
            self.open_catalog_embedded.clicked.connect(self.open_catalog_embedded_page)
            filter_actions.addWidget(
                self.open_catalog_embedded, 0, Qt.AlignmentFlag.AlignRight
            )
            filter_actions.addWidget(self.open_filter, 0, Qt.AlignmentFlag.AlignRight)
            browse_layout.addLayout(filter_actions)
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
            self.player_enabled = QCheckBox()
            self.player_enabled.toggled.connect(self.toggle_player_mod)
            mod_row.addWidget(self.player_enabled)
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
            self.retry_button = QPushButton()
            self.retry_button.setObjectName("ghost")
            self.retry_button.clicked.connect(self.retry_last_operation)
            search_row.addWidget(self.retry_button)
            search_layout.addLayout(search_row)

            self.status = QLabel()
            self.status.setObjectName("preview")
            self.status.setTextFormat(Qt.TextFormat.PlainText)
            self.status.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
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
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(2, 150)
            self.table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.table.setMinimumHeight(220)
            self.table.itemSelectionChanged.connect(self.series_selection_changed)
            self.table.itemDoubleClicked.connect(lambda *_: self.load_episodes())
            search_layout.addWidget(self.table)

            actions = QHBoxLayout()
            actions.addStretch()
            self.load_episodes_button = QPushButton()
            self.load_episodes_button.setObjectName("primary")
            self.load_episodes_button.clicked.connect(self.load_episodes)
            actions.addWidget(self.load_episodes_button)
            self.open_selected_button = QPushButton()
            self.open_selected_button.setObjectName("primary")
            self.open_selected_button.clicked.connect(self.open_selected)
            actions.addWidget(self.open_selected_button)
            self.open_selected_embedded_button = QPushButton("在軟體內開啟")
            self.open_selected_embedded_button.setObjectName("ghost")
            self.open_selected_embedded_button.clicked.connect(
                self.open_selected_embedded
            )
            actions.addWidget(self.open_selected_embedded_button)
            search_layout.addLayout(actions)

            self.episode_heading = QLabel()
            self.episode_heading.setObjectName("sectionTitle")
            search_layout.addWidget(self.episode_heading)
            self.episode_context = QLabel()
            self.episode_context.setObjectName("sectionSubtitle")
            self.episode_context.setWordWrap(True)
            self.episode_context.setVisible(False)
            search_layout.addWidget(self.episode_context)
            self.episode_fallback = QFrame()
            self.episode_fallback.setObjectName("dependencySummary")
            self.episode_fallback.setProperty("dependencyState", "warning")
            fallback_layout = QVBoxLayout(self.episode_fallback)
            fallback_layout.setContentsMargins(12, 10, 12, 10)
            fallback_layout.setSpacing(8)
            self.episode_fallback_title = QLabel()
            self.episode_fallback_title.setObjectName("sectionTitle")
            fallback_layout.addWidget(self.episode_fallback_title)
            self.episode_fallback_note = QLabel()
            self.episode_fallback_note.setWordWrap(True)
            fallback_layout.addWidget(self.episode_fallback_note)
            fallback_actions = QHBoxLayout()
            self.fallback_open_series = QPushButton()
            self.fallback_open_series.setObjectName("primary")
            self.fallback_open_series.clicked.connect(self.open_selected)
            fallback_actions.addWidget(self.fallback_open_series)
            self.fallback_open_embedded = QPushButton("在軟體內開啟")
            self.fallback_open_embedded.setObjectName("ghost")
            self.fallback_open_embedded.clicked.connect(self.open_selected_embedded)
            fallback_actions.addWidget(self.fallback_open_embedded)
            fallback_actions.addStretch()
            fallback_layout.addLayout(fallback_actions)
            manual_episode_row = QHBoxLayout()
            self.manual_episode_url = QLineEdit()
            self.manual_episode_url.setMaxLength(1000)
            self.manual_episode_url.textChanged.connect(self.update_action_state)
            self.manual_episode_url.returnPressed.connect(
                self.add_manual_episode_url
            )
            manual_episode_row.addWidget(self.manual_episode_url, 1)
            self.manual_episode_add = QPushButton()
            self.manual_episode_add.setObjectName("ghost")
            self.manual_episode_add.clicked.connect(self.add_manual_episode_url)
            manual_episode_row.addWidget(self.manual_episode_add)
            fallback_layout.addLayout(manual_episode_row)
            self.episode_fallback.setVisible(False)
            search_layout.addWidget(self.episode_fallback)
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
            episode_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.episode_table.setColumnWidth(1, 150)
            self.episode_table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.episode_table.setMinimumHeight(180)
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
            self.open_episode_button.setObjectName("primary")
            self.open_episode_button.clicked.connect(self.open_selected_episode)
            episode_actions.addWidget(self.open_episode_button)
            self.next_episode_button = QPushButton()
            self.next_episode_button.setObjectName("ghost")
            self.next_episode_button.clicked.connect(self.open_next_episode)
            episode_actions.addWidget(self.next_episode_button)
            self.open_episode_embedded_button = QPushButton()
            self.open_episode_embedded_button.setObjectName("ghost")
            self.open_episode_embedded_button.clicked.connect(
                self.open_selected_episode_embedded
            )
            episode_actions.addWidget(self.open_episode_embedded_button)
            self.history_button = QPushButton()
            self.history_button.setObjectName("ghost")
            self.history_menu = QMenu(self.history_button)
            self.history_menu.aboutToShow.connect(self.populate_history_menu)
            self.history_button.setMenu(self.history_menu)
            episode_actions.addWidget(self.history_button)
            search_layout.addLayout(episode_actions)
            layout.addWidget(search_card, 1)

            offline_card = QFrame()
            offline_card.setObjectName("card")
            offline_layout = QVBoxLayout(offline_card)
            offline_layout.setContentsMargins(16, 12, 16, 12)
            offline_layout.setSpacing(8)
            self.offline_heading = QLabel()
            self.offline_heading.setObjectName("sectionTitle")
            offline_layout.addWidget(self.offline_heading)
            self.offline_boundary = QLabel()
            self.offline_boundary.setObjectName("sectionSubtitle")
            self.offline_boundary.setWordWrap(True)
            offline_layout.addWidget(self.offline_boundary)

            offline_control = QGridLayout()
            offline_control.setHorizontalSpacing(8)
            offline_control.setVerticalSpacing(8)
            self.offline_enabled = QCheckBox()
            self.offline_enabled.toggled.connect(self.toggle_offline_mod)
            offline_control.addWidget(self.offline_enabled, 0, 0, 1, 3)
            self.offline_output_label = QLabel()
            offline_control.addWidget(self.offline_output_label, 1, 0)
            self.offline_output = QLineEdit(
                str(Path(context.paths.downloads) / "AniGamer Offline")
            )
            self.offline_output.setReadOnly(True)
            self.offline_output.setMaxLength(1000)
            offline_control.addWidget(self.offline_output, 1, 1)
            self.offline_browse_button = QPushButton()
            self.offline_browse_button.clicked.connect(self.choose_offline_output)
            offline_control.addWidget(self.offline_browse_button, 1, 2)
            self.offline_prefix_label = QLabel()
            offline_control.addWidget(self.offline_prefix_label, 2, 0)
            self.offline_prefix = QLineEdit()
            self.offline_prefix.setMaxLength(48)
            offline_control.addWidget(self.offline_prefix, 2, 1)
            self.offline_suffix_label = QLabel()
            offline_control.addWidget(self.offline_suffix_label, 3, 0)
            self.offline_suffix = QLineEdit()
            self.offline_suffix.setMaxLength(48)
            offline_control.addWidget(self.offline_suffix, 3, 1)
            offline_control.setColumnStretch(1, 1)
            offline_layout.addLayout(offline_control)

            offline_actions = QHBoxLayout()
            offline_actions.addStretch()
            self.offline_save_button = QPushButton()
            self.offline_save_button.setObjectName("primary")
            self.offline_save_button.clicked.connect(self.save_offline_record)
            offline_actions.addWidget(self.offline_save_button)
            self.offline_import_button = QPushButton()
            self.offline_import_button.clicked.connect(self.start_local_media_import)
            offline_actions.addWidget(self.offline_import_button)
            self.offline_play_button = QPushButton()
            self.offline_play_button.clicked.connect(self.play_local_media)
            offline_actions.addWidget(self.offline_play_button)
            self.offline_verify_button = QPushButton()
            self.offline_verify_button.clicked.connect(self.verify_offline_archive)
            offline_actions.addWidget(self.offline_verify_button)
            self.offline_cancel_button = QPushButton()
            self.offline_cancel_button.setObjectName("ghost")
            self.offline_cancel_button.clicked.connect(self.cancel_local_media_import)
            offline_actions.addWidget(self.offline_cancel_button)
            offline_layout.addLayout(offline_actions)
            self.offline_status = QLabel()
            self.offline_status.setObjectName("preview")
            self.offline_status.setTextFormat(Qt.TextFormat.PlainText)
            self.offline_status.setWordWrap(True)
            offline_layout.addWidget(self.offline_status)
            layout.addWidget(offline_card)

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
            self.text.setdefault("player_pause", "播放 / 暫停")
            self.text.setdefault("player_stop", "停止")
            self.text.setdefault("player_volume", "音量")
            self.text.setdefault("player_previous", "上一個媒體")
            self.text.setdefault("player_next", "下一個媒體")
            self.module_names = {
                provider_id: modules[provider_id].display_name
                for provider_id in (
                    ANI_GAMER_SEARCH_PROVIDER_ID,
                    ANI_GAMER_EPISODES_PROVIDER_ID,
                    ANI_GAMER_OFFLINE_PROVIDER_ID,
                    ANI_GAMER_PLAYER_PROVIDER_ID,
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
            self.open_catalog_embedded.setText(
                self.t("open_episode_embedded")
            )
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
            self.retry_button.setText(self.t("retry"))
            if not self.status.text() or not self.busy:
                self.status.setText(self.t("initial_status"))
            self.table.setAccessibleName(self.t("title"))
            self.table.setHorizontalHeaderLabels(
                (self.t("cover"), self.t("title"), self.t("official_site"))
            )
            self.load_episodes_button.setText(self.t("load_episodes"))
            self.open_selected_button.setText(self.t("open_series"))
            self.open_selected_embedded_button.setText(
                self.t("open_episode_embedded")
            )
            self.episode_heading.setText(self.t("episode_section"))
            self.episode_fallback_title.setText(self.t("episode_fallback_title"))
            self.episode_fallback_note.setText(self.t("episode_fallback_note"))
            self.fallback_open_series.setText(self.t("episode_fallback_open"))
            self.fallback_open_embedded.setText(
                self.t("open_episode_embedded")
            )
            self.manual_episode_url.setPlaceholderText(
                self.t("manual_episode_placeholder")
            )
            self.manual_episode_url.setAccessibleName(
                self.t("manual_episode_placeholder")
            )
            self.manual_episode_add.setText(self.t("manual_episode_add"))
            self.episode_table.setAccessibleName(self.t("episode_section"))
            self.episode_table.setHorizontalHeaderLabels(
                (self.t("episode"), self.t("official_site"))
            )
            self.load_more_button.setText(self.t("load_more"))
            self.open_episode_button.setText(self.t("open_episode"))
            self.next_episode_button.setText(self.t("next_episode"))
            self.open_episode_embedded_button.setText(
                self.t("open_episode_embedded")
            )
            self.history_button.setText(self.t("history"))
            self.history_button.setToolTip(self.t("history_tooltip"))
            self.offline_heading.setText(self.t("offline_title"))
            self.offline_boundary.setText(self.t("offline_boundary"))
            self.offline_output_label.setText(self.t("offline_output"))
            self.offline_output.setAccessibleName(self.t("offline_output"))
            self.offline_browse_button.setText(self.t("offline_browse"))
            self.offline_prefix_label.setText(self.t("offline_prefix"))
            self.offline_prefix.setPlaceholderText(self.t("offline_prefix_placeholder"))
            self.offline_prefix.setAccessibleName(self.t("offline_prefix"))
            self.offline_suffix_label.setText(self.t("offline_suffix"))
            self.offline_suffix.setPlaceholderText(self.t("offline_suffix_placeholder"))
            self.offline_suffix.setAccessibleName(self.t("offline_suffix"))
            self.offline_save_button.setText(self.t("offline_save"))
            self.offline_import_button.setText(self.t("offline_import"))
            self.offline_play_button.setText(self.t("offline_play"))
            self.offline_verify_button.setText(self.t("offline_verify"))
            self.offline_cancel_button.setText(self.t("offline_cancel"))
            if not self.offline_status.text() or not self.busy:
                self.offline_status.setText(self.t("offline_initial"))
            self.refresh_availability()

        def focus_episode_section(self) -> None:
            target = (
                self.episode_fallback
                if self.episode_fallback.isVisible()
                else self.episode_heading
            )
            self.scroll_area.ensureWidgetVisible(target, 0, 16)

        def show_episode_fallback(self, visible: bool) -> None:
            self.episode_fallback.setVisible(visible)
            if visible:
                QTimer.singleShot(0, self.focus_episode_section)
                QTimer.singleShot(0, self.manual_episode_url.setFocus)

        def show_episode_context(self, title: str) -> None:
            self.episode_context.setText(title)
            self.episode_context.setVisible(bool(title))
            QTimer.singleShot(0, self.focus_episode_section)

        def handle_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            if payload.get("provider_id") in {
                "ani-gamer",
                ANI_GAMER_SEARCH_PROVIDER_ID,
                ANI_GAMER_EPISODES_PROVIDER_ID,
                ANI_GAMER_OFFLINE_PROVIDER_ID,
                ANI_GAMER_PLAYER_PROVIDER_ID,
            }:
                self.refresh_availability()

        def feature_state(self, provider_id: str) -> tuple[bool, bool]:
            try:
                statuses = {
                    status.provider_id: status for status in context.features.statuses()
                }
                status = statuses.get(provider_id)
                return status is not None, bool(status.enabled) if status else False
            except (AttributeError, KeyError, RuntimeError):
                return False, False

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
            offline_available, offline_enabled = self.feature_state(
                ANI_GAMER_OFFLINE_PROVIDER_ID
            )
            player_available, player_enabled = self.feature_state(
                ANI_GAMER_PLAYER_PROVIDER_ID
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
            self.player_enabled.setText(
                self.module_names.get(
                    ANI_GAMER_PLAYER_PROVIDER_ID, ANI_GAMER_PLAYER_PROVIDER_ID
                )
            )
            for checkbox, available, enabled in (
                (self.search_enabled, search_available, search_enabled),
                (self.episodes_enabled, episodes_available, episodes_enabled),
                (self.offline_enabled, offline_available, offline_enabled),
                (self.player_enabled, player_available, player_enabled),
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
            self.offline_enabled.setText(
                self.module_names.get(
                    ANI_GAMER_OFFLINE_PROVIDER_ID, ANI_GAMER_OFFLINE_PROVIDER_ID
                )
            )
            if not offline_available:
                self.offline_enabled.setText(self.t("offline_unavailable"))
            elif not parent_enabled:
                self.offline_enabled.setText(self.t("parent_required"))
            if not player_available:
                self.player_enabled.setText(
                    self.module_names.get(
                        ANI_GAMER_PLAYER_PROVIDER_ID, ANI_GAMER_PLAYER_PROVIDER_ID
                    )
                )
            elif not parent_enabled:
                self.player_enabled.setText(self.t("parent_required"))
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

        def toggle_offline_mod(self, enabled: bool) -> None:
            self.toggle_mod(ANI_GAMER_OFFLINE_PROVIDER_ID, enabled)

        def toggle_player_mod(self, enabled: bool) -> None:
            self.toggle_mod(ANI_GAMER_PLAYER_PROVIDER_ID, enabled)

        def dispatch_official_url(
            self,
            url: str,
            success_key: str,
            **values: object,
        ) -> bool:
            """Hand an official URL to the OS without claiming media playback."""

            accepted = open_ani_gamer_system_browser(
                url,
                lambda official_url: QDesktopServices.openUrl(
                    QUrl(official_url)
                ),
            )
            if accepted:
                self.status.setText(self.t(success_key, **values))
                return True
            self.status.setText(self.t("system_browser_open_failed", url=url))
            return False

        def open_official(self, url: str, label: str) -> None:
            if url not in {ANI_GAMER_HOME, ANI_GAMER_LIST} and not url.startswith(
                f"{ANI_GAMER_LIST}?"
            ):
                self.status.setText(self.t("catalog_rejected"))
                return
            self.dispatch_official_url(url, "catalog_opened", label=label)

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

        def open_catalog_embedded_page(self) -> None:
            self.open_embedded_url(ANI_GAMER_LIST, "AniGamer 官方目錄")

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

        def retry_last_operation(self) -> None:
            if self.busy or self.closing:
                return
            if self.retry_kind == "search" and self.retry_query:
                self.start_search(self.retry_query, self.retry_status_key)
                return
            if self.retry_kind == "episodes" and self.retry_query:
                selected = self.selected_result()
                if (
                    not self.retry_episode_append
                    and (selected is None or selected.url != self.retry_query)
                ):
                    self.status.setText(self.t("select_series"))
                    return
                self.load_episodes(append=self.retry_episode_append)
                return
            self.status.setText(self.t("retry_unavailable"))

        def browse_catalog(self, query: str) -> None:
            self.start_search(query, "catalog_running")

        def start_search(self, query: str, status_key: str) -> None:
            _available, enabled = self.provider_state(ANI_GAMER_SEARCH_PROVIDER_ID)
            if not enabled:
                self.status.setText(self.t("enable_search"))
                return
            if self.busy or self.closing:
                return
            self.retry_kind = "search"
            self.retry_query = query
            self.retry_status_key = status_key
            generation = self.begin_operation("search")
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
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
            available, enabled = self.provider_state(ANI_GAMER_EPISODES_PROVIDER_ID)
            if not parent_enabled:
                self.status.setText(self.t("enable_episodes"))
                return
            if not available:
                self.status.setText(self.t("episodes_unavailable"))
                return
            if not enabled:
                if append:
                    self.status.setText(self.t("enable_episodes"))
                    return
                answer = QMessageBox.question(
                    self,
                    self.t("episodes_enable_title"),
                    self.t("episodes_enable_prompt"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    self.status.setText(self.t("enable_episodes"))
                    return
                try:
                    set_builtin_mod_enabled(
                        context, ANI_GAMER_EPISODES_PROVIDER_ID, True
                    )
                except (
                    AttributeError,
                    KeyError,
                    OSError,
                    RuntimeError,
                    ValueError,
                ) as error:
                    self.status.setText(f"{self.t('enable_episodes')} {str(error)[:240]}")
                    self.refresh_availability()
                    return
                _available, enabled = self.provider_state(
                    ANI_GAMER_EPISODES_PROVIDER_ID
                )
                if not enabled:
                    self.status.setText(self.t("enable_episodes"))
                    self.refresh_availability()
                    return
            if self.busy or self.closing or (append and not self.episode_cursor):
                return
            self.retry_kind = "episodes"
            self.retry_query = query
            self.retry_episode_append = append
            cursor = self.episode_cursor if append else ""
            if not append:
                self.episode_query = query
                self.episode_cursor = ""
                self.episode_replace_pending = True
                self.show_episode_fallback(False)
                self.show_episode_context(selected.title if selected is not None else "")
            else:
                self.episode_replace_pending = False
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
            if self.operation in {"offline-import", "offline-verify"}:
                self.cancel_local_media_import()
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
            elif operation == "offline-import":
                self.show_offline_import_response(response, error)
            elif operation == "offline-verify":
                self.show_offline_verify_response(response, error)
            else:
                self.show_episode_results(response, error)
            self.refresh_availability()

        def show_search_results(self, response: object, error: str) -> None:
            if error:
                if ANI_GAMER_BROWSER_VERIFICATION_ERROR in error:
                    self.status.setText(self.t("search_browser_verification"))
                else:
                    self.status.setText(self.t("search_failed", error=error))
                return
            if not isinstance(response, FederatedSearchResult):
                self.status.setText(self.t("search_invalid"))
                return
            accepted = []
            seen_video_ids: set[str] = set()
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                route = classify_site_url(item.url)
                if (
                    source == ANI_GAMER_SEARCH_PROVIDER_ID
                    and route is not None
                    and route.site_family == "ani-gamer"
                    and route.resource_kind == "series"
                    and item.video_id not in seen_video_ids
                ):
                    accepted.append(item)
                    seen_video_ids.add(item.video_id)
            self.results = tuple(accepted)
            self.clear_episodes()
            self.populate_results()
            if response.failures:
                message = response.failures[0].message[:240]
                if ANI_GAMER_BROWSER_VERIFICATION_ERROR in message:
                    self.status.setText(self.t("search_browser_verification"))
                else:
                    self.status.setText(self.t("search_failed", error=message))
            elif self.results:
                self.status.setText(self.t("search_found", count=len(self.results)))
            else:
                self.status.setText(self.t("search_empty"))

        def show_episode_results(self, response: object, error: str) -> None:
            if error:
                if ANI_GAMER_BROWSER_VERIFICATION_ERROR in error:
                    self.status.setText(self.t("episodes_browser_verification"))
                    self.show_episode_fallback(True)
                else:
                    self.status.setText(self.t("episodes_failed", error=error))
                return
            if not isinstance(response, FederatedSearchResult):
                self.status.setText(self.t("episodes_invalid"))
                return
            accepted = []
            seen_video_ids: set[str] = set()
            for index, item in enumerate(response.items):
                source = response.sources[index] if index < len(response.sources) else ""
                route = classify_site_url(item.url)
                if (
                    source == ANI_GAMER_EPISODES_PROVIDER_ID
                    and route is not None
                    and route.site_family == "ani-gamer"
                    and route.resource_kind == "episode"
                    and item.video_id not in seen_video_ids
                ):
                    accepted.append(item)
                    seen_video_ids.add(item.video_id)
            if self.episode_replace_pending:
                self.episodes = tuple(accepted)
                self.episode_replace_pending = False
            else:
                known = {item.video_id for item in self.episodes}
                self.episodes = self.episodes + tuple(
                    item for item in accepted if item.video_id not in known
                )
            self.episode_cursor = dict(response.next_cursors).get(
                ANI_GAMER_EPISODES_PROVIDER_ID, ""
            )
            self.show_episode_fallback(False)
            self.populate_episodes()
            QTimer.singleShot(0, self.focus_episode_section)
            if response.failures:
                message = response.failures[0].message[:240]
                if ANI_GAMER_BROWSER_VERIFICATION_ERROR in message:
                    self.status.setText(self.t("episodes_browser_verification"))
                    self.show_episode_fallback(True)
                else:
                    self.status.setText(self.t("episodes_failed", error=message))
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
            selected = self.selected_result()
            if (
                selected is not None
                and selected.url == self.episode_query
                and not self.episode_context.text()
            ):
                self.show_episode_context(selected.title)
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
            self.episode_replace_pending = False
            self.episode_table.setRowCount(0)
            self.episode_context.clear()
            self.episode_context.setVisible(False)
            self.show_episode_fallback(False)
            self.manual_episode_url.clear()
            if self.retry_kind == "episodes":
                self.retry_kind = ""
                self.retry_query = ""
                self.retry_episode_append = False

        def add_manual_episode_url(self) -> None:
            selected = self.selected_result()
            if selected is None:
                self.status.setText(self.t("manual_episode_requires_series"))
                return
            value = "".join(self.manual_episode_url.text().split())
            item = manual_official_episode(
                value,
                self.t(
                    "manual_episode_label",
                    title=selected.title,
                    serial=parse_qs(urlsplit(value).query).get("sn", [""])[0],
                ),
            )
            if item is None:
                self.status.setText(self.t("manual_episode_invalid"))
                return
            self.episodes = (item,)
            self.episode_query = selected.url
            self.episode_cursor = ""
            self.show_episode_context(selected.title)
            self.populate_episodes()
            self.episode_table.selectRow(0)
            self.status.setText(self.t("manual_episode_added", title=item.title))

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
            self.dispatch_official_url(
                selected.url,
                "series_opened",
                title=selected.title,
            )

        def open_embedded_url(self, url: str, title: str) -> None:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or (parsed.hostname or "").casefold() != "ani.gamer.com.tw"
                or parsed.username
                or parsed.password
                or parsed.port not in {None, 443}
            ):
                self.status.setText(self.t("catalog_rejected"))
                return

            def open_system_browser() -> bool:
                return self.dispatch_official_url(
                    url,
                    "catalog_opened",
                    label=title,
                )
            if not self.embedded_web_engine_available:
                self.status.setText(self.t("embedded_webengine_unavailable"))
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(title[:120] or "AniGamer 官方頁")
            dialog.resize(960, 680)
            dialog.setMinimumSize(700, 480)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)
            status = QLabel(self.t("embedded_loading"), dialog)
            status.setTextFormat(Qt.TextFormat.PlainText)
            status.setWordWrap(True)
            status.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
            status.setMaximumHeight(56)
            layout.addWidget(status)
            actions = QHBoxLayout()
            actions.addStretch()
            fallback = QPushButton(self.t("open_official_fallback"), dialog)
            fallback.setObjectName("primary")
            fallback.setProperty(
                "controlId",
                "aniGamerEmbeddedSystemBrowserFallback",
            )
            fallback.setAccessibleName(self.t("open_official_fallback"))

            def use_system_browser() -> None:
                if open_system_browser():
                    dialog.close()

            fallback.clicked.connect(use_system_browser)
            actions.addWidget(fallback)
            close_button = QPushButton(self.t("cancel"), dialog)
            close_button.setObjectName("aniGamerEmbeddedCloseButton")
            close_button.setAccessibleName(self.t("cancel"))
            close_button.clicked.connect(dialog.close)
            actions.addWidget(close_button)
            layout.addLayout(actions)
            view = QWebEngineView(dialog)
            view.setMinimumSize(640, 420)
            view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            view.setPage(OfficialPage(view))
            configure_ani_gamer_web_view(view)
            layout.addWidget(view, 1)
            layout.setStretch(2, 1)

            def promote_fallback() -> None:
                fallback.setDefault(True)
                fallback.setFocus(Qt.FocusReason.OtherFocusReason)

            # Keep the embedded surface bounded: a verification/interstitial page
            # may never emit a useful media state, so always expose a safe fallback
            # instead of leaving a blank, apparently-frozen dialog.
            load_timeout = QTimer(dialog)
            load_timeout.setSingleShot(True)
            probe_timeout = QTimer(dialog)
            probe_timeout.setSingleShot(True)
            probe_pending = {"active": False}

            def on_load_timeout() -> None:
                status.setText(self.t("embedded_load_failed"))
                promote_fallback()

            def on_page_loaded() -> None:
                load_timeout.stop()
                status.setText(self.t("embedded_page_loaded"))
                probe_pending["active"] = True
                probe_timeout.start(5_000)

            def on_load_failed() -> None:
                load_timeout.stop()
                probe_timeout.stop()
                probe_pending["active"] = False
                status.setText(self.t("embedded_load_failed"))
                promote_fallback()

            def on_probe_timeout() -> None:
                probe_pending["active"] = False
                status.setText(self.t("embedded_capability_unknown"))
                promote_fallback()

            def on_capability(capability: WebEngineMediaCapability) -> None:
                if not probe_pending["active"]:
                    return
                probe_pending["active"] = False
                probe_timeout.stop()
                status_key = {
                    WebEngineMediaCapability.SUPPORTED: (
                        "embedded_capability_supported"
                    ),
                    WebEngineMediaCapability.UNSUPPORTED: (
                        "embedded_capability_unsupported"
                    ),
                    WebEngineMediaCapability.UNKNOWN: (
                        "embedded_capability_unknown"
                    ),
                }[capability]
                status.setText(self.t(status_key))
                if capability is not WebEngineMediaCapability.SUPPORTED:
                    promote_fallback()

            def on_renderer_terminated() -> None:
                load_timeout.stop()
                probe_timeout.stop()
                probe_pending["active"] = False
                status.setText(self.t("embedded_renderer_terminated"))
                promote_fallback()

            load_timeout.timeout.connect(on_load_timeout)
            probe_timeout.timeout.connect(on_probe_timeout)
            wire_ani_gamer_web_view_diagnostics(
                view,
                on_page_loaded=on_page_loaded,
                on_load_failed=on_load_failed,
                on_capability=on_capability,
                on_renderer_terminated=on_renderer_terminated,
            )
            view.setUrl(QUrl(url))
            load_timeout.start(15_000)
            self._browser_dialogs.append(dialog)
            dialog.finished.connect(
                lambda _result, current=dialog: self._browser_dialogs.remove(current)
                if current in self._browser_dialogs
                else None
            )
            dialog.show()

        def play_local_media(self) -> None:
            try:
                player_enabled = context.features.is_enabled(
                    ANI_GAMER_PLAYER_PROVIDER_ID
                )
            except (AttributeError, KeyError, RuntimeError):
                player_enabled = False
            if not player_enabled:
                self.offline_status.setText(self.t("parent_required"))
                return
            if (
                QMediaPlayer is None
                or QAudioOutput is None
                or QMediaFormat is None
                or QVideoWidget is None
            ):
                self.offline_status.setText(self.t("offline_media_missing"))
                return
            runtime_support = detect_qt_local_media_runtime_support(QMediaFormat)
            filters: list[str] = []
            if runtime_support.supported:
                filters.append(
                    self.t(
                        "offline_play_supported_filter",
                        patterns=" ".join(
                            f"*{suffix}"
                            for suffix in sorted(runtime_support.supported)
                        ),
                    )
                )
            if runtime_support.unknown:
                filters.append(
                    self.t(
                        "offline_play_unknown_filter",
                        patterns=" ".join(
                            f"*{suffix}"
                            for suffix in sorted(runtime_support.unknown)
                        ),
                    )
                )
            filenames, _filter = QFileDialog.getOpenFileNames(
                self,
                self.t("offline_play"),
                str(Path(context.paths.downloads)),
                ";;".join(filters),
            )
            if not filenames:
                return
            try:
                queue = validate_local_media_selection(
                    tuple(Path(filename) for filename in filenames)
                )
            except ValueError:
                self.offline_status.setText(self.t("offline_select_files"))
                return
            playback_capability = classify_local_media_playback_selection(
                queue,
                runtime_support,
            )
            if playback_capability is LocalMediaPlaybackCapability.UNSUPPORTED:
                names = ", ".join(
                    safe_local_media_display_name(path, limit=80) for path in queue
                )[:160]
                self.offline_status.setText(
                    self.t("offline_media_runtime_unsupported", path=names)
                )
                return
            self.stop_local_media()
            dialog = QDialog(self)
            dialog.setWindowTitle(safe_local_media_display_name(queue[0]))
            dialog.resize(960, 640)
            layout = QVBoxLayout(dialog)
            video = QVideoWidget(dialog)
            layout.addWidget(video, 1)
            controls = QHBoxLayout()
            pause_button = QPushButton(self.t("player_pause"), dialog)
            controls.addWidget(pause_button)
            stop_button = QPushButton(self.t("player_stop"), dialog)
            controls.addWidget(stop_button)
            previous_button = QPushButton("◀", dialog)
            previous_button.setToolTip(self.t("player_previous"))
            previous_button.setAccessibleName(self.t("player_previous"))
            controls.addWidget(previous_button)
            next_button = QPushButton("▶", dialog)
            next_button.setToolTip(self.t("player_next"))
            next_button.setAccessibleName(self.t("player_next"))
            controls.addWidget(next_button)
            controls.addWidget(QLabel(self.t("player_volume"), dialog))
            volume_slider = QSlider(Qt.Orientation.Horizontal, dialog)
            volume_slider.setRange(0, 100)
            volume_slider.setValue(70)
            controls.addWidget(volume_slider, 1)
            close_button = QPushButton(self.t("cancel"), dialog)
            controls.addWidget(close_button)
            layout.addLayout(controls)
            player = QMediaPlayer(dialog)
            audio = QAudioOutput(dialog)
            audio.setVolume(0.7)
            player.setAudioOutput(audio)
            player.setVideoOutput(video)
            # Stop playback without closing the player window; closing remains an
            # explicit user action and mirrors normal desktop-player behaviour.
            stop_button.clicked.connect(player.stop)
            pause_button.clicked.connect(
                lambda: (
                    player.pause()
                    if player.playbackState()
                    == QMediaPlayer.PlaybackState.PlayingState
                    else player.play()
                )
            )
            close_button.clicked.connect(dialog.close)
            volume_slider.valueChanged.connect(lambda value: audio.setVolume(value / 100))
            dialog.finished.connect(self.stop_local_media)
            self.local_media_dialog = dialog
            self.local_media_player = player
            self.local_media_queue = queue
            self.local_media_index = 0
            reported_error: dict[str, object] = {"key": None}
            active_source: dict[str, object] = {
                "url": None,
                "capability": LocalMediaPlaybackCapability.UNKNOWN,
            }

            def current_source_is_active() -> bool:
                source = active_source["url"]
                return (
                    source is not None
                    and 0 <= self.local_media_index < len(self.local_media_queue)
                    and player.source() == source
                )

            def report_playback_error(code: str) -> None:
                if not current_source_is_active():
                    return
                source = active_source["url"]
                key = (source, code)
                if reported_error["key"] == key:
                    return
                reported_error["key"] = key
                item = self.local_media_queue[self.local_media_index]
                self.offline_status.setText(
                    self.t(
                        "offline_media_error",
                        path=safe_local_media_display_name(item),
                        code=code,
                    )
                )

            def handle_player_error(error: object, *_details: object) -> None:
                if error != player.error() or not current_source_is_active():
                    return
                report_playback_error(
                    classify_local_media_player_error(getattr(error, "name", ""))
                )

            player.errorOccurred.connect(handle_player_error)

            def load_queue_item(index: int) -> None:
                if not 0 <= index < len(self.local_media_queue):
                    return
                self.local_media_index = index
                item = self.local_media_queue[index]
                item_name = safe_local_media_display_name(item)
                reported_error["key"] = None
                dialog.setWindowTitle(item_name)
                previous_button.setEnabled(index > 0)
                next_button.setEnabled(index + 1 < len(self.local_media_queue))
                item_capability = classify_local_media_playback_selection(
                    (item,),
                    runtime_support,
                )
                source = QUrl.fromLocalFile(str(item))
                active_source["url"] = source
                active_source["capability"] = item_capability
                self.offline_status.setText(
                    self.t(
                        local_media_playback_status_key(item_capability, "LoadingState"),
                        path=item_name,
                    )
                )
                player.setSource(source)
                player.play()

            previous_button.clicked.connect(
                lambda: load_queue_item(self.local_media_index - 1)
            )
            next_button.clicked.connect(
                lambda: load_queue_item(self.local_media_index + 1)
            )

            def handle_playback_state(state: object) -> None:
                if (
                    getattr(state, "name", "") != "PlayingState"
                    or not current_source_is_active()
                ):
                    return
                item = self.local_media_queue[self.local_media_index]
                capability = active_source["capability"]
                if not isinstance(capability, LocalMediaPlaybackCapability):
                    capability = LocalMediaPlaybackCapability.UNKNOWN
                self.offline_status.setText(
                    self.t(
                        local_media_playback_status_key(capability, "PlayingState"),
                        path=safe_local_media_display_name(item),
                    )
                )

            player.playbackStateChanged.connect(handle_playback_state)

            def handle_media_status(status: object) -> None:
                if status != player.mediaStatus() or not current_source_is_active():
                    return
                if (
                    status == QMediaPlayer.MediaStatus.EndOfMedia
                    and self.local_media_index + 1 < len(self.local_media_queue)
                ):
                    load_queue_item(self.local_media_index + 1)
                    return
                if status == QMediaPlayer.MediaStatus.InvalidMedia:
                    error = player.error()
                    report_playback_error(
                        classify_local_media_player_error(
                            getattr(error, "name", ""),
                            invalid_media=True,
                        )
                    )

            player.mediaStatusChanged.connect(handle_media_status)
            dialog.show()
            load_queue_item(0)

        def stop_local_media(self) -> None:
            player = self.local_media_player
            dialog = self.local_media_dialog
            self.local_media_player = None
            self.local_media_dialog = None
            self.local_media_queue = ()
            self.local_media_index = -1
            if player is not None:
                player.stop()
                player.setSource(QUrl())
            if dialog is not None and dialog.isVisible():
                dialog.close()

        def open_selected_embedded(self) -> None:
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
            self.open_embedded_url(selected.url, selected.title)

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
            if self.dispatch_official_url(
                selected.url,
                "episode_opened",
                title=selected.title,
            ):
                self.record_episode_history(selected)

        def open_next_episode(self) -> None:
            row = self.episode_table.currentRow()
            next_row = row + 1
            if row < 0 or next_row >= len(self.episodes):
                self.status.setText(self.t("next_episode_unavailable"))
                return
            self.episode_table.selectRow(next_row)
            self.open_selected_episode()

        def open_selected_episode_embedded(self) -> None:
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
            self.record_episode_history(selected)
            self.open_embedded_url(selected.url, selected.title)

        def record_episode_history(self, episode: DiscoveryItemV1) -> None:
            series = self.selected_result()
            if series is None:
                return
            try:
                record_history(self.history_file, series, episode)
            except (OSError, TypeError, ValueError):
                # History is an optional local convenience and must never block
                # opening the official page.
                return

        def populate_history_menu(self) -> None:
            self.history_menu.clear()
            entries = load_history(self.history_file)
            if not entries:
                action = self.history_menu.addAction(self.t("history_empty"))
                action.setEnabled(False)
                return
            for entry in entries[:40]:
                label = f"{entry.series_title} — {entry.episode_title}"
                action = QAction(label[:180], self.history_menu)
                action.setToolTip(entry.url)
                action.triggered.connect(
                    lambda _checked=False, current=entry: self.open_history_entry(
                        current
                    )
                )
                self.history_menu.addAction(action)

            self.history_menu.addSeparator()
            clear_action = QAction(self.t("history_clear"), self.history_menu)
            clear_action.triggered.connect(self.clear_history_with_confirmation)
            self.history_menu.addAction(clear_action)
            export_action = QAction(self.t("history_export"), self.history_menu)
            export_action.triggered.connect(self.export_history_to_file)
            self.history_menu.addAction(export_action)

        def clear_history_with_confirmation(self) -> None:
            answer = QMessageBox.question(
                self,
                self.t("history_clear_title"),
                self.t("history_clear_prompt"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                clear_history(self.history_file)
            except (OSError, ValueError):
                self.status.setText(self.t("history_clear_failed"))
                return
            self.status.setText(self.t("history_cleared"))

        def export_history_to_file(self) -> None:
            filename, _filter = QFileDialog.getSaveFileName(
                self,
                self.t("history_export"),
                str(Path(context.paths.data) / "ani-gamer-history.json"),
                "JSON (*.json)",
            )
            if not filename:
                return
            try:
                export_history(self.history_file, Path(filename))
            except (OSError, ValueError):
                self.status.setText(self.t("history_export_failed"))
                return
            self.status.setText(self.t("history_exported"))

        def open_history_entry(self, entry: AniGamerHistoryEntry) -> None:
            route = classify_site_url(entry.url)
            if (
                route is None
                or route.site_family != "ani-gamer"
                or route.resource_kind != "episode"
            ):
                self.status.setText(self.t("catalog_rejected"))
                return
            self.dispatch_official_url(
                entry.url,
                "episode_opened",
                title=entry.episode_title,
            )

        def choose_offline_output(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self,
                self.t("offline_output"),
                self.offline_output.text(),
            )
            if selected:
                self.offline_output.setText(str(Path(selected)))

        def selected_cover_png(self) -> bytes | None:
            selected = self.selected_result()
            if selected is None or not selected.thumbnail_url:
                return None
            pixmap = self.thumbnail_loader.cache.get(selected.thumbnail_url)
            if pixmap is None or pixmap.isNull():
                return None
            buffer = QBuffer()
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
                return None
            if not pixmap.save(buffer, "PNG"):
                return None
            return bytes(buffer.data())

        def create_selected_archive(self) -> object:
            _available, enabled = self.feature_state(ANI_GAMER_OFFLINE_PROVIDER_ID)
            if not enabled:
                raise RuntimeError(self.t("offline_disabled"))
            series = self.selected_result()
            episode = self.selected_episode()
            if series is None:
                raise ValueError(self.t("select_series"))
            if episode is None:
                raise ValueError(self.t("select_episode"))
            output = Path(self.offline_output.text()).expanduser()
            if not str(output).strip():
                raise ValueError(self.t("offline_output"))
            archive = create_episode_archive(
                output,
                series,
                episode,
                cover_png=self.selected_cover_png(),
                name_prefix=self.offline_prefix.text(),
                name_suffix=self.offline_suffix.text(),
            )
            self.offline_archive_root = archive.root
            return archive

        def save_offline_record(self) -> None:
            if self.busy:
                return
            try:
                archive = self.create_selected_archive()
                episode = self.selected_episode()
                title = episode.title if episode is not None else ""
                self.offline_status.setText(
                    self.t("offline_saved", title=title, path=str(archive.root))
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                self.offline_status.setText(
                    self.t("offline_failed", error=str(error)[:300])
                )
            self.update_action_state()

        def start_local_media_import(self) -> None:
            if self.busy:
                return
            try:
                archive = self.create_selected_archive()
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                self.offline_status.setText(
                    self.t("offline_failed", error=str(error)[:300])
                )
                return
            filenames, _filter = QFileDialog.getOpenFileNames(
                self,
                self.t("offline_import"),
                str(Path(context.paths.downloads)),
                "Media and subtitles (*.mp4 *.mkv *.webm *.mov *.m4v *.avi *.ts "
                "*.mpeg *.mpg *.mp3 *.m4a *.flac *.wav *.opus *.ogg *.ass *.srt "
                "*.ssa *.sub *.ttml *.vtt *.xml)",
            )
            if not filenames:
                return
            selected = tuple(Path(filename) for filename in filenames)
            media = tuple(
                path
                for path in selected
                if path.suffix.casefold() in ALLOWED_LOCAL_MEDIA_SUFFIXES
            )
            subtitles = tuple(
                path
                for path in selected
                if path.suffix.casefold() in ALLOWED_LOCAL_SUBTITLE_SUFFIXES
            )
            if len(media) > 1 or not media and not subtitles:
                self.offline_status.setText(
                    self.t(
                        "offline_failed",
                        error=self.t("offline_select_files"),
                    )
                )
                return
            self.offline_cancel_event.clear()
            generation = self.begin_operation("offline-import")
            self.offline_status.setText(self.t("offline_importing"))

            def worker() -> None:
                try:
                    result = archive
                    if media:
                        result = import_local_media(
                            archive.root,
                            media[0],
                            cancelled=self.offline_cancel_event.is_set,
                        )
                    if subtitles:
                        result = import_local_subtitles(
                            archive.root,
                            subtitles,
                            cancelled=self.offline_cancel_event.is_set,
                        )
                    error = ""
                except OfflineImportCancelled:
                    result = None
                    error = "__cancelled__"
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit(
                        "offline-import", generation, result, error
                    )

            threading.Thread(
                target=worker,
                name="ani-gamer-local-media-import",
                daemon=True,
            ).start()

        def cancel_local_media_import(self) -> None:
            if self.busy and self.operation in {"offline-import", "offline-verify"}:
                self.offline_cancel_event.set()
                self.offline_cancel_button.setEnabled(False)

        def show_offline_import_response(self, response: object, error: str) -> None:
            if error == "__cancelled__":
                self.offline_status.setText(self.t("offline_cancelled"))
                return
            if error:
                self.offline_status.setText(
                    self.t("offline_failed", error=error)
                )
                return
            local_media = getattr(response, "local_media", None)
            subtitles = getattr(response, "local_subtitles", ())
            paths = [str(local_media)] if isinstance(local_media, Path) else []
            if isinstance(subtitles, tuple):
                paths.extend(str(path) for path in subtitles if isinstance(path, Path))
            if not paths:
                self.offline_status.setText(
                    self.t("offline_failed", error="invalid local media result")
                )
                return
            self.offline_status.setText(
                self.t("offline_imported", path="; ".join(paths))
            )

        def verify_offline_archive(self) -> None:
            if self.busy:
                return
            try:
                archive = self.create_selected_archive()
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                self.offline_status.setText(
                    self.t("offline_failed", error=str(error)[:300])
                )
                return
            self.offline_cancel_event.clear()
            generation = self.begin_operation("offline-verify")
            self.offline_status.setText(self.t("offline_verifying"))

            def worker() -> None:
                try:
                    result = verify_episode_archive(
                        archive.root,
                        cancelled=self.offline_cancel_event.is_set,
                    )
                    error = ""
                except OfflineImportCancelled:
                    result = None
                    error = "__cancelled__"
                except Exception as caught:
                    result = None
                    error = str(caught)[:300] or type(caught).__name__
                if not self.closing:
                    self.bridge.finished.emit(
                        "offline-verify", generation, result, error
                    )

            threading.Thread(
                target=worker,
                name="ani-gamer-offline-verify",
                daemon=True,
            ).start()

        def show_offline_verify_response(self, response: object, error: str) -> None:
            if error == "__cancelled__":
                self.offline_status.setText(self.t("offline_cancelled"))
                return
            if error:
                self.offline_status.setText(
                    self.t("offline_failed", error=error)
                )
                return
            if not isinstance(response, AniGamerArchiveVerification):
                self.offline_status.setText(
                    self.t("offline_failed", error="invalid verification result")
                )
                return
            if (
                response.media_state == "not-linked"
                and response.subtitle_state == "not-linked"
            ):
                self.offline_status.setText(self.t("offline_verify_no_media"))
            elif response.valid:
                verified_paths = [
                    str(path)
                    for path in (
                        [response.media_path]
                        if response.media_path is not None
                        else []
                    )
                ]
                verified_paths.extend(str(path) for path in response.subtitle_paths)
                self.offline_status.setText(
                    self.t("offline_verified", path="; ".join(verified_paths))
                )
            else:
                states = [
                    state
                    for state in (response.media_state, response.subtitle_state)
                    if state not in {"ok", "not-linked"}
                ]
                self.offline_status.setText(
                    self.t(
                        "offline_verify_invalid",
                        state="/".join(states) or response.media_state,
                    )
                )

        def update_action_state(self) -> None:
            try:
                parent_enabled = context.features.is_enabled("ani-gamer")
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
            _search_available, search_enabled = self.provider_state(
                ANI_GAMER_SEARCH_PROVIDER_ID
            )
            episodes_available, episodes_enabled = self.provider_state(
                ANI_GAMER_EPISODES_PROVIDER_ID
            )
            _offline_available, offline_enabled = self.feature_state(
                ANI_GAMER_OFFLINE_PROVIDER_ID
            )
            _player_available, player_enabled = self.feature_state(
                ANI_GAMER_PLAYER_PROVIDER_ID
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
            retry_available = bool(self.retry_kind and self.retry_query)
            if self.retry_kind == "episodes":
                _retry_available, retry_provider_enabled = self.provider_state(
                    ANI_GAMER_EPISODES_PROVIDER_ID
                )
                retry_available = retry_available and retry_provider_enabled
            else:
                _retry_available, retry_provider_enabled = self.provider_state(
                    ANI_GAMER_SEARCH_PROVIDER_ID
                )
                retry_available = retry_available and retry_provider_enabled
            self.retry_button.setEnabled(
                parent_enabled and retry_available and not self.busy
            )
            self.open_filter.setEnabled(
                parent_enabled and search_enabled and not self.busy
            )
            self.load_episodes_button.setText(
                self.t(
                    "load_episodes"
                    if episodes_enabled
                    else "enable_and_load_episodes"
                )
            )
            self.load_episodes_button.setToolTip(
                "" if episodes_enabled else self.t("enable_episodes")
            )
            self.load_episodes_button.setEnabled(
                parent_enabled
                and episodes_available
                and selected is not None
                and not self.busy
            )
            self.open_selected_button.setEnabled(selected is not None and not self.busy)
            self.open_selected_embedded_button.setEnabled(
                parent_enabled and player_enabled and selected is not None and not self.busy
            )
            self.load_more_button.setEnabled(
                parent_enabled
                and episodes_enabled
                and bool(self.episode_cursor)
                and not self.busy
            )
            self.open_episode_button.setEnabled(
                selected_episode is not None and not self.busy
            )
            selected_row = self.episode_table.currentRow()
            self.next_episode_button.setEnabled(
                selected_episode is not None
                and selected_row + 1 < len(self.episodes)
                and not self.busy
            )
            self.open_episode_embedded_button.setEnabled(
                parent_enabled
                and player_enabled
                and selected_episode is not None
                and not self.busy
            )
            self.history_button.setEnabled(parent_enabled and not self.busy)
            manual_ready = (
                parent_enabled
                and episodes_enabled
                and selected is not None
                and not self.busy
            )
            self.manual_episode_url.setEnabled(manual_ready)
            self.manual_episode_add.setEnabled(
                manual_ready and bool(self.manual_episode_url.text().strip())
            )
            offline_ready = (
                parent_enabled
                and offline_enabled
                and selected is not None
                and selected_episode is not None
            )
            self.offline_output.setEnabled(not self.busy)
            self.offline_browse_button.setEnabled(not self.busy)
            self.offline_prefix.setEnabled(not self.busy)
            self.offline_suffix.setEnabled(not self.busy)
            self.offline_save_button.setEnabled(offline_ready and not self.busy)
            self.offline_import_button.setEnabled(offline_ready and not self.busy)
            self.offline_play_button.setEnabled(
                parent_enabled and player_enabled and not self.busy
            )
            self.offline_verify_button.setEnabled(offline_ready and not self.busy)
            self.offline_cancel_button.setEnabled(
                self.busy
                and self.operation in {"offline-import", "offline-verify"}
                and not self.offline_cancel_event.is_set()
            )

        def shutdown(self) -> None:
            if self.closing:
                return
            self.closing = True
            self.offline_cancel_event.set()
            self.generation += 1
            self.thumbnail_loader.shutdown()
            self.stop_local_media()
            if self.events is not None:
                self.events.unsubscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.unsubscribe("ui.language.changed", self.apply_language)

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return AniGamerWorkspace()
