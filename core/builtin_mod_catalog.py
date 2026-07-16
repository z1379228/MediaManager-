"""Typed single source of truth for built-in MOD presentation and routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BuiltinModKind = Literal["download", "discovery", "feature"]


@dataclass(frozen=True, slots=True)
class BuiltinModDescriptor:
    provider_id: str
    display_name: str
    kind: BuiltinModKind
    purpose: str
    control_location: str
    default_enabled: bool
    optional_workspace: str = ""
    parent_provider_id: str = ""
    dependency_ids: tuple[str, ...] = ()


BUILTIN_MOD_CATALOG = (
    BuiltinModDescriptor(
        "youtube", "YouTube", "download", "批量、分段與音訊下載",
        "YouTube 下載工作區", True,
        dependency_ids=("yt-dlp", "yt-dlp-ejs", "javascript-runtime", "ffmpeg"),
    ),
    BuiltinModDescriptor(
        "generic-ytdlp", "其他網站 Beta", "download", "白名單網站的分析、清單與下載",
        "MOD 管理（預設停用；不顯示於網站工作區）", False,
        dependency_ids=("yt-dlp", "yt-dlp-ejs", "javascript-runtime", "ffmpeg"),
    ),
    BuiltinModDescriptor(
        "bilibili", "Bilibili", "download", "影片、番劇與分段下載",
        "Bilibili 下載工作區（預設停用）", False,
        dependency_ids=("yt-dlp", "javascript-runtime", "ffmpeg"),
    ),
    BuiltinModDescriptor(
        "ani-gamer", "動畫瘋", "feature", "官方作品目錄與播放頁入口",
        "啟用後顯示動畫瘋官方目錄工作區", False, "ani-gamer",
    ),
    BuiltinModDescriptor(
        "facebook", "Facebook", "download", "公開影片頁資訊、縮圖與分流下載",
        "啟用後顯示 Facebook 下載工作區", False, "facebook",
        dependency_ids=("yt-dlp", "javascript-runtime", "ffmpeg"),
    ),
    BuiltinModDescriptor(
        "mega", "MEGA", "download", "公開檔案分享辨識與官方 MEGAcmd 分流下載",
        "啟用後顯示 MEGA 下載工作區；下載需要 mega-get", False, "mega",
        dependency_ids=("mega-get",),
    ),
    BuiltinModDescriptor(
        "direct-http", "Direct HTTP", "download",
        "明確 HTTPS 檔案網址的續傳、雜湊驗證與本機下載",
        "啟用後顯示 Direct HTTP 工作區；不接管任何網站 MOD", False,
        "direct-http",
    ),
    BuiltinModDescriptor(
        "instagram", "Instagram", "feature", "官方公開媒體頁與帳號資料匯出入口",
        "啟用後顯示 Instagram 官方工具工作區", False, "instagram",
    ),
    BuiltinModDescriptor(
        "threads", "Threads", "feature", "官方貼文頁與帳號資料匯出入口",
        "啟用後顯示 Threads 官方工具工作區", False, "threads",
    ),
    BuiltinModDescriptor(
        "twitter", "X / Twitter", "feature", "官方貼文頁與帳號資料匯出入口",
        "啟用後顯示 X 官方工具工作區", False, "twitter",
    ),
    BuiltinModDescriptor(
        "youtube-search", "YouTube Search", "discovery", "搜尋 YouTube 影片與音樂",
        "網站搜尋 → 搜尋 MOD", True, parent_provider_id="youtube",
        dependency_ids=("yt-dlp", "yt-dlp-ejs", "javascript-runtime"),
    ),
    BuiltinModDescriptor(
        "bilibili-search", "Bilibili Search", "discovery", "獨立搜尋 Bilibili 公開影片",
        "網站搜尋 → 搜尋 MOD（預設停用）", False, parent_provider_id="bilibili",
    ),
    BuiltinModDescriptor(
        "bilibili-danmaku", "Bilibili Danmaku", "feature",
        "依需求保留 XML、轉換 ASS 或封裝 MKV",
        "Bilibili 下載工作區（預設停用）", False,
        parent_provider_id="bilibili", dependency_ids=("ffmpeg",),
    ),
    BuiltinModDescriptor(
        "ani-gamer-search", "動畫瘋官方搜尋", "discovery", "搜尋官方公開作品目錄；只開官方頁",
        "動畫瘋官方目錄工作區（預設停用）", False,
        parent_provider_id="ani-gamer",
    ),
    BuiltinModDescriptor(
        "ani-gamer-episodes", "動畫瘋集數導覽", "discovery",
        "讀取官方公開作品頁並列出可選集數；只開官方頁",
        "動畫瘋官方目錄工作區（預設停用）", False,
        parent_provider_id="ani-gamer",
    ),
    BuiltinModDescriptor(
        "ani-gamer-offline", "動畫瘋番劇儲存", "feature",
        "保存已選取單集的公開資料、封面與使用者本機媒體副本",
        "動畫瘋官方目錄 → 選取單集離線保存（預設停用）", False,
        parent_provider_id="ani-gamer",
    ),
    BuiltinModDescriptor(
        "youtube-player", "YouTube Player", "discovery", "可選的低畫質影片預覽",
        "網站搜尋 → 搜尋 MOD", False, parent_provider_id="youtube",
        dependency_ids=("yt-dlp", "yt-dlp-ejs", "javascript-runtime", "ffmpeg"),
    ),
    BuiltinModDescriptor(
        "youtube-history", "YouTube History", "discovery", "記錄有限搜尋偏好",
        "網站搜尋 → 搜尋 MOD", True, parent_provider_id="youtube",
    ),
    BuiltinModDescriptor(
        "youtube-recovery", "YouTube Recovery", "discovery", "尋找失效影片替代項目",
        "網站搜尋 → 搜尋 MOD", True, parent_provider_id="youtube",
    ),
    BuiltinModDescriptor(
        "youtube-similar", "YouTube Similar", "discovery", "隨機尋找相似內容",
        "網站搜尋 → 搜尋 MOD", True, parent_provider_id="youtube",
    ),
    BuiltinModDescriptor(
        "youtube-auto-split", "YouTube Auto Split", "discovery", "分析並預覽長影片切割點",
        "MOD 管理啟用；YouTube 下載工作區使用", True, parent_provider_id="youtube",
        dependency_ids=("ffmpeg",),
    ),
    BuiltinModDescriptor(
        "instagram-page", "Instagram Official Page", "feature",
        "驗證 Instagram 公開貼文、Reel 或 IGTV 網址並交由系統瀏覽器開啟",
        "Instagram 官方工具工作區", False, parent_provider_id="instagram",
    ),
    BuiltinModDescriptor(
        "instagram-export", "Instagram Data Export", "feature",
        "開啟 Meta 官方 Instagram 資料匯出說明",
        "Instagram 官方工具工作區", False, parent_provider_id="instagram",
    ),
    BuiltinModDescriptor(
        "threads-page", "Threads Official Post", "feature",
        "驗證 Threads 官方貼文網址並交由系統瀏覽器開啟",
        "Threads 官方工具工作區", False, parent_provider_id="threads",
    ),
    BuiltinModDescriptor(
        "threads-export", "Threads Data Export", "feature",
        "開啟 Meta 官方 Threads 資料匯出說明",
        "Threads 官方工具工作區", False, parent_provider_id="threads",
    ),
    BuiltinModDescriptor(
        "twitter-page", "X Official Post", "feature",
        "驗證 X／Twitter 官方貼文網址並交由系統瀏覽器開啟",
        "X 官方工具工作區", False, parent_provider_id="twitter",
    ),
    BuiltinModDescriptor(
        "twitter-export", "X Data Archive", "feature",
        "開啟 X 官方帳號資料封存下載說明",
        "X 官方工具工作區", False, parent_provider_id="twitter",
    ),
    BuiltinModDescriptor(
        "media-convert", "Media Convert", "feature", "本機轉封裝、轉檔、壓縮、串接、切割與字幕處理",
        "啟用後顯示 Media Convert 工作區", False, "media-convert",
        dependency_ids=("ffmpeg",),
    ),
    BuiltinModDescriptor(
        "media-ad-trim", "Local Ad Segment Trim", "feature",
        "僅處理使用者選取的本機媒體，依手動時間區間剪除廣告段落並輸出新檔",
        "Media Convert → 本機廣告段落剪除", False,
        parent_provider_id="media-convert", dependency_ids=("ffmpeg",),
    ),
    BuiltinModDescriptor(
        "speech-to-text", "Speech to Text", "feature", "本機語音轉文字與 TXT、SRT、VTT 輸出",
        "啟用後顯示 Speech to Text 工作區", False, "speech-to-text",
        dependency_ids=("whisper-cli", "speech-model"),
    ),
    BuiltinModDescriptor(
        "automation", "Automation", "feature", "排程網址、監看資料夾與剪貼簿網址候選",
        "啟用後顯示 Automation 工作區；規則仍預設關閉", False, "automation",
    ),
)

BUILTIN_MOD_BY_ID = {item.provider_id: item for item in BUILTIN_MOD_CATALOG}
BUILTIN_MOD_IDS = frozenset(BUILTIN_MOD_BY_ID)
BUILTIN_MOD_PARENT = {
    item.provider_id: item.parent_provider_id
    for item in BUILTIN_MOD_CATALOG
    if item.parent_provider_id
}
BUILTIN_MOD_CHILDREN = {
    parent_id: tuple(
        item.provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id == parent_id
    )
    for parent_id in dict.fromkeys(BUILTIN_MOD_PARENT.values())
}
OPTIONAL_WORKSPACE_IDS = frozenset(
    item.provider_id for item in BUILTIN_MOD_CATALOG if item.optional_workspace
)


def builtin_mod_ids(kind: BuiltinModKind) -> frozenset[str]:
    return frozenset(
        descriptor.provider_id
        for descriptor in BUILTIN_MOD_CATALOG
        if descriptor.kind == kind
    )


def builtin_mod_descriptor(provider_id: str) -> BuiltinModDescriptor:
    try:
        return BUILTIN_MOD_BY_ID[provider_id]
    except KeyError:
        raise KeyError(f"unknown built-in MOD: {provider_id}") from None


def builtin_default_enabled(provider_id: str) -> bool:
    return builtin_mod_descriptor(provider_id).default_enabled
