from __future__ import annotations

from trusted_ui.builtin_mod_panel import BUILTIN_MOD_IDS
from trusted_ui.planned_mod_catalog import (
    PLANNED_MOD_IDS,
    PLANNED_MODS,
    PRIORITY_WORK_ITEM_IDS,
    PRIORITY_WORK_ITEMS,
    priority_work_items,
)


def test_planned_mod_catalog_is_ordered_and_separate_from_runtime_mods() -> None:
    assert PLANNED_MODS == ()
    assert PLANNED_MOD_IDS == frozenset()
    assert {"gopeed-transfer", "p2p-transfer"} <= BUILTIN_MOD_IDS
    assert not PLANNED_MOD_IDS & BUILTIN_MOD_IDS
    assert len(PLANNED_MOD_IDS) == len(PLANNED_MODS)


def test_official_bridges_stay_separate_from_pending_download_mods() -> None:
    assert not PLANNED_MOD_IDS & {
        "instagram",
        "threads",
    }
    assert not {
        "ani-gamer",
        "ani-gamer-search",
        "ani-gamer-episodes",
        "ani-gamer-offline",
        "ani-gamer-player",
    } & (PLANNED_MOD_IDS | BUILTIN_MOD_IDS)
    assert "bilibili-danmaku" not in PLANNED_MOD_IDS
    assert not {"facebook", "mega"} & PLANNED_MOD_IDS


def test_priority_work_queue_is_sorted_without_registering_backlog_items() -> None:
    ordered = priority_work_items()
    assert tuple(item.priority for item in ordered) == (
        "P0",
        "P0",
        "P0",
        "P1",
        "P1",
        "P1",
        "P1",
    )
    assert ordered == tuple(sorted(ordered, key=lambda item: (item.priority, item.item_id)))
    assert len(PRIORITY_WORK_ITEM_IDS) == len(PRIORITY_WORK_ITEMS)
    assert not PRIORITY_WORK_ITEM_IDS & BUILTIN_MOD_IDS


def test_priority_work_queue_supports_deterministic_filters() -> None:
    assert tuple(item.item_id for item in priority_work_items("P0")) == (
        "bilibili-regression",
        "language-ui-contract",
        "youtube-regression",
    )
    assert all(item.priority == "P1" for item in priority_work_items("P1"))


def test_p0_work_items_have_offline_validation_status() -> None:
    p0_items = priority_work_items("P0")
    assert len(p0_items) == 3
    assert {item.state for item in p0_items} == {"已完成離線驗證"}
    assert all(item.scope and item.acceptance for item in p0_items)


def test_p1_work_items_have_offline_validation_status() -> None:
    p1_items = priority_work_items("P1")
    assert len(p1_items) == 4
    assert {item.state for item in p1_items} == {"已完成離線驗證"}
    assert all(item.scope and item.acceptance for item in p1_items)


def test_completed_transfer_mods_are_not_left_in_the_planned_queue() -> None:
    assert priority_work_items("P2") == ()
    assert not {"gopeed-transfer", "p2p-transfer"} & PRIORITY_WORK_ITEM_IDS
