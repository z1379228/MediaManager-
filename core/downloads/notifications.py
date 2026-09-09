"""Transport-neutral aggregation for download completion notifications."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
import threading
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


@dataclass(frozen=True, slots=True)
class DownloadNotificationDecision:
    immediate: DownloadTask | None
    schedule_flush: bool = False


class DownloadNotificationCoalescer:
    """Keep only the newest high-frequency RUNNING snapshot per task."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, DownloadState] = {}
        self._pending: dict[str, DownloadTask] = {}
        self._flush_scheduled = False

    def submit(self, task: DownloadTask) -> DownloadNotificationDecision:
        snapshot = replace(task)
        with self._lock:
            previous_state = self._states.get(snapshot.task_id)
            terminal = snapshot.state in {
                DownloadState.COMPLETED,
                DownloadState.FAILED,
                DownloadState.CANCELLED,
            }
            state_transition = previous_state is not snapshot.state
            if terminal:
                self._states.pop(snapshot.task_id, None)
                self._pending.pop(snapshot.task_id, None)
                return DownloadNotificationDecision(snapshot)
            self._states[snapshot.task_id] = snapshot.state
            if snapshot.state is not DownloadState.RUNNING or state_transition:
                self._pending.pop(snapshot.task_id, None)
                return DownloadNotificationDecision(snapshot)
            self._pending[snapshot.task_id] = snapshot
            schedule_flush = not self._flush_scheduled
            self._flush_scheduled = True
            return DownloadNotificationDecision(
                None,
                schedule_flush=schedule_flush,
            )

    def flush(self) -> tuple[DownloadTask, ...]:
        with self._lock:
            snapshots = tuple(self._pending.values())
            self._pending.clear()
            self._flush_scheduled = False
            return snapshots


class DownloadCompletionTracker:
    """Collapse one busy queue period into one terminal summary."""

    def __init__(self, tasks: Iterable[DownloadTask] = ()) -> None:
        self._active: set[str] = set()
        self._terminal: dict[str, DownloadState] = {}
        self._output_dirs: dict[str, Path] = {}
        for task in tasks:
            if task.state in {
                DownloadState.QUEUED,
                DownloadState.RUNNING,
                DownloadState.RETRYING,
            }:
                self._active.add(task.task_id)
                self._output_dirs[task.task_id] = task.request.output_dir

    def observe(self, task: DownloadTask) -> DownloadBatchSummary | None:
        if task.state in {
            DownloadState.QUEUED,
            DownloadState.RUNNING,
            DownloadState.RETRYING,
        }:
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
