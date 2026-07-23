"""Deterministic, local-only resource baseline for Development G39.

The benchmark deliberately exercises only MediaManager's durable queue.  It
does not start a provider, open a GUI, read UserData, or perform network I/O.
Results are returned to the caller and the CLI emits a single JSON document;
the tool never writes benchmark evidence back into the repository.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import ctypes
from ctypes import wintypes
import gc
import json
import math
import os
from pathlib import Path
import platform
import secrets
import shutil
import sys
import tempfile
import threading
import time
import tracemalloc
from typing import Any, Protocol

from core.downloads.models import DownloadRequest
from core.downloads.queue import DownloadQueue
from core.version import CORE_VERSION
from tools.source_fingerprint import source_fingerprint, source_revision


_SCHEMA_VERSION = 1
_WORKLOAD_ID = "queue-roundtrip-v1"
_ATTEMPT_PREFIX = "g39-"
_OWNER_MARKER = ".mediamanager-g39-owner"
_DEFAULT_TASK_COUNT = 1_001
_DEFAULT_WORKERS = 4


class _Backend(Protocol):
    def download(self, *_args: object, **_kwargs: object) -> str: ...


BackendFactory = Callable[[], _Backend]
ResourceProbe = Callable[[], dict[str, Any]]


class _BackendCallCounter:
    def __init__(self) -> None:
        self.calls = 0


class _NetworkForbiddenBackend:
    """Fail the baseline if a queue worker ever invokes a provider."""

    def __init__(self, counter: _BackendCallCounter) -> None:
        self._counter = counter

    def download(self, *_args: object, **_kwargs: object) -> str:
        self._counter.calls += 1
        raise AssertionError("G39 baseline must not invoke a download backend")


def nearest_rank(values: list[int | float], percentile: float) -> int | float:
    """Return the documented nearest-rank percentile for a non-empty sample."""

    if not values:
        raise ValueError("percentile sample must not be empty")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be greater than zero and at most one")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _stats(values: list[int | float], *, digits: int | None = None) -> dict[str, Any]:
    def normalize(value: int | float) -> int | float:
        if digits is None:
            return int(value)
        return round(float(value), digits)

    return {
        "p50": normalize(nearest_rank(values, 0.50)),
        "p95": normalize(nearest_rank(values, 0.95)),
        "max": normalize(max(values)),
    }


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve(strict=False)
    second = second.resolve(strict=False)
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def _existing_components(path: Path) -> tuple[Path, ...]:
    components = tuple(reversed(path.parents)) + (path,)
    return tuple(component for component in components if component.exists())


def default_temp_root(environment: Mapping[str, str] | None = None) -> Path:
    """Return the dedicated benchmark root without falling back to TEMP/TMP."""

    values = os.environ if environment is None else environment
    local_app_data = values.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError(
            "LOCALAPPDATA is unavailable; provide an explicit --temp-root"
        )
    return Path(local_app_data) / "MediaManager-BenchmarkRuns"


def validate_temp_root(temp_root: Path, repository_root: Path) -> Path:
    """Create and return a non-reparse root that cannot overlap the repository."""

    candidate = Path(os.path.abspath(temp_root.expanduser()))
    repository = repository_root.resolve()
    if _paths_overlap(candidate, repository):
        raise ValueError("benchmark temp root must not overlap the repository")
    if any(_is_linklike(component) for component in _existing_components(candidate)):
        raise ValueError(
            "benchmark temp root must not use a symbolic link or junction"
        )
    candidate.mkdir(parents=True, exist_ok=True)
    if _is_linklike(candidate):
        raise ValueError(
            "benchmark temp root must not use a symbolic link or junction"
        )
    resolved = candidate.resolve()
    if _paths_overlap(resolved, repository):
        raise ValueError("benchmark temp root must not overlap the repository")
    return resolved


def _create_owned_attempt(temp_root: Path) -> tuple[Path, str]:
    token = secrets.token_hex(32)
    attempt = Path(tempfile.mkdtemp(prefix=_ATTEMPT_PREFIX, dir=temp_root))
    try:
        if attempt.parent != temp_root or not attempt.name.startswith(_ATTEMPT_PREFIX):
            raise RuntimeError("owned benchmark attempt escaped its temp root")
        (attempt / _OWNER_MARKER).write_text(token, encoding="ascii")
    except BaseException as create_error:
        if (
            attempt.parent != temp_root
            or not attempt.name.startswith(_ATTEMPT_PREFIX)
            or _is_linklike(attempt)
        ):
            raise RuntimeError(
                "refusing to discard an unsafe unmarked benchmark attempt"
            ) from create_error
        try:
            shutil.rmtree(attempt)
        except OSError as cleanup_error:
            raise RuntimeError(
                "failed to discard the unmarked benchmark attempt"
            ) from cleanup_error
        raise
    return attempt, token


def _remove_owned_attempt(attempt: Path, token: str, *, retries: int = 3) -> None:
    marker = attempt / _OWNER_MARKER
    if (
        not attempt.name.startswith(_ATTEMPT_PREFIX)
        or attempt.parent == attempt
        or _is_linklike(attempt)
    ):
        raise RuntimeError("refusing to clean an unsafe benchmark attempt")
    try:
        recorded = marker.read_text(encoding="ascii")
    except OSError as error:
        raise RuntimeError("benchmark ownership marker is missing") from error
    if not secrets.compare_digest(recorded, token):
        raise RuntimeError("benchmark ownership marker does not match")
    _tree_bytes(attempt)
    last_error: OSError | None = None
    for retry in range(retries):
        try:
            shutil.rmtree(attempt)
            return
        except OSError as error:
            last_error = error
            if retry + 1 < retries:
                time.sleep(0.1 * (retry + 1))
    raise RuntimeError("failed to clean the owned benchmark attempt") from last_error


def _tree_bytes(root: Path) -> int:
    total = 0
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in names:
            if _is_linklike(directory_path / name):
                raise RuntimeError("benchmark output contains a reparse directory")
        for name in filenames:
            child = directory_path / name
            if _is_linklike(child) or not child.is_file():
                raise RuntimeError("benchmark output contains an unsafe file")
            total += child.stat().st_size
    return total


class _ThreadEntry32(ctypes.Structure):
    _fields_ = (
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    )


_ERROR_NO_MORE_FILES = 18


def _count_process_threads(kernel32: Any, snapshot: Any, process_id: int) -> int:
    entry = _ThreadEntry32()
    entry.dwSize = ctypes.sizeof(entry)
    count = 0
    enumeration_error: BaseException | None = None
    try:
        ctypes.set_last_error(0)
        found = bool(kernel32.Thread32First(snapshot, ctypes.byref(entry)))
        if not found:
            error_code = ctypes.get_last_error()
            if error_code != _ERROR_NO_MORE_FILES:
                raise OSError(error_code, "Thread32First failed")
            return 0
        while True:
            if entry.th32OwnerProcessID == process_id:
                count += 1
            ctypes.set_last_error(0)
            if kernel32.Thread32Next(snapshot, ctypes.byref(entry)):
                continue
            error_code = ctypes.get_last_error()
            if error_code != _ERROR_NO_MORE_FILES:
                raise OSError(error_code, "Thread32Next failed")
            return count
    except BaseException as error:
        enumeration_error = error
        raise
    finally:
        ctypes.set_last_error(0)
        if not kernel32.CloseHandle(snapshot) and enumeration_error is None:
            raise OSError(ctypes.get_last_error(), "CloseHandle failed")


def windows_resource_probe() -> dict[str, Any]:
    """Return current-process handle and OS-thread counts on Windows."""

    if os.name != "nt":
        return {"status": "unsupported", "handles": None, "os_threads": None}
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessHandleCount.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.GetProcessHandleCount.restype = wintypes.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = (
        wintypes.DWORD,
        wintypes.DWORD,
    )
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ThreadEntry32),
    )
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ThreadEntry32),
    )
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    handle_count = wintypes.DWORD()
    if not kernel32.GetProcessHandleCount(process, ctypes.byref(handle_count)):
        raise OSError(ctypes.get_last_error(), "GetProcessHandleCount failed")

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot == invalid_handle:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    count = _count_process_threads(kernel32, snapshot, os.getpid())
    return {
        "status": "supported",
        "handles": int(handle_count.value),
        "os_threads": count,
    }


def _download_thread_count() -> int:
    return sum(
        1
        for thread in threading.enumerate()
        if thread.is_alive() and thread.name.startswith("download-")
    )


def _resource_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> int | None:
    if before.get("status") != "supported" or after.get("status") != "supported":
        return None
    return int(after[key]) - int(before[key])


def _run_sample(
    sample_root: Path,
    *,
    task_count: int,
    workers: int,
    backend_factory: BackendFactory,
    resource_probe: ResourceProbe,
) -> dict[str, Any]:
    sample_root.mkdir()
    state_path = sample_root / "queue.json"
    output_dir = sample_root / "outputs"
    before = resource_probe()
    checkpoints: list[int] = []
    empty_queue: DownloadQueue | None = None
    empty_queue_stopped = False
    started_tracing = not tracemalloc.is_tracing()
    if started_tracing:
        tracemalloc.start()
    try:
        total_started = time.perf_counter_ns()
        requests = [
            DownloadRequest(
                f"https://example.invalid/mediamanager-g39/{index}",
                output_dir,
            )
            for index in range(task_count)
        ]
        original = DownloadQueue(backend_factory(), state_path=state_path)
        persist_started = time.perf_counter_ns()
        original.add_batch(requests)
        persist_ns = time.perf_counter_ns() - persist_started
        checkpoints.append(_tree_bytes(sample_root))

        restore_started = time.perf_counter_ns()
        restored = DownloadQueue(backend_factory(), state_path=state_path)
        restored_count = len(restored.snapshots())
        restore_ns = time.perf_counter_ns() - restore_started
        if restored_count != task_count:
            raise RuntimeError("queue round-trip restored an unexpected task count")
        checkpoints.append(_tree_bytes(sample_root))

        empty_queue = DownloadQueue(backend_factory(), workers=workers)
        lifecycle_started = time.perf_counter_ns()
        empty_queue.start()
        empty_queue.shutdown()
        empty_queue_stopped = True
        lifecycle_ns = time.perf_counter_ns() - lifecycle_started
        total_ns = time.perf_counter_ns() - total_started
        _current, memory_peak = tracemalloc.get_traced_memory()
    finally:
        active_error = sys.exception()
        cleanup_error: Exception | None = None
        if empty_queue is not None and not empty_queue_stopped:
            try:
                empty_queue.shutdown()
            except Exception as error:
                cleanup_error = error
        if started_tracing and tracemalloc.is_tracing():
            tracemalloc.stop()
        if cleanup_error is not None and active_error is None:
            raise cleanup_error

    del requests, original, restored, empty_queue
    gc.collect()
    after = resource_probe()
    return {
        "persist_ns": persist_ns,
        "restore_snapshot_ns": restore_ns,
        "worker_lifecycle_ns": lifecycle_ns,
        "total_ns": total_ns,
        "memory_peak_bytes": memory_peak,
        "temp_checkpoint_high_water_bytes": max(checkpoints, default=0),
        "handle_delta": _resource_delta(before, after, "handles"),
        "os_thread_delta": _resource_delta(before, after, "os_threads"),
        "download_threads_after": _download_thread_count(),
        "resource_status": (
            "supported"
            if before.get("status") == after.get("status") == "supported"
            else "unsupported"
        ),
    }


def _cleanup_sample(sample_root: Path, attempt: Path) -> None:
    if sample_root.parent != attempt or _is_linklike(sample_root):
        raise RuntimeError("refusing to clean an unsafe benchmark sample")
    _tree_bytes(sample_root)
    shutil.rmtree(sample_root)


def run_baseline(
    *,
    repository_root: Path,
    temp_root: Path | None = None,
    warmups: int = 2,
    iterations: int = 20,
    task_count: int = _DEFAULT_TASK_COUNT,
    workers: int = _DEFAULT_WORKERS,
    resource_probe: ResourceProbe = windows_resource_probe,
) -> dict[str, Any]:
    """Run the local queue workload and return a JSON-serializable report."""

    if not 0 <= warmups <= 20:
        raise ValueError("warmups must be between 0 and 20")
    if not 1 <= iterations <= 100:
        raise ValueError("iterations must be between 1 and 100")
    if not 1 <= task_count <= _DEFAULT_TASK_COUNT:
        raise ValueError("task_count must be between 1 and 1001")
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")

    repository = repository_root.resolve()
    benchmark_root = validate_temp_root(
        default_temp_root() if temp_root is None else temp_root,
        repository,
    )
    backend_counter = _BackendCallCounter()

    def backend_factory() -> _NetworkForbiddenBackend:
        return _NetworkForbiddenBackend(backend_counter)

    attempt, token = _create_owned_attempt(benchmark_root)
    samples: list[dict[str, Any]] = []
    cleanup_succeeded = False
    try:
        for index in range(warmups + iterations):
            sample_root = attempt / f"sample-{index + 1:03d}"
            sample = _run_sample(
                sample_root,
                task_count=task_count,
                workers=workers,
                backend_factory=backend_factory,
                resource_probe=resource_probe,
            )
            _cleanup_sample(sample_root, attempt)
            if index >= warmups:
                samples.append(sample)
    finally:
        _remove_owned_attempt(attempt, token)
        cleanup_succeeded = not attempt.exists()

    if backend_counter.calls:
        raise RuntimeError("G39 baseline invoked its forbidden download backend")

    timing: dict[str, dict[str, Any]] = {}
    for output_name, sample_name in (
        ("persist", "persist_ns"),
        ("restore_snapshot", "restore_snapshot_ns"),
        ("worker_lifecycle", "worker_lifecycle_ns"),
        ("total", "total_ns"),
    ):
        timing[output_name] = _stats(
            [sample[sample_name] / 1_000_000 for sample in samples],
            digits=3,
        )

    supported = all(sample["resource_status"] == "supported" for sample in samples)
    resources: dict[str, Any] = {"status": "supported" if supported else "unsupported"}
    if supported:
        resources["handle_delta"] = _stats(
            [sample["handle_delta"] for sample in samples]
        )
        resources["os_thread_delta"] = _stats(
            [sample["os_thread_delta"] for sample in samples]
        )
    else:
        resources.update({"handle_delta": None, "os_thread_delta": None})

    return {
        "schema_version": _SCHEMA_VERSION,
        "result": "BASELINE_RECORDED",
        "workload": {
            "id": _WORKLOAD_ID,
            "warmups": warmups,
            "iterations": iterations,
            "tasks": task_count,
            "workers": workers,
            "restored_tasks_per_sample": task_count,
        },
        "source": {
            "core_version": CORE_VERSION,
            "fingerprint_sha256": source_fingerprint(repository),
            "revision": source_revision(repository),
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
        },
        "timing_ms": timing,
        "tracemalloc_peak_bytes": _stats(
            [sample["memory_peak_bytes"] for sample in samples]
        ),
        "process_resources": resources,
        "temp_bytes": {
            "measurement": "owned-tree checkpoint high-water; not OS instantaneous peak",
            **_stats(
                [sample["temp_checkpoint_high_water_bytes"] for sample in samples]
            ),
            "owned_attempt_removed": cleanup_succeeded,
        },
        "safety": {
            "network_backend_calls": backend_counter.calls,
            "gui_used": False,
            "user_data_read": False,
            "download_threads_after_max": max(
                sample["download_threads_after"] for sample in samples
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record the local-only Development G39 queue baseline."
    )
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="Dedicated writable root outside the repository (default: LOCALAPPDATA).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    try:
        report = run_baseline(
            repository_root=repository,
            temp_root=arguments.temp_root,
            warmups=arguments.warmups,
            iterations=arguments.iterations,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"G39 baseline failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
