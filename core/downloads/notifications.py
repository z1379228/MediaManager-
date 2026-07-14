"""Transport-neutral aggregation for download completion notifications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.downloads.models import DownloadState, DownloadTask


@dataclass(frozen=True, slots=True)
class DownloadBatchSummary:
    completed: int
    failed: int
    cancelled: int
    output_dir: Path | None

    @property
    def total(self) -> int:
        return self.completed + self.failed + self.cancelled


class DownloadCompletionTracker:
    """Collapse one busy queue period into one terminal summary."""

    def __init__(self, tasks: Iterable[DownloadTask] = ()) -> None:
        self._active: set[str] = set()
        self._terminal: dict[str, DownloadState] = {}
        self._output_dirs: dict[str, Path] = {}
        for task in tasks:
            if task.state in {DownloadState.QUEUED, DownloadState.RUNNING}:
                self._active.add(task.task_id)
                self._output_dirs[task.task_id] = task.request.output_dir

    def observe(self, task: DownloadTask) -> DownloadBatchSummary | None:
        if task.state in {DownloadState.QUEUED, DownloadState.RUNNING}:
            self._active.add(task.task_id)
            self._terminal.pop(task.task_id, None)
            self._output_dirs[task.task_id] = task.request.output_dir
            return None
        if task.task_id not in self._active:
            return None
        self._active.remove(task.task_id)
        self._terminal[task.task_id] = task.state
        if self._active:
            return None
        summary = DownloadBatchSummary(
            completed=sum(
                state is DownloadState.COMPLETED
                for state in self._terminal.values()
            ),
            failed=sum(
                state is DownloadState.FAILED for state in self._terminal.values()
            ),
            cancelled=sum(
                state is DownloadState.CANCELLED
                for state in self._terminal.values()
            ),
            output_dir=next(
                (
                    self._output_dirs[task_id]
                    for task_id, state in reversed(tuple(self._terminal.items()))
                    if state is DownloadState.COMPLETED
                    and task_id in self._output_dirs
                ),
                None,
            ),
        )
        self._terminal.clear()
        self._output_dirs.clear()
        return summary


def completion_message(summary: DownloadBatchSummary) -> str:
    parts = []
    if summary.completed:
        parts.append(f"完成 {summary.completed} 個")
    if summary.failed:
        parts.append(f"失敗 {summary.failed} 個")
    if summary.cancelled:
        parts.append(f"取消 {summary.cancelled} 個")
    return "下載工作已結束：" + "、".join(parts)
