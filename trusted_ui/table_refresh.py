"""Small helpers for low-overhead task-table refreshes."""

from __future__ import annotations

from collections.abc import Iterable


def visible_rows_signature(rows: Iterable[Iterable[object]]) -> tuple[tuple[str, ...], ...]:
    """Normalize only displayed values so unchanged tables can skip repainting."""

    return tuple(tuple(str(value) for value in row) for row in rows)


def task_table_interval(*, active: bool, visible: bool) -> int:
    if not visible:
        return 2500
    return 500 if active else 1500
