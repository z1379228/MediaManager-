from __future__ import annotations

from pathlib import Path

from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.downloads.notifications import (
    DownloadBatchSummary,
    DownloadCompletionTracker,
    completion_message,
)


def task(
    task_id: str,
    state: DownloadState,
    output_dir: Path,
) -> DownloadTask:
    return DownloadTask(
        task_id,
        DownloadRequest(f"https://youtu.be/{task_id}", output_dir),
        state=state,
    )


def test_completion_tracker_emits_once_when_all_active_tasks_end(
    tmp_path: Path,
) -> None:
    tracker = DownloadCompletionTracker()
    assert tracker.observe(task("one", DownloadState.QUEUED, tmp_path)) is None
    assert tracker.observe(task("two", DownloadState.QUEUED, tmp_path)) is None
    assert tracker.observe(task("one", DownloadState.RUNNING, tmp_path)) is None
    assert tracker.observe(task("one", DownloadState.RETRYING, tmp_path)) is None
    assert tracker.observe(task("one", DownloadState.COMPLETED, tmp_path)) is None
    summary = tracker.observe(task("two", DownloadState.FAILED, tmp_path))
    assert summary is not None
    assert (summary.completed, summary.failed, summary.cancelled) == (1, 1, 0)
    assert summary.output_dir == tmp_path
    assert completion_message(summary) == "下載工作已結束：完成 1 個、失敗 1 個"


def test_completion_tracker_seeds_restored_active_tasks(tmp_path: Path) -> None:
    tracker = DownloadCompletionTracker(
        (task("restored", DownloadState.QUEUED, tmp_path),)
    )
    summary = tracker.observe(task("restored", DownloadState.CANCELLED, tmp_path))
    assert summary is not None
    assert summary.total == 1 and summary.cancelled == 1
    assert summary.output_dir is None


def test_completion_tracker_ignores_terminal_history(tmp_path: Path) -> None:
    tracker = DownloadCompletionTracker()
    assert tracker.observe(task("old", DownloadState.COMPLETED, tmp_path)) is None


def test_completion_message_includes_cancelled_count() -> None:
    summary = DownloadBatchSummary(
        completed=0,
        failed=1,
        cancelled=2,
        output_dir=None,
    )
    assert completion_message(summary) == "下載工作已結束：失敗 1 個、取消 2 個"
