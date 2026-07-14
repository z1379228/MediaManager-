from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from core.downloads.models import DownloadRequest, DownloadState
from core.downloads.queue import DownloadQueue


class RecordingBackend:
    def __init__(self):
        self.urls = []
        self.release = threading.Event()

    def download(self, request, progress, cancel_event):
        self.urls.append(request.url)
        progress({"downloaded_bytes": 50, "total_bytes": 100, "info_dict": {"title": request.url}})
        self.release.wait(1)
        return str(request.output_dir / "result.mp4")


def wait_for(predicate, timeout=2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached")


def test_request_validates_segment_and_priority(tmp_path: Path) -> None:
    request = DownloadRequest("https://youtu.be/example", tmp_path, priority=10, start_time=2, end_time=5)
    assert request.start_time == 2


def test_request_rejects_unsafe_output_filename(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output filename"):
        DownloadRequest(
            "https://youtu.be/example",
            tmp_path,
            output_filename="..\\escape.m4a",
            audio_only=True,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_request_rejects_non_finite_segment_times(
    tmp_path: Path, value: float
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        DownloadRequest("https://youtu.be/example", tmp_path, start_time=value)


def test_priority_queue_runs_higher_priority_first(tmp_path: Path) -> None:
    backend = RecordingBackend()
    downloads = DownloadQueue(backend, workers=1)
    downloads.add(DownloadRequest("https://youtu.be/low", tmp_path, priority=-1))
    downloads.add(DownloadRequest("https://youtu.be/high", tmp_path, priority=5))
    downloads.start()
    wait_for(lambda: bool(backend.urls))
    assert backend.urls[0].endswith("/high")
    backend.release.set()
    wait_for(lambda: all(task.state is DownloadState.COMPLETED for task in downloads.snapshots()))
    downloads.shutdown()


def test_cancel_queued_task(tmp_path: Path) -> None:
    downloads = DownloadQueue(RecordingBackend(), workers=1)
    task_id = downloads.add(DownloadRequest("https://youtu.be/x", tmp_path))
    assert downloads.cancel(task_id)
    assert downloads.snapshots()[0].state is DownloadState.CANCELLED




class FailingOnceBackend:
    def __init__(self):
        self.calls = 0

    def download(self, request, progress, cancel_event):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        return str(request.output_dir / "retry.mp4")


class FailThenBlockBackend:
    def __init__(self):
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def download(self, request, progress, cancel_event):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        self.started.set()
        self.release.wait(2)
        return str(request.output_dir / "result.mp4")


class CancelAwareBackend:
    def __init__(self):
        self.started = threading.Event()
        self.cancelled = threading.Event()

    def download(self, request, progress, cancel_event):
        self.started.set()
        if cancel_event.wait(2):
            self.cancelled.set()
            from core.downloads.errors import DownloadCancelled

            raise DownloadCancelled("shutdown")
        raise RuntimeError("cancel signal was not received")


class ResumableBackend:
    def __init__(self):
        self.calls = 0
        self.started = threading.Event()
        self.resumed = threading.Event()
        self.release = threading.Event()

    def download(self, request, progress, cancel_event):
        self.calls += 1
        if self.calls == 1:
            self.started.set()
            if cancel_event.wait(2):
                from core.downloads.errors import DownloadCancelled

                raise DownloadCancelled("paused")
            raise RuntimeError("pause signal was not received")
        self.resumed.set()
        self.release.wait(2)
        return str(request.output_dir / "resumed.mp4")


def test_queued_task_pause_persists_and_resumes(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    backend = RecordingBackend()
    backend.release.set()
    downloads = DownloadQueue(backend, workers=1, state_path=state)
    task_id = downloads.add(DownloadRequest("https://youtu.be/x", tmp_path))

    assert downloads.pause(task_id)
    assert downloads.snapshots()[0].state is DownloadState.PAUSED
    assert DownloadQueue(backend, state_path=state).snapshots()[0].state is DownloadState.PAUSED
    assert downloads.resume(task_id)
    assert downloads.snapshots()[0].state is DownloadState.QUEUED

    downloads.start()
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.COMPLETED)
    downloads.shutdown()


def test_running_task_pause_waits_for_provider_then_resumes(tmp_path: Path) -> None:
    backend = ResumableBackend()
    downloads = DownloadQueue(
        backend,
        workers=1,
        state_path=tmp_path / "queue.json",
    )
    task_id = downloads.add(DownloadRequest("https://youtu.be/x", tmp_path))
    downloads.start()
    assert backend.started.wait(2)

    assert downloads.pause(task_id)
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.PAUSED)
    assert downloads.resume(task_id)
    assert backend.resumed.wait(2)
    backend.release.set()
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.COMPLETED)
    assert backend.calls == 2
    downloads.shutdown()


def test_pause_resume_all_and_dynamic_worker_count(tmp_path: Path) -> None:
    downloads = DownloadQueue(RecordingBackend(), workers=1)
    for index in range(3):
        downloads.add(
            DownloadRequest(f"https://youtu.be/{index}", tmp_path)
        )
    assert downloads.pause_all() == 3
    assert all(
        task.state is DownloadState.PAUSED for task in downloads.snapshots()
    )
    assert downloads.resume_all() == 3
    assert all(
        task.state is DownloadState.QUEUED for task in downloads.snapshots()
    )

    downloads.start()
    wait_for(lambda: sum(thread.is_alive() for thread in downloads._threads) == 1)
    assert downloads.set_worker_count(3) == 3
    wait_for(lambda: sum(thread.is_alive() for thread in downloads._threads) == 3)
    assert downloads.set_worker_count(1) == 1
    wait_for(lambda: sum(thread.is_alive() for thread in downloads._threads) == 1)
    downloads.shutdown()


def test_queue_restores_waiting_task_from_disk(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    original = DownloadQueue(RecordingBackend(), workers=1, state_path=state)
    task_id = original.add(DownloadRequest("https://youtu.be/x", tmp_path))
    restored = DownloadQueue(RecordingBackend(), workers=1, state_path=state)
    task = restored.snapshots()[0]
    assert task.task_id == task_id
    assert task.state is DownloadState.QUEUED


def test_running_task_is_requeued_after_restart(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    state.write_text(
        '[{"task_id":"abc","url":"https://youtu.be/x",'
        '"output_dir":"' + str(tmp_path).replace("\\", "\\\\") + '",'
        '"priority":5,"state":"RUNNING"}]',
        encoding="utf-8",
    )
    restored = DownloadQueue(RecordingBackend(), workers=1, state_path=state)
    assert restored.snapshots()[0].state is DownloadState.QUEUED


def test_failed_task_can_be_retried(tmp_path: Path) -> None:
    backend = FailingOnceBackend()
    downloads = DownloadQueue(backend, workers=1, state_path=tmp_path / "queue.json")
    task_id = downloads.add(DownloadRequest("https://youtu.be/x", tmp_path))
    downloads.start()
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.FAILED)
    assert downloads.retry(task_id)
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.COMPLETED)
    assert backend.calls == 2
    downloads.shutdown()


def test_retry_rejects_equivalent_active_request(tmp_path: Path) -> None:
    backend = FailThenBlockBackend()
    downloads = DownloadQueue(backend, workers=1)
    request = DownloadRequest("https://youtu.be/example", tmp_path)
    failed = downloads.add(request)
    downloads.start()
    wait_for(
        lambda: downloads.snapshots()[0].state is DownloadState.FAILED
    )
    downloads.add(request)
    assert backend.started.wait(2)

    assert not downloads.retry(failed)

    backend.release.set()
    downloads.shutdown()


def test_completed_task_cannot_be_retried(tmp_path: Path) -> None:
    backend = RecordingBackend()
    backend.release.set()
    downloads = DownloadQueue(backend, workers=1)
    task_id = downloads.add(DownloadRequest("https://youtu.be/x", tmp_path))
    downloads.start()
    wait_for(lambda: downloads.snapshots()[0].state is DownloadState.COMPLETED)
    assert not downloads.retry(task_id)
    downloads.shutdown()


def test_malformed_persisted_queue_is_ignored(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    state.write_text("not-json", encoding="utf-8")
    assert DownloadQueue(RecordingBackend(), state_path=state).snapshots() == ()


def test_queue_round_trip_preserves_timed_comment_options(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    original = DownloadQueue(RecordingBackend(), state_path=state)
    original.add(
        DownloadRequest(
            "https://www.bilibili.com/video/BVexample",
            tmp_path,
            timed_comment_mode="ass",
            container_preset="mkv",
        )
    )

    restored = DownloadQueue(RecordingBackend(), state_path=state)
    request = restored.snapshots()[0].request

    assert request.timed_comment_mode == "ass"
    assert request.container_preset == "mkv"


def test_restore_salvages_valid_records_when_one_record_is_invalid(
    tmp_path: Path,
) -> None:
    import json

    state = tmp_path / "queue.json"
    original = DownloadQueue(RecordingBackend(), state_path=state)
    task_id = original.add(DownloadRequest("https://youtu.be/example", tmp_path))
    payload = json.loads(state.read_text(encoding="utf-8"))
    payload.append({"task_id": "bad", "priority": 99})
    state.write_text(json.dumps(payload), encoding="utf-8")

    restored = DownloadQueue(RecordingBackend(), state_path=state)

    assert [task.task_id for task in restored.snapshots()] == [task_id]


def test_queue_state_round_trip_supports_more_than_one_thousand_tasks(
    tmp_path: Path,
) -> None:
    state = tmp_path / "queue.json"
    original = DownloadQueue(RecordingBackend(), state_path=state)
    requests = [
        DownloadRequest(f"https://example.com/video/{index}", tmp_path)
        for index in range(1001)
    ]
    original.add_batch(requests)

    restored = DownloadQueue(RecordingBackend(), state_path=state)

    assert len(restored.snapshots()) == 1001


def test_add_rolls_back_memory_when_state_persistence_fails(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = DownloadQueue(
        RecordingBackend(), state_path=tmp_path / "queue.json"
    )

    def fail() -> None:
        raise OSError("disk full")

    monkeypatch.setattr(downloads, "_persist_locked", fail)
    with pytest.raises(RuntimeError, match="cannot save download queue"):
        downloads.add(DownloadRequest("https://youtu.be/example", tmp_path))

    assert downloads.snapshots() == ()
    assert downloads._pending.empty()


def test_worker_survives_running_state_persistence_failure(
    tmp_path: Path, monkeypatch
) -> None:
    backend = RecordingBackend()
    backend.release.set()
    downloads = DownloadQueue(
        backend, workers=1, state_path=tmp_path / "queue.json"
    )
    downloads.add(DownloadRequest("https://youtu.be/example", tmp_path))
    original = downloads._persist_locked
    failed = False

    def fail_once() -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("disk full")
        original()

    monkeypatch.setattr(downloads, "_persist_locked", fail_once)
    downloads.start()
    wait_for(
        lambda: downloads.snapshots()[0].state is DownloadState.FAILED
    )

    assert downloads._threads[0].is_alive()
    assert "queue state write failed" in downloads.snapshots()[0].error
    downloads.shutdown()


def test_shutdown_cancels_running_backend_and_requeues_task(
    tmp_path: Path,
) -> None:
    backend = CancelAwareBackend()
    downloads = DownloadQueue(backend, workers=1, state_path=tmp_path / "queue.json")
    downloads.add(DownloadRequest("https://youtu.be/example", tmp_path))
    downloads.start()
    assert backend.started.wait(2)

    downloads.shutdown(timeout=2)

    assert backend.cancelled.is_set()
    assert not downloads._threads
    task = downloads.snapshots()[0]
    assert task.state is DownloadState.QUEUED
    assert not task.cancel_event.is_set()


def test_progress_ignores_invalid_numbers_and_bounds_provider_text(
    tmp_path: Path,
) -> None:
    downloads = DownloadQueue(RecordingBackend())
    downloads.add(DownloadRequest("https://youtu.be/example", tmp_path))
    task = downloads._tasks[next(iter(downloads._tasks))]

    downloads._progress(
        task,
        {
            "downloaded_bytes": "invalid",
            "total_bytes": -1,
            "_speed_str": "x" * 1000,
            "_eta_str": ["invalid"],
            "info_dict": {"title": "t" * 1000},
        },
    )

    assert task.progress == 0
    assert len(task.title) == 500
    assert len(task.speed) == 100
    assert task.eta == ""


def test_clear_finished_keeps_active_tasks(tmp_path: Path) -> None:
    downloads = DownloadQueue(RecordingBackend(), state_path=tmp_path / "queue.json")
    waiting = downloads.add(DownloadRequest("https://youtu.be/wait", tmp_path))
    cancelled = downloads.add(DownloadRequest("https://youtu.be/cancel", tmp_path))
    downloads.cancel(cancelled)
    assert downloads.clear_finished() == 1
    snapshots = downloads.snapshots()
    assert len(snapshots) == 1 and snapshots[0].task_id == waiting
    restored = DownloadQueue(RecordingBackend(), state_path=tmp_path / "queue.json")
    assert len(restored.snapshots()) == 1


def test_clear_finished_rolls_back_when_persistence_fails(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = DownloadQueue(RecordingBackend())
    task_id = downloads.add(DownloadRequest("https://youtu.be/example", tmp_path))
    assert downloads.cancel(task_id)

    def fail() -> None:
        raise OSError("disk full")

    monkeypatch.setattr(downloads, "_persist_locked", fail)
    with pytest.raises(OSError, match="disk full"):
        downloads.clear_finished()

    assert downloads.snapshots()[0].task_id == task_id

