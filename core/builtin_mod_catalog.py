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
        "bilibili", "Bilibili", "download", "影片、分段與彈幕 XML／ASS／MKV",
        "Bilibili 下載工作區（預設停用）", False,
        dependency_ids=("yt-dlp", "javascript-runtime", "ffmpeg"),
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
        "youtube-search", "YouTube Search", "discovery", "搜尋 YouTube 影片與音樂",
        "網站搜尋 → 搜尋 MOD", True, parent_provider_id="youtube",
        dependency_ids=("yt-dlp", "yt-dlp-ejs", "javascript-runtime"),
    ),
    BuiltinModDescriptor(
        "bilibili-search", "Bilibili Search", "discovery", "獨立搜尋 Bilibili 公開影片",
        "網站搜尋 → 搜尋 MOD（預設停用）", False, parent_provider_id="bilibili",
    ),
    BuiltinModDescriptor(
        "ani-gamer-search", "動畫瘋官方搜尋", "discovery", "搜尋官方公開作品目錄；只開官方頁",
        "網站搜尋 → 搜尋 MOD（預設停用）", False,
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
        "media-convert", "Media Convert", "feature", "本機轉封裝、轉檔、壓縮、串接、切割與字幕處理",
        "啟用後顯示 Media Convert 工作區", False, "media-convert",
        dependency_ids=("ffmpeg",),
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
