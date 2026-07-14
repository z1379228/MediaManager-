"""Threaded priority download queue with durable task history."""

from __future__ import annotations

import itertools
import json
import math
import queue
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from core.downloads.archive import DownloadArchive, DuplicateDownloadError
from core.downloads.errors import DownloadCancelled
from core.downloads.models import DownloadRequest, DownloadState, DownloadTask


_MAX_QUEUE_TASKS = 10_000
_MAX_QUEUE_STATE_BYTES = 16 * 1024 * 1024
_SHUTDOWN_PRIORITY = -1000


class DownloadBackend(Protocol):
    def download(
        self,
        request: DownloadRequest,
        progress: Callable[[dict[str, Any]], None],
        cancel_event: threading.Event,
    ) -> str: ...


class DownloadQueue:
    def __init__(
        self,
        backend: DownloadBackend,
        *,
        workers: int = 2,
        state_path: Path | None = None,
        archive_path: Path | None = None,
    ) -> None:
        self.backend = backend
        self.worker_count = max(1, min(workers, 4))
        self.state_path = state_path
        self.archive = DownloadArchive(archive_path)
        self._pending: queue.PriorityQueue[tuple[int, int, str | None]] = (
            queue.PriorityQueue()
        )
        self._tasks: dict[str, DownloadTask] = {}
        self._sequence = itertools.count()
        self._lock = threading.RLock()
        self._listeners: list[Callable[[DownloadTask], None]] = []
        self._threads: list[threading.Thread] = []
        self._stopping = threading.Event()
        self._restore()

    def start(self) -> None:
        with self._lock:
            self._threads = [thread for thread in self._threads if thread.is_alive()]
            if self._threads:
                return
            self._stopping.clear()
            for index in range(self.worker_count):
                thread = threading.Thread(
                    target=self._worker,
                    name=f"download-{index + 1}",
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)

    def set_worker_count(self, workers: int) -> int:
        target = max(1, min(workers, 4))
        with self._lock:
            self._threads = [thread for thread in self._threads if thread.is_alive()]
            live = len(self._threads)
            self.worker_count = target
            if not self._threads or self._stopping.is_set():
                return target
            if target > live:
                for index in range(live, target):
                    thread = threading.Thread(
                        target=self._worker,
                        name=f"download-{index + 1}",
                        daemon=True,
                    )
                    thread.start()
                    self._threads.append(thread)
            elif target < live:
                for _ in range(live - target):
                    self._pending.put(
                        (_SHUTDOWN_PRIORITY, next(self._sequence), None)
                    )
        return target

    def shutdown(self, timeout: float = 3.0) -> None:
        with self._lock:
            self._stopping.set()
            threads = tuple(self._threads)
            for task in self._tasks.values():
                if task.state is DownloadState.RUNNING:
                    task.cancel_event.set()
            for _ in threads:
                self._pending.put(
                    (_SHUTDOWN_PRIORITY, next(self._sequence), None)
                )
        deadline = time.monotonic() + max(0.0, timeout)
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        with self._lock:
            self._threads = [thread for thread in threads if thread.is_alive()]
            try:
                self._persist_locked()
            except OSError:
                pass

    def subscribe(self, listener: Callable[[DownloadTask], None]) -> None:
        self._listeners.append(listener)

    def add(self, request: DownloadRequest) -> str:
        return self.add_batch([request])[0]

    def add_batch(self, requests: list[DownloadRequest]) -> tuple[str, ...]:
        if not requests:
            return ()
        tasks: list[DownloadTask] = []
        with self._lock:
            if self._stopping.is_set():
                raise RuntimeError("download queue is shutting down")
            if len(self._tasks) + len(requests) > _MAX_QUEUE_TASKS:
                raise RuntimeError(
                    "download queue task limit reached; clear finished tasks first"
                )
            existing = {
                self.archive.request_key(task.request)
                for task in self._tasks.values()
                if task.state not in {
                    DownloadState.FAILED,
                    DownloadState.CANCELLED,
                }
            }
            batch: set[str] = set()
            for request in requests:
                key = self.archive.request_key(request)
                if (
                    key in batch
                    or key in existing
                    or self.archive.contains(request)
                ):
                    raise DuplicateDownloadError(
                        f"download is already queued or archived: {request.url}"
                    )
                batch.add(key)
            for request in requests:
                task = DownloadTask(uuid.uuid4().hex, request)
                self._tasks[task.task_id] = task
                tasks.append(task)
            try:
                self._persist_locked()
            except OSError as error:
                for task in tasks:
                    self._tasks.pop(task.task_id, None)
                raise RuntimeError(f"cannot save download queue: {error}") from error
            except Exception:
                for task in tasks:
                    self._tasks.pop(task.task_id, None)
                raise
            for task in tasks:
                self._enqueue(task)
        for task in tasks:
            self._notify(task)
        return tuple(task.task_id for task in tasks)

    def retry(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if (
                self._stopping.is_set()
                or task is None
                or task.state not in {
                    DownloadState.FAILED,
                    DownloadState.CANCELLED,
                }
            ):
                return False
            key = self.archive.request_key(task.request)
            if self.archive.contains(task.request) or any(
                other.task_id != task_id
                and other.state
                not in {DownloadState.FAILED, DownloadState.CANCELLED}
                and self.archive.request_key(other.request) == key
                for other in self._tasks.values()
            ):
                return False
            previous = replace(task)
            task.state = DownloadState.QUEUED
            task.progress = 0.0
            task.speed = ""
            task.eta = ""
            task.output_path = ""
            task.error = ""
            task.cancel_event = threading.Event()
            task.pause_requested = threading.Event()
            try:
                self._persist_locked()
            except Exception:
                task.state = previous.state
                task.progress = previous.progress
                task.speed = previous.speed
                task.eta = previous.eta
                task.output_path = previous.output_path
                task.error = previous.error
                task.cancel_event = previous.cancel_event
                task.pause_requested = previous.pause_requested
                raise
            self._enqueue(task)
            snapshot = replace(task)
        self._notify(snapshot)
        return True

    def pause(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.state not in {
                DownloadState.QUEUED,
                DownloadState.RUNNING,
            }:
                return False
            if task.pause_requested.is_set():
                return False
            if task.state is DownloadState.QUEUED:
                task.state = DownloadState.PAUSED
                try:
                    self._persist_locked()
                except Exception:
                    task.state = DownloadState.QUEUED
                    raise
            else:
                task.pause_requested.set()
                task.cancel_event.set()
            task.speed = ""
            task.eta = ""
            snapshot = replace(task)
        self._notify(snapshot)
        return True

    def resume(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if self._stopping.is_set() or task is None:
                return False
            if task.state is not DownloadState.PAUSED:
                return False
            task.state = DownloadState.QUEUED
            task.speed = ""
            task.eta = ""
            task.error = ""
            task.cancel_event = threading.Event()
            task.pause_requested = threading.Event()
            try:
                self._persist_locked()
            except Exception:
                task.state = DownloadState.PAUSED
                raise
            self._enqueue(task)
            snapshot = replace(task)
        self._notify(snapshot)
        return True

    def pause_all(self) -> int:
        task_ids = tuple(
            task.task_id
            for task in self.snapshots()
            if task.state in {DownloadState.QUEUED, DownloadState.RUNNING}
        )
        return sum(self.pause(task_id) for task_id in task_ids)

    def resume_all(self) -> int:
        task_ids = tuple(
            task.task_id
            for task in self.snapshots()
            if task.state is DownloadState.PAUSED
        )
        return sum(self.resume(task_id) for task_id in task_ids)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.state in {
                DownloadState.COMPLETED,
                DownloadState.FAILED,
                DownloadState.CANCELLED,
            }:
                return False
            task.cancel_event.set()
            if task.state in {DownloadState.QUEUED, DownloadState.PAUSED}:
                task.state = DownloadState.CANCELLED
            self._persist_locked()
            snapshot = replace(task)
        self._notify(snapshot)
        return True

    def clear_finished(self) -> int:
        terminal = {
            DownloadState.COMPLETED,
            DownloadState.FAILED,
            DownloadState.CANCELLED,
        }
        with self._lock:
            previous_tasks = self._tasks.copy()
            removable = [
                task_id
                for task_id, task in self._tasks.items()
                if task.state in terminal
            ]
            for task_id in removable:
                del self._tasks[task_id]
            if removable:
                try:
                    self._persist_locked()
                except Exception:
                    self._tasks = previous_tasks
                    raise
        return len(removable)

    def snapshots(self) -> tuple[DownloadTask, ...]:
        with self._lock:
            return tuple(replace(task) for task in self._tasks.values())

    def _enqueue(self, task: DownloadTask) -> None:
        self._pending.put(
            (-task.request.priority, next(self._sequence), task.task_id)
        )

    def _worker(self) -> None:
        while True:
            _, _, task_id = self._pending.get()
            if task_id is None:
                return
            with self._lock:
                task = self._tasks[task_id]
                if task.state is not DownloadState.QUEUED:
                    continue
                if self._stopping.is_set():
                    self._enqueue(task)
                    continue
                task.state = DownloadState.RUNNING
                try:
                    self._persist_locked()
                except OSError as persist_error:
                    task.state = DownloadState.FAILED
                    task.error = f"queue state write failed: {persist_error}"
                    snapshot = replace(task)
                    persistence_failed = True
                else:
                    snapshot = replace(task)
                    persistence_failed = False
            self._notify(snapshot)
            if persistence_failed:
                continue
            output_path = ""
            terminal_state = DownloadState.COMPLETED
            error_text = ""
            try:
                output_path = self.backend.download(
                    task.request,
                    lambda status, current=task: self._progress(current, status),
                    task.cancel_event,
                )
                terminal_state = DownloadState.COMPLETED
            except DownloadCancelled:
                terminal_state = (
                    DownloadState.PAUSED
                    if task.pause_requested.is_set()
                    else DownloadState.QUEUED
                    if self._stopping.is_set()
                    else DownloadState.CANCELLED
                )
            except Exception as error:
                terminal_state = (
                    DownloadState.PAUSED
                    if task.pause_requested.is_set()
                    else DownloadState.QUEUED
                    if self._stopping.is_set() and task.cancel_event.is_set()
                    else (
                        DownloadState.CANCELLED
                        if task.cancel_event.is_set()
                        else DownloadState.FAILED
                    )
                )
                error_text = str(error)
            with self._lock:
                task.output_path = output_path
                task.state = terminal_state
                task.error = error_text
                if task.state is DownloadState.QUEUED:
                    task.progress = 0.0
                    task.speed = ""
                    task.eta = ""
                    task.output_path = ""
                    task.error = ""
                    task.cancel_event = threading.Event()
                    task.pause_requested = threading.Event()
                    self._enqueue(task)
                elif task.state is DownloadState.PAUSED:
                    task.speed = ""
                    task.eta = ""
                    task.output_path = ""
                    task.error = ""
                    task.cancel_event = threading.Event()
                    task.pause_requested = threading.Event()
                elif task.state is DownloadState.COMPLETED:
                    task.progress = 100.0
                if task.state is DownloadState.COMPLETED:
                    try:
                        self.archive.record(task.request)
                    except (OSError, RuntimeError) as error:
                        task.error = f"archive warning: {error}"
                try:
                    self._persist_locked()
                except OSError as error:
                    warning = f"queue state warning: {error}"
                    task.error = f"{task.error}; {warning}" if task.error else warning
                snapshot = replace(task)
            self._notify(snapshot)

    def _progress(self, task: DownloadTask, status: dict[str, Any]) -> None:
        with self._lock:
            info = status.get("info_dict") or {}
            title = info.get("title") if isinstance(info, dict) else None
            if isinstance(title, str) and title:
                task.title = title[:500]
            total = status.get("total_bytes") or status.get(
                "total_bytes_estimate"
            )
            downloaded = status.get("downloaded_bytes") or 0
            valid_total = (
                isinstance(total, (int, float))
                and not isinstance(total, bool)
                and math.isfinite(total)
                and total > 0
            )
            valid_downloaded = (
                isinstance(downloaded, (int, float))
                and not isinstance(downloaded, bool)
                and math.isfinite(downloaded)
                and downloaded >= 0
            )
            if valid_total and valid_downloaded:
                task.progress = max(
                    0.0, min(100.0, downloaded * 100.0 / total)
                )
            speed = status.get("_speed_str")
            eta = status.get("_eta_str")
            task.speed = speed.strip()[:100] if isinstance(speed, str) else ""
            task.eta = eta.strip()[:100] if isinstance(eta, str) else ""
            snapshot = replace(task)
        self._notify(snapshot)

    def _restore(self) -> None:
        if self.state_path is None or not self.state_path.is_file():
            return
        try:
            if self.state_path.stat().st_size > _MAX_QUEUE_STATE_BYTES:
                return
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return
            for item in raw[:_MAX_QUEUE_TASKS]:
                try:
                    task = self._task_from_payload(item)
                except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
                    continue
                if task.task_id in self._tasks:
                    continue
                if (
                    task.state is DownloadState.QUEUED
                    and self.archive.contains(task.request)
                ):
                    task.state = DownloadState.COMPLETED
                    task.progress = 100.0
                    task.error = "restored as completed from download archive"
                if task.state is DownloadState.COMPLETED:
                    try:
                        self.archive.record(task.request)
                    except (OSError, RuntimeError):
                        pass
                self._tasks[task.task_id] = task
                if task.state is DownloadState.QUEUED:
                    task.progress = 0.0
                    self._enqueue(task)
        except (OSError, ValueError, TypeError):
            return

    @staticmethod
    def _task_from_payload(item: object) -> DownloadTask:
        if not isinstance(item, dict):
            raise TypeError("queue task must be an object")

        def text_value(key: str, default: str, limit: int) -> str:
            value = item.get(key, default)
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f"queue task {key} is invalid")
            return value

        task_id = text_value("task_id", "", 64)
        if not task_id:
            raise ValueError("queue task id is invalid")
        priority = item.get("priority", 0)
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise ValueError("queue task priority is invalid")
        subtitle_languages = item.get("subtitle_languages", [])
        if not isinstance(subtitle_languages, list):
            raise ValueError("queue task subtitle languages are invalid")
        request = DownloadRequest(
            url=text_value("url", "", 4096),
            output_dir=Path(text_value("output_dir", "", 32_767)),
            priority=priority,
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            source_video_id=text_value("source_video_id", "", 100),
            source_title=text_value("source_title", "", 300),
            source_artist=text_value("source_artist", "", 200),
            source_language=text_value("source_language", "", 32),
            source_category=text_value("source_category", "", 100),
            output_filename=text_value("output_filename", "", 180),
            audio_only=item.get("audio_only", False),
            format_preset=text_value("format_preset", "best", 32),
            subtitle_mode=text_value("subtitle_mode", "none", 32),
            subtitle_languages=tuple(subtitle_languages),
            timed_comment_mode=text_value("timed_comment_mode", "none", 32),
            container_preset=text_value("container_preset", "auto", 32),
        )
        state = DownloadState(item.get("state", "QUEUED"))
        if state in {DownloadState.RUNNING, DownloadState.QUEUED}:
            state = DownloadState.QUEUED
        progress = item.get("progress", 0.0)
        if (
            not isinstance(progress, (int, float))
            or isinstance(progress, bool)
            or not math.isfinite(progress)
            or not 0 <= progress <= 100
        ):
            raise ValueError("queue task progress is invalid")
        return DownloadTask(
            task_id=task_id,
            request=request,
            state=state,
            title=text_value("title", "", 500),
            progress=float(progress),
            output_path=text_value("output_path", "", 32_767),
            error=text_value("error", "", 4096),
        )

    def _persist(self) -> None:
        with self._lock:
            self._persist_locked()

    def _persist_locked(self) -> None:
        if self.state_path is None:
            return
        payload = [
            {
                "task_id": task.task_id,
                "url": task.request.url,
                "output_dir": str(task.request.output_dir),
                "priority": task.request.priority,
                "start_time": task.request.start_time,
                "end_time": task.request.end_time,
                "source_video_id": task.request.source_video_id,
                "source_title": task.request.source_title,
                "source_artist": task.request.source_artist,
                "source_language": task.request.source_language,
                "source_category": task.request.source_category,
                "output_filename": task.request.output_filename,
                "audio_only": task.request.audio_only,
                "format_preset": task.request.format_preset,
                "subtitle_mode": task.request.subtitle_mode,
                "subtitle_languages": list(task.request.subtitle_languages),
                "timed_comment_mode": task.request.timed_comment_mode,
                "container_preset": task.request.container_preset,
                "state": task.state,
                "title": task.title,
                "progress": task.progress,
                "output_path": task.output_path,
                "error": task.error,
            }
            for task in self._tasks.values()
        ]
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(
            f".{self.state_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.state_path)
        finally:
            if temporary.exists() and temporary.parent == self.state_path.parent:
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def _notify(self, task: DownloadTask) -> None:
        snapshot = replace(task)
        for listener in tuple(self._listeners):
            try:
                listener(snapshot)
            except Exception:
                continue

