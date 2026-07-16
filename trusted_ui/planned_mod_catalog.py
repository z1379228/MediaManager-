"""Single read-only catalog for MOD work that is not runnable yet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PlannedModPriority = Literal["P0", "P1", "P2"]
PRIORITY_ORDER: dict[PlannedModPriority, int] = {"P0": 0, "P1": 1, "P2": 2}


@dataclass(frozen=True, slots=True)
class PlannedMod:
    """Describe an approved backlog item without registering a runtime MOD."""

    provider_id: str
    display_name: str
    priority: PlannedModPriority
    kind: str
    planned_capabilities: str
    implementation_gap: str
    state: str = "製作中"


# Ordering is intentional: priority first, then the agreed implementation order.
# Entries here are visible planning facts only. They must never be passed to a
# provider registry or gain an enable control until a real implementation and
# its security/integrity tests exist.
PLANNED_MODS = (
    PlannedMod(
        "gopeed-transfer",
        "Gopeed Bridge",
        "P2",
        "本機傳輸橋接 MOD",
        "由使用者明確交給已安裝的本機 Gopeed，核心不內建傳輸引擎",
        "本機 API 授權、版本契約及連接埠／token 預設關閉政策",
        "安全基線完成／未啟用",
    ),
    PlannedMod(
        "p2p-transfer",
        "P2P Transfer",
        "P2",
        "P2P 傳輸 MOD",
        "BitTorrent／Magnet 選檔、優先級與頻寬控制，清楚顯示上傳與做種",
        "法律確認、網路／儲存配額與隔離；不包含 torrent 搜尋或自動開埠",
        "安全基線完成／未啟用",
    ),
)

PLANNED_MOD_IDS = frozenset(item.provider_id for item in PLANNED_MODS)


@dataclass(frozen=True, slots=True)
class PriorityWorkItem:
    """Track current work priority without creating an enableable MOD."""

    item_id: str
    title: str
    priority: PlannedModPriority
    state: str
    scope: str
    acceptance: str


# This is a development queue, not a provider registry. P0/P1 entries refer
# to existing runtime MODs that need regression or boundary work; P2 entries
# remain candidates until their implementation and security tests exist.
PRIORITY_WORK_ITEMS = (
    PriorityWorkItem(
        "youtube-regression",
        "YouTube／Music 搜尋、播放清單與批量下載",
        "P0",
        "已完成離線驗證",
        "youtube、youtube-search、youtube-player、youtube-history、youtube-recovery",
        "單片／清單路由、縮圖、試聽停止、取消／暫停與重啟不自動下載均通過離線回歸",
    ),
    PriorityWorkItem(
        "bilibili-regression",
        "Bilibili 搜尋、縮圖、分 P、批量與彈幕",
        "P0",
        "已完成離線驗證",
        "bilibili、bilibili-search、bilibili-danmaku",
        "不借用 YouTube 工作區；分 P 有名稱；XML／ASS／MKV 選項在子 MOD 關閉時仍安全退回",
    ),
    PriorityWorkItem(
        "ani-gamer-flow",
        "動畫瘋分類、作品與集數流程",
        "P0",
        "已完成離線驗證",
        "ani-gamer、ani-gamer-search、ani-gamer-episodes、ani-gamer-offline",
        "近期熱播／新上架／分類、作品選取與集數狀態一致；403／Cloudflare 只顯示官方入口",
    ),
    PriorityWorkItem(
        "language-ui-contract",
        "核心語言與父子 MOD UI 契約",
        "P0",
        "已完成離線驗證",
        "builtin_mod_panel、mod_groups",
        "zh-TW／zh-CN／en／ja 由核心傳遞；父 MOD 關閉時子 MOD 不可單獨啟用",
    ),
    PriorityWorkItem(
        "mega-runtime",
        "MEGA 檔案／資料夾類型與 MEGAcmd 依賴",
        "P1",
        "已完成離線驗證",
        "mega",
        "獨立於影音 UI；正確顯示檔案、壓縮檔、文件與資料夾，缺工具時提供可操作診斷",
    ),
    PriorityWorkItem(
        "facebook-public-url",
        "Facebook 公開影片網址讀取",
        "P1",
        "已完成離線驗證",
        "facebook",
        "只處理使用者明確提供的公開網址；失敗分類清楚，不讀取 Cookie 或繞過存取控制",
    ),
    PriorityWorkItem(
        "generic-site-smoke",
        "Generic yt-dlp 網站能力矩陣",
        "P1",
        "已完成離線驗證",
        "generic-ytdlp",
        "只宣稱已有 fixture／smoke 證據的網站，來源失敗時不改路由到其他網站 MOD",
    ),
    PriorityWorkItem(
        "speech-runtime",
        "Speech-to-Text 工具與模型診斷",
        "P1",
        "已完成離線驗證",
        "speech-to-text",
        "whisper-cli／模型缺失可明確選取安裝或匯入；不自動下載、不在乾淨啟動執行",
    ),
    PriorityWorkItem(
        "gopeed-transfer",
        "Gopeed Bridge",
        "P2",
        "安全基線完成／未啟用",
        "gopeed-transfer",
        "先完成本機 API 授權、token 生命週期與預設關閉政策，再評估獨立 MOD",
    ),
    PriorityWorkItem(
        "p2p-transfer",
        "P2P／Torrent 傳輸",
        "P2",
        "安全基線完成／未啟用",
        "p2p-transfer",
        "另建法律、網路、儲存配額與隔離模型；不進入網站下載核心或自動開埠",
    ),
)

PRIORITY_WORK_ITEM_IDS = frozenset(item.item_id for item in PRIORITY_WORK_ITEMS)


def priority_work_items(
    priority: PlannedModPriority | None = None,
) -> tuple[PriorityWorkItem, ...]:
    """Return the development queue in deterministic P0 → P1 → P2 order."""

    items = (
        item for item in PRIORITY_WORK_ITEMS if priority is None or item.priority == priority
    )
    return tuple(sorted(items, key=lambda item: (PRIORITY_ORDER[item.priority], item.item_id)))
