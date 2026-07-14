"""Read-only catalog of candidate website MODs that are not installed yet."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from urllib.parse import SplitResult, parse_qs, urlencode, urlsplit, urlunsplit


ANI_GAMER_HOME = "https://ani.gamer.com.tw/"
FACEBOOK_HOME = "https://www.facebook.com/"
FACEBOOK_EXPORT_HELP = "https://www.facebook.com/help/www/466076673571942"
INSTAGRAM_HOME = "https://www.instagram.com/"
INSTAGRAM_EXPORT_HELP = (
    "https://www.facebook.com/help/instagram/181231772500920"
)
MEGA_HOME = "https://mega.io/"
THREADS_HOME = "https://www.threads.com/"
THREADS_EXPORT_HELP = (
    "https://www.facebook.com/help/instagram/259803026523198"
)


def _official_https_parts(
    value: str,
    *,
    home: str,
    hosts: frozenset[str],
) -> SplitResult | None:
    raw = value.strip() or home
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() not in hosts
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        return None
    return parsed


def _single_ascii_digits_query(
    query_text: str,
    *,
    key: str,
    maximum_length: int,
) -> str | None:
    try:
        query = parse_qs(
            query_text,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError:
        return None
    if set(query) != {key} or len(query[key]) != 1:
        return None
    value = query[key][0]
    if not value.isascii() or not value.isdigit() or not 1 <= len(value) <= maximum_length:
        return None
    return value


def validated_ani_gamer_url(value: str) -> str | None:
    """Accept only the official homepage or a canonical episode page."""

    parsed = _official_https_parts(
        value,
        home=ANI_GAMER_HOME,
        hosts=frozenset({"ani.gamer.com.tw"}),
    )
    if parsed is None:
        return None
    if parsed.path in {"", "/"} and not parsed.query:
        return ANI_GAMER_HOME
    if parsed.path != "/animeVideo.php":
        return None
    serial = _single_ascii_digits_query(
        parsed.query,
        key="sn",
        maximum_length=10,
    )
    if serial is None:
        return None
    return urlunsplit(
        ("https", "ani.gamer.com.tw", "/animeVideo.php", urlencode({"sn": serial}), "")
    )


def validated_facebook_url(value: str) -> str | None:
    """Accept a bounded set of canonical Facebook video page forms."""

    parsed = _official_https_parts(
        value,
        home=FACEBOOK_HOME,
        hosts=frozenset({"facebook.com", "www.facebook.com", "m.facebook.com"}),
    )
    if parsed is None:
        return None
    if parsed.path in {"", "/"} and not parsed.query:
        return FACEBOOK_HOME
    if parsed.path in {"/watch", "/watch/", "/video.php"}:
        video_id = _single_ascii_digits_query(
            parsed.query,
            key="v",
            maximum_length=32,
        )
        if video_id is None:
            return None
        canonical_path = "/watch/" if parsed.path.startswith("/watch") else "/video.php"
        return urlunsplit(
            (
                "https",
                "www.facebook.com",
                canonical_path,
                urlencode({"v": video_id}),
                "",
            )
        )
    if parsed.query:
        return None
    reel = re.fullmatch(r"/reel/([0-9]{1,32})/?", parsed.path)
    if reel:
        return f"https://www.facebook.com/reel/{reel.group(1)}/"
    page_video = re.fullmatch(
        r"/([A-Za-z0-9._-]{1,100})/videos/([0-9]{1,32})/?",
        parsed.path,
    )
    if page_video:
        return (
            "https://www.facebook.com/"
            f"{page_video.group(1)}/videos/{page_video.group(2)}/"
        )
    return None


def validated_instagram_url(value: str) -> str | None:
    """Accept only canonical public Instagram post and video page forms."""

    parsed = _official_https_parts(
        value,
        home=INSTAGRAM_HOME,
        hosts=frozenset({"instagram.com", "www.instagram.com"}),
    )
    if parsed is None:
        return None
    if parsed.path in {"", "/"} and not parsed.query:
        return INSTAGRAM_HOME
    if parsed.query:
        return None
    media = re.fullmatch(
        r"/(p|reel|tv)/([A-Za-z0-9_-]{5,32})/?",
        parsed.path,
    )
    if media is None:
        return None
    return f"https://www.instagram.com/{media.group(1)}/{media.group(2)}/"


def validated_threads_url(value: str) -> str | None:
    """Accept only canonical Threads post pages on current or migrated hosts."""

    parsed = _official_https_parts(
        value,
        home=THREADS_HOME,
        hosts=frozenset(
            {"threads.com", "www.threads.com", "threads.net", "www.threads.net"}
        ),
    )
    if parsed is None:
        return None
    if parsed.path in {"", "/"} and not parsed.query:
        return THREADS_HOME
    if parsed.query:
        return None
    post = re.fullmatch(
        r"/@([A-Za-z0-9._]{1,30})/post/([A-Za-z0-9_-]{5,64})/?",
        parsed.path,
    )
    if post is None:
        return None
    return f"https://www.threads.com/@{post.group(1)}/post/{post.group(2)}/"


def validated_mega_url(value: str) -> str | None:
    """Accept the official homepage or a bounded modern public-share URL."""

    raw = value.strip() or MEGA_HOME
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme.casefold() != "https"
        or host not in {"mega.io", "www.mega.io", "mega.nz", "www.mega.nz"}
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
    ):
        return None
    if parsed.path in {"", "/"} and not parsed.fragment:
        return MEGA_HOME
    if host not in {"mega.nz", "www.mega.nz"}:
        return None
    share = re.fullmatch(r"/(file|folder)/([A-Za-z0-9_-]{6,64})/?", parsed.path)
    if share is None or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", parsed.fragment):
        return None
    return f"https://mega.nz/{share.group(1)}/{share.group(2)}#{parsed.fragment}"


@dataclass(frozen=True, slots=True)
class SiteModCandidate:
    provider_id: str
    display_name: str
    stage: str
    planned_capabilities: str
    safety_boundary: str


@dataclass(frozen=True, slots=True)
class OfficialBridgeSpec:
    bridge_id: str
    display_name: str
    placeholder: str
    validator: Callable[[str], str | None]
    help_url: str = ""


OFFICIAL_BRIDGES = (
    OfficialBridgeSpec(
        "ani-gamer",
        "動畫瘋",
        "https://ani.gamer.com.tw/animeVideo.php?sn=...（留空開首頁）",
        validated_ani_gamer_url,
    ),
    OfficialBridgeSpec(
        "facebook",
        "Facebook",
        "貼上官方 watch、reel 或頁面影片網址（留空開首頁）",
        validated_facebook_url,
        FACEBOOK_EXPORT_HELP,
    ),
    OfficialBridgeSpec(
        "instagram",
        "Instagram",
        "貼上官方貼文、Reel 或 IGTV 網址（留空開首頁）",
        validated_instagram_url,
        INSTAGRAM_EXPORT_HELP,
    ),
    OfficialBridgeSpec(
        "threads",
        "Threads",
        "貼上 threads.com 官方貼文網址（留空開首頁）",
        validated_threads_url,
        THREADS_EXPORT_HELP,
    ),
    OfficialBridgeSpec(
        "mega",
        "MEGA",
        "貼上 mega.nz 官方公開檔案或資料夾分享連結（留空開首頁）",
        validated_mega_url,
    ),
)


SITE_MOD_CANDIDATES = (
    SiteModCandidate(
        "ani-gamer",
        "巴哈姆特動畫瘋",
        "官方播放限定",
        "驗證官方動畫頁網址並交由系統瀏覽器播放",
        "不擷取影片或彈幕、不接收 Cookie；不規避廣告、地區、IP 或串流限制",
    ),
    SiteModCandidate(
        "facebook",
        "Facebook",
        "官方工具限定",
        "驗證官方影片頁並提供官方資料匯出說明",
        "不啟用自動擷取器、不接收帳密或 Cookie；不繞過私人內容限制",
    ),
    SiteModCandidate(
        "instagram",
        "Instagram",
        "官方工具限定",
        "驗證官方貼文或 Reel 並提供官方資料匯出說明",
        "不啟用自動擷取器、不匯入登入工作階段；限時與私人內容不處理",
    ),
    SiteModCandidate(
        "threads",
        "Threads",
        "官方工具限定",
        "驗證官方貼文頁並提供官方 Threads 資料匯出說明",
        "沒有專用擷取器；不自動收集貼文、不匯入登入資料或處理私人內容",
    ),
    SiteModCandidate(
        "mega",
        "MEGA",
        "官方 SDK 評估",
        "驗證官方公開分享連結；規劃以 MEGA SDK 或 MEGAcmd 建立獨立下載 MOD",
        "不接收帳密或工作階段、不繞過傳輸配額或權限；驗證完成前不宣稱下載支援",
    ),
)


def create_site_mod_catalog_panel(parent: object = None) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QDesktopServices
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from trusted_ui.theme import COLORS

    panel = QWidget(parent)
    page = QVBoxLayout(panel)
    page.setContentsMargins(4, 8, 4, 4)
    page.setSpacing(10)

    intro = QLabel(
        "這裡只列出未安裝的網站 MOD 備選方案。完成相容性、授權邊界與"
        "獨立測試前，不會啟用、不會連線，也不會出現在預設工作區。"
    )
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary = QLabel(f"已登記 {len(SITE_MOD_CANDIDATES)} 個候選網站 MOD")
    summary.setObjectName("dependencySummary")
    summary.setProperty("dependencyState", "ready")
    page.addWidget(summary)

    table = QTableWidget(len(SITE_MOD_CANDIDATES), 4)
    table.setHorizontalHeaderLabels(("候選 MOD", "階段", "預定能力", "安全邊界"))
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setStretchLastSection(True)
    table.setColumnWidth(0, 150)
    table.setColumnWidth(1, 105)
    table.setColumnWidth(2, 230)

    for row, candidate in enumerate(SITE_MOD_CANDIDATES):
        stage = QTableWidgetItem(candidate.stage)
        stage.setForeground(QColor(COLORS["muted"]))
        values = (
            QTableWidgetItem(
                f"{candidate.display_name}\n{candidate.provider_id}"
            ),
            stage,
            QTableWidgetItem(candidate.planned_capabilities),
            QTableWidgetItem(candidate.safety_boundary),
        )
        for column, item in enumerate(values):
            item.setToolTip(item.text())
            table.setItem(row, column, item)
        table.setRowHeight(row, 58)

    page.addWidget(table, 1)

    official = QFrame()
    official.setObjectName("card")
    official_layout = QVBoxLayout(official)
    official_layout.setContentsMargins(14, 12, 14, 12)
    official_title = QLabel("官方網站入口")
    official_title.setObjectName("fieldLabel")
    official_layout.addWidget(official_title)
    official_note = QLabel(
        "只驗證網址並交由系統瀏覽器開啟；不解析串流、不匯入登入資料，"
        "也不在背景連線。"
    )
    official_note.setObjectName("sectionSubtitle")
    official_note.setWordWrap(True)
    official_layout.addWidget(official_note)
    official_controls = QHBoxLayout()
    official_site = QComboBox()
    official_site.setObjectName("officialSiteBridgeSelect")
    for bridge in OFFICIAL_BRIDGES:
        official_site.addItem(bridge.display_name, bridge.bridge_id)
    official_url = QLineEdit()
    official_url.setObjectName("officialSiteBridgeUrl")
    open_official = QPushButton("開啟官方頁面")
    open_official.setObjectName("officialSiteBridgeOpen")
    open_help = QPushButton("官方資料匯出說明")
    open_help.setObjectName("officialSiteBridgeHelp")
    official_controls.addWidget(official_site)
    official_controls.addWidget(official_url, 1)
    official_controls.addWidget(open_official)
    official_controls.addWidget(open_help)
    official_layout.addLayout(official_controls)
    official_status = QLabel()
    official_status.setObjectName("officialSiteBridgeStatus")
    official_layout.addWidget(official_status)
    page.addWidget(official)

    def selected_bridge() -> OfficialBridgeSpec:
        return OFFICIAL_BRIDGES[max(0, official_site.currentIndex())]

    def update_bridge(_index: int) -> None:
        bridge = selected_bridge()
        official_url.clear()
        official_url.setPlaceholderText(bridge.placeholder)
        open_help.setVisible(bool(bridge.help_url))
        official_status.setText(
            f"{bridge.display_name}：等待使用者操作；不會在背景連線。"
        )

    def open_official_site() -> None:
        from PySide6.QtCore import QUrl

        bridge = selected_bridge()
        target = bridge.validator(official_url.text())
        if target is None:
            official_status.setText(
                f"網址不是允許的「{bridge.display_name}」官方媒體頁。"
            )
            return
        opened = QDesktopServices.openUrl(QUrl(target))
        official_status.setText(
            f"已交由系統瀏覽器開啟「{bridge.display_name}」官方頁面。"
            if opened
            else "系統無法開啟瀏覽器。"
        )

    def open_official_help() -> None:
        from PySide6.QtCore import QUrl

        bridge = selected_bridge()
        if not bridge.help_url:
            return
        opened = QDesktopServices.openUrl(QUrl(bridge.help_url))
        official_status.setText(
            f"已開啟「{bridge.display_name}」官方資料匯出說明。"
            if opened
            else "系統無法開啟瀏覽器。"
        )

    official_site.currentIndexChanged.connect(update_bridge)
    open_official.clicked.connect(open_official_site)
    open_help.clicked.connect(open_official_help)
    update_bridge(official_site.currentIndex())
    return panel
