from __future__ import annotations

import ctypes
import os
from pathlib import Path
import tracemalloc

import pytest

from tools import g39_baseline


class SequenceProbe:
    def __init__(self) -> None:
        self.index = 0

    def __call__(self) -> dict[str, object]:
        pair = self.index // 2
        after = self.index % 2
        self.index += 1
        return {
            "status": "supported",
            "handles": 100 + pair + after,
            "os_threads": 8 + pair,
        }


def test_nearest_rank_uses_documented_rule() -> None:
    values = [4, 1, 3, 2]

    assert g39_baseline.nearest_rank(values, 0.50) == 2
    assert g39_baseline.nearest_rank(values, 0.95) == 4
    assert g39_baseline.nearest_rank([7], 0.50) == 7


def test_small_injected_workload_is_local_and_cleans_owned_attempt(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    temp_root = tmp_path / "benchmarks"
    sibling = temp_root / "keep.txt"
    temp_root.mkdir()
    sibling.write_text("owned by somebody else", encoding="utf-8")
    report = g39_baseline.run_baseline(
        repository_root=repository,
        temp_root=temp_root,
        warmups=0,
        iterations=2,
        task_count=11,
        workers=2,
        resource_probe=SequenceProbe(),
    )

    assert report["schema_version"] == 1
    assert report["workload"] == {
        "id": "queue-roundtrip-v1",
        "warmups": 0,
        "iterations": 2,
        "tasks": 11,
        "workers": 2,
        "restored_tasks_per_sample": 11,
    }
    assert report["process_resources"]["handle_delta"] == {
        "p50": 1,
        "p95": 1,
        "max": 1,
    }
    assert report["process_resources"]["os_thread_delta"] == {
        "p50": 0,
        "p95": 0,
        "max": 0,
    }
    assert report["safety"]["network_backend_calls"] == 0
    assert report["safety"]["download_threads_after_max"] == 0
    assert report["temp_bytes"]["owned_attempt_removed"] is True
    assert sibling.read_text(encoding="utf-8") == "owned by somebody else"
    assert not any(path.name.startswith("g39-") for path in temp_root.iterdir())


def test_repository_overlap_is_rejected_before_writing(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    repository.mkdir()

    with pytest.raises(ValueError, match="must not overlap"):
        g39_baseline.run_baseline(
            repository_root=repository,
            temp_root=repository / "benchmark",
            warmups=0,
            iterations=1,
            task_count=1,
        )

    assert not (repository / "benchmark").exists()


def test_linklike_temp_root_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    temp_root = tmp_path / "linklike"
    temp_root.mkdir()
    original = g39_baseline._is_linklike
    monkeypatch.setattr(
        g39_baseline,
        "_is_linklike",
        lambda path: path == temp_root or original(path),
    )

    with pytest.raises(ValueError, match="symbolic link or junction"):
        g39_baseline.validate_temp_root(temp_root, repository)


def test_default_temp_root_never_falls_back_to_temp(tmp_path: Path) -> None:
    environment = {
        "TEMP": str(tmp_path / "temp"),
        "TMP": str(tmp_path / "tmp"),
    }

    with pytest.raises(RuntimeError, match="LOCALAPPDATA is unavailable"):
        g39_baseline.default_temp_root(environment)


def test_owner_marker_failure_removes_unmarked_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temp_root = tmp_path / "benchmarks"
    temp_root.mkdir()
    original_write_text = Path.write_text

    def fail_owner_marker(path: Path, *args: object, **kwargs: object) -> int:
        if path.name == g39_baseline._OWNER_MARKER:
            raise OSError("marker write failed")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_owner_marker)

    with pytest.raises(OSError, match="marker write failed"):
        g39_baseline._create_owned_attempt(temp_root)

    assert not any(path.name.startswith("g39-") for path in temp_root.iterdir())


def test_sample_failure_stops_tracing_and_partial_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    temp_root = tmp_path / "benchmarks"
    original_start = g39_baseline.DownloadQueue.start

    def start_then_fail(queue: g39_baseline.DownloadQueue) -> None:
        original_start(queue)
        raise RuntimeError("injected start failure")

    assert not tracemalloc.is_tracing()
    monkeypatch.setattr(g39_baseline.DownloadQueue, "start", start_then_fail)

    with pytest.raises(RuntimeError, match="injected start failure"):
        g39_baseline.run_baseline(
            repository_root=repository,
            temp_root=temp_root,
            warmups=0,
            iterations=1,
            task_count=3,
            workers=2,
            resource_probe=SequenceProbe(),
        )

    assert not tracemalloc.is_tracing()
    assert g39_baseline._download_thread_count() == 0
    assert not any(path.name.startswith("g39-") for path in temp_root.iterdir())


def test_forbidden_backend_counts_attempted_invocations() -> None:
    counter = g39_baseline._BackendCallCounter()
    backend = g39_baseline._NetworkForbiddenBackend(counter)

    with pytest.raises(AssertionError, match="must not invoke"):
        backend.download()

    assert counter.calls == 1


class _FakeWinFunction:
    def __init__(self, result: bool, error_code: int) -> None:
        self.result = result
        self.error_code = error_code

    def __call__(self, *_args: object) -> bool:
        ctypes.set_last_error(self.error_code)
        return self.result


class _FakeKernel32:
    def __init__(
        self,
        *,
        first_result: bool,
        first_error: int,
        close_result: bool,
        close_error: int,
    ) -> None:
        self.Thread32First = _FakeWinFunction(first_result, first_error)
        self.Thread32Next = _FakeWinFunction(False, g39_baseline._ERROR_NO_MORE_FILES)
        self.CloseHandle = _FakeWinFunction(close_result, close_error)


@pytest.mark.skipif(os.name != "nt", reason="Win32 resource probe")
def test_thread_probe_rejects_thread32first_failure() -> None:
    kernel32 = _FakeKernel32(
        first_result=False,
        first_error=5,
        close_result=True,
        close_error=0,
    )

    with pytest.raises(OSError, match="Thread32First failed"):
        g39_baseline._count_process_threads(kernel32, 1, os.getpid())


@pytest.mark.skipif(os.name != "nt", reason="Win32 resource probe")
def test_thread_probe_rejects_close_handle_failure() -> None:
    kernel32 = _FakeKernel32(
        first_result=False,
        first_error=g39_baseline._ERROR_NO_MORE_FILES,
        close_result=False,
        close_error=6,
    )

    with pytest.raises(OSError, match="CloseHandle failed"):
        g39_baseline._count_process_threads(kernel32, 1, os.getpid())


@pytest.mark.skipif(os.name != "nt", reason="Win32 resource probe")
def test_windows_resource_probe_returns_non_negative_counts() -> None:
    result = g39_baseline.windows_resource_probe()

    assert result["status"] == "supported"
    assert int(result["handles"]) >= 0
    assert int(result["os_threads"]) >= 1
