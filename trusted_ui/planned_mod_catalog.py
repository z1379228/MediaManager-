"""Single read-only catalog for MOD work that is not runnable yet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PlannedModPriority = Literal["P0", "P1", "P2"]


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
    ),
    PlannedMod(
        "p2p-transfer",
        "P2P Transfer",
        "P2",
        "P2P 傳輸 MOD",
        "BitTorrent／Magnet 選檔、優先級與頻寬控制，清楚顯示上傳與做種",
        "法律確認、網路／儲存配額與隔離；不包含 torrent 搜尋或自動開埠",
    ),
)

PLANNED_MOD_IDS = frozenset(item.provider_id for item in PLANNED_MODS)
