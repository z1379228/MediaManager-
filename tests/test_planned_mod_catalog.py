from __future__ import annotations

from trusted_ui.builtin_mod_panel import BUILTIN_MOD_IDS
from trusted_ui.planned_mod_catalog import PLANNED_MOD_IDS, PLANNED_MODS


def test_planned_mod_catalog_is_ordered_and_separate_from_runtime_mods() -> None:
    assert tuple(item.provider_id for item in PLANNED_MODS) == (
        "bilibili-danmaku",
        "ani-gamer-offline",
        "facebook",
        "mega",
        "self-check",
        "direct-transfer",
        "gopeed-transfer",
        "p2p-transfer",
    )
    assert tuple(item.priority for item in PLANNED_MODS) == (
        "P1",
        "P1",
        "P1",
        "P1",
        "P2",
        "P2",
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
    assert {"facebook", "ani-gamer-offline", "bilibili-danmaku"} <= (
        PLANNED_MOD_IDS
    )


def test_self_check_entry_preserves_its_non_provider_boundary() -> None:
    self_check = next(item for item in PLANNED_MODS if item.provider_id == "self-check")

    assert "非外部 provider" in self_check.kind
    assert "不重跑完整流程" in self_check.planned_capabilities
