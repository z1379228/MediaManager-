"""Small helpers for low-overhead task-table refreshes."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator


VISIBLE_ACTIVE_INTERVAL_MS = 500
VISIBLE_IDLE_INTERVAL_MS = 1500
HIDDEN_ACTIVE_INTERVAL_MS = 2500
HIDDEN_IDLE_INTERVAL_MS = 10_000


def visible_rows_signature(rows: Iterable[Iterable[object]]) -> tuple[tuple[str, ...], ...]:
    """Normalize only displayed values so unchanged tables can skip repainting."""

    return tuple(tuple(str(value) for value in row) for row in rows)


def task_table_interval(*, active: bool, visible: bool) -> int:
    if not visible:
        return HIDDEN_ACTIVE_INTERVAL_MS if active else HIDDEN_IDLE_INTERVAL_MS
    return VISIBLE_ACTIVE_INTERVAL_MS if active else VISIBLE_IDLE_INTERVAL_MS


@contextmanager
def suspended_table_updates(table: object) -> Iterator[None]:
    """Avoid intermediate repaints while applying one coherent table snapshot."""

    updates_enabled = bool(table.updatesEnabled())
    if updates_enabled:
        table.setUpdatesEnabled(False)
    try:
        yield
    finally:
        if updates_enabled:
            table.setUpdatesEnabled(True)
