from __future__ import annotations

from trusted_ui.builtin_mod_panel import BUILTIN_MOD_IDS
from trusted_ui.planned_mod_catalog import PLANNED_MOD_IDS, PLANNED_MODS


def test_planned_mod_catalog_is_ordered_and_separate_from_runtime_mods() -> None:
    assert tuple(item.provider_id for item in PLANNED_MODS) == (
        "gopeed-transfer",
        "p2p-transfer",
    )
    assert tuple(item.priority for item in PLANNED_MODS) == (
        "P2",
        "P2",
    )
    assert not PLANNED_MOD_IDS & BUILTIN_MOD_IDS
    assert len(PLANNED_MOD_IDS) == len(PLANNED_MODS)
    assert {item.state for item in PLANNED_MODS} == {"製作中"}


def test_official_bridges_stay_separate_from_pending_download_mods() -> None:
    assert not PLANNED_MOD_IDS & {
        "ani-gamer",
        "ani-gamer-search",
        "instagram",
        "threads",
    }
    assert "ani-gamer-offline" not in PLANNED_MOD_IDS
    assert "ani-gamer-offline" in BUILTIN_MOD_IDS
    assert "bilibili-danmaku" not in PLANNED_MOD_IDS
    assert not {"facebook", "mega"} & PLANNED_MOD_IDS
