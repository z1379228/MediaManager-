"""Small helpers for low-overhead task-table refreshes."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator


VISIBLE_ACTIVE_INTERVAL_MS = 500
VISIBLE_IDLE_INTERVAL_MS = 1500
HIDDEN_ACTIVE_INTERVAL_MS = 2500
HIDDEN_IDLE_INTERVAL_MS = 10_000
RESIZE_CONTENTS_SAMPLE_ROWS = 50


def visible_rows_signature(rows: Iterable[Iterable[object]]) -> tuple[tuple[str, ...], ...]:
    """Normalize only displayed values so unchanged tables can skip repainting."""

    return tuple(tuple(str(value) for value in row) for row in rows)


def task_table_interval(*, active: bool, visible: bool) -> int:
    if not visible:
        return HIDDEN_ACTIVE_INTERVAL_MS if active else HIDDEN_IDLE_INTERVAL_MS
    return VISIBLE_ACTIVE_INTERVAL_MS if active else VISIBLE_IDLE_INTERVAL_MS


def limit_resize_contents_work(
    header: object,
    *,
    sample_rows: int = RESIZE_CONTENTS_SAMPLE_ROWS,
) -> None:
    """Bound content-based column sizing without disabling automatic widths."""

    if sample_rows < 0:
        raise ValueError("resize sample rows must not be negative")
    header.setResizeContentsPrecision(sample_rows)


@contextmanager
def suspended_resize_to_contents(header: object) -> Iterator[None]:
    """Defer repeated content-width scans until one coherent update completes."""

    from PySide6.QtWidgets import QHeaderView

    resize_to_contents = QHeaderView.ResizeMode.ResizeToContents
    fixed = QHeaderView.ResizeMode.Fixed
    deferred: list[tuple[int, object]] = []
    try:
        for section in range(int(header.count())):
            mode = header.sectionResizeMode(section)
            if mode == resize_to_contents:
                header.setSectionResizeMode(section, fixed)
                deferred.append((section, mode))
        yield
    finally:
        for section, mode in deferred:
            header.setSectionResizeMode(section, mode)


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
