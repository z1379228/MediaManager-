"""Record isolated, no-network startup, host and trusted-UI baselines."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import ctypes
from ctypes import wintypes
import io
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from typing import Any


_SCHEMA_VERSION = 1
_MARKER = "__MEDIAMANAGER_STARTUP_BASELINE__="
_ROLES = (
    "version",
    "verify-only",
    "provider-host",
    "plugin-host",
    "gui-lazy",
    "gui-materialized",
    "table-rebuild",
    "table-reuse",
)
_EXPECTED_EXIT_CODES = {
    "version": frozenset({0}),
    "verify-only": frozenset({0, 2}),
    "provider-host": frozenset({1}),
    "plugin-host": frozenset({0}),
    "gui-lazy": frozenset({0}),
    "gui-materialized": frozenset({0}),
    "table-rebuild": frozenset({0}),
    "table-reuse": frozenset({0}),
}

_DEFERRED_WORKSPACE_MODULES = frozenset(
    {
        "trusted_ui.automation_panel",
        "trusted_ui.conversion_panel",
        "trusted_ui.direct_http_workspace",
        "trusted_ui.library_panel",
        "trusted_ui.mega_workspace",
        "trusted_ui.official_social_workspace",
        "trusted_ui.search_panel",
        "trusted_ui.transcription_panel",
        "trusted_ui.transfer_panel",
    }
)


class _ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = (
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    )


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


def nearest_rank(values: Sequence[int | float], percentile: float) -> int | float:
    if not values:
        raise ValueError("percentile sample must not be empty")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be greater than zero and at most one")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _stats(values: Sequence[int | float], *, digits: int | None = None) -> dict[str, Any]:
    def normalize(value: int | float) -> int | float:
        return int(value) if digits is None else round(float(value), digits)

    return {
        "p50": normalize(nearest_rank(values, 0.50)),
        "p95": normalize(nearest_rank(values, 0.95)),
        "max": normalize(max(values)),
    }


def _windows_thread_count(kernel32: Any, process_id: int) -> int:
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
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
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    entry = _ThreadEntry32()
    entry.dwSize = ctypes.sizeof(entry)
    count = 0
    try:
        found = bool(kernel32.Thread32First(snapshot, ctypes.byref(entry)))
        while found:
            if entry.th32OwnerProcessID == process_id:
                count += 1
            found = bool(kernel32.Thread32Next(snapshot, ctypes.byref(entry)))
    finally:
        kernel32.CloseHandle(snapshot)
    return count


def _windows_process_metrics() -> dict[str, Any]:
    if os.name != "nt":
        return {
            "status": "unsupported",
            "private_bytes": None,
            "working_set_bytes": None,
            "peak_working_set_bytes": None,
            "os_threads": None,
        }
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCountersEx),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = _ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    process = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(
        process,
        ctypes.byref(counters),
        counters.cb,
    ):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return {
        "status": "supported",
        "private_bytes": int(counters.PrivateUsage),
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        "os_threads": _windows_thread_count(kernel32, os.getpid()),
    }


def _install_network_guard() -> list[str]:
    attempts: list[str] = []
    original_socket = socket.socket

    class GuardedSocket(original_socket):
        def connect(self, address: object) -> None:
            attempts.append("connect")
            raise RuntimeError("startup baseline forbids network access")

        def connect_ex(self, address: object) -> int:
            attempts.append("connect_ex")
            raise RuntimeError("startup baseline forbids network access")

    def blocked_create_connection(*_args: object, **_kwargs: object) -> None:
        attempts.append("create_connection")
        raise RuntimeError("startup baseline forbids network access")

    socket.socket = GuardedSocket
    socket.create_connection = blocked_create_connection
    return attempts


def _application_arguments(role: str, repository: Path, runtime_root: Path) -> list[str]:
    if role == "version":
        return ["--version"]
    if role == "verify-only":
        return ["--verify-only"]
    if role == "provider-host":
        return [
            "--provider-host",
            str(repository / "mod" / "builtin" / "youtube" / "provider.py"),
            "--provider-root",
            str(repository / "mod" / "builtin"),
        ]
    if role == "plugin-host":
        return [
            "--plugin-host",
            "--plugin-id",
            "benchmark.plugin",
            "--plugin-root",
            str(runtime_root / "plugin"),
            "--entry-point",
            "plugin.py",
            "--nonce",
            "benchmark-runtime-nonce-0001",
        ]
    raise ValueError(f"unsupported startup role: {role}")


def _run_gui_workload(role: str) -> tuple[int, dict[str, Any]]:
    from core.bootstrap.bootstrap import Bootstrap
    from PySide6.QtCore import QObject, QTimer
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
    from trusted_ui.main_window import run_main_window

    app = QApplication.instance() or QApplication([])
    context = Bootstrap().initialize(start_background=False)
    observed: dict[str, Any] = {}

    def inspect_then_exit(_app: QApplication) -> int:
        app.processEvents()
        window = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QMainWindow)
            and widget.accessibleName() == "MediaManager 主視窗"
        )
        tabs = window.findChild(QTabWidget, "workspaceTabs")
        if role == "gui-materialized":
            for index in range(tabs.count()):
                tabs.setCurrentIndex(index)
                app.processEvents()
            tabs.setCurrentIndex(0)
            app.processEvents()
        observed.update(
            qt_objects=len(window.findChildren(QObject)),
            active_repeat_timers=sum(
                timer.isActive() and not timer.isSingleShot()
                for timer in window.findChildren(QTimer)
            ),
            tabs=tabs.count(),
            materialized_workspaces=(
                len(window.core_workspace_manager.panels)
                + len(window.optional_workspace_manager.panels)
            ),
            loaded_deferred_modules=sum(
                name in sys.modules for name in _DEFERRED_WORKSPACE_MODULES
            ),
        )
        window.request_full_exit()
        app.processEvents()
        return 0

    original_exec = QApplication.exec
    QApplication.exec = inspect_then_exit
    try:
        result = run_main_window(context)
    finally:
        QApplication.exec = original_exec
        context.lifecycle.shutdown()
    return result, observed


def _run_table_workload(role: str) -> tuple[int, dict[str, Any]]:
    """Apply the same changing snapshot through rebuild and reuse strategies."""

    from PySide6.QtCore import QCoreApplication, QEvent, QObject
    from PySide6.QtWidgets import (
        QApplication,
        QProgressBar,
        QTableWidget,
        QTableWidgetItem,
    )
    from trusted_ui.table_refresh import suspended_table_updates

    if role not in {"table-rebuild", "table-reuse"}:
        raise ValueError(f"unsupported table role: {role}")
    app = QApplication.instance() or QApplication([])
    row_count = 200
    refresh_iterations = 50
    table = QTableWidget(0, 5)
    item_allocations = 0
    progress_allocations = 0
    started = time.perf_counter_ns()
    for iteration in range(refresh_iterations):
        with suspended_table_updates(table):
            table.setRowCount(row_count)
            for row in range(row_count):
                progress_value = (iteration * 17 + row) % 1001
                values = (
                    f"task-{row}",
                    "running",
                    f"{progress_value / 10:.1f} KiB/s",
                    f"{max(0, 200 - row)} s",
                )
                if role == "table-rebuild":
                    for column, value in enumerate(values):
                        table.setItem(row, column, QTableWidgetItem(value))
                    progress = QProgressBar(table)
                    progress.setRange(0, 1000)
                    progress.setValue(progress_value)
                    progress.setFormat(f"{progress_value / 10:.1f}%")
                    table.setCellWidget(row, 4, progress)
                    item_allocations += len(values)
                    progress_allocations += 1
                else:
                    for column, value in enumerate(values):
                        item = table.item(row, column)
                        if item is None:
                            item = QTableWidgetItem()
                            table.setItem(row, column, item)
                            item_allocations += 1
                        if item.text() != value:
                            item.setText(value)
                    progress = table.cellWidget(row, 4)
                    if not isinstance(progress, QProgressBar):
                        progress = QProgressBar(table)
                        progress.setRange(0, 1000)
                        table.setCellWidget(row, 4, progress)
                        progress_allocations += 1
                    if progress.value() != progress_value:
                        progress.setValue(progress_value)
                    progress_text = f"{progress_value / 10:.1f}%"
                    if progress.format() != progress_text:
                        progress.setFormat(progress_text)
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    observed = {
        "table_workload_ms": round(elapsed_ms, 3),
        "rendered_rows": row_count,
        "refresh_iterations": refresh_iterations,
        "item_allocations": item_allocations,
        "progress_allocations": progress_allocations,
        "table_qt_objects": len(table.findChildren(QObject)),
    }
    table.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    return 0, observed


def _run_probe(role: str, repository: Path, runtime_root: Path) -> int:
    if role not in _ROLES:
        return 2
    attempts = _install_network_guard()
    sys.path.insert(0, str(repository))
    # AppPaths intentionally derives the application bundle root from argv[0].
    # The probe runs as a tools module, so point it at the real entry script to
    # prevent verify-only from provisioning bundled MODs below ``tools/``.
    try:
        original_argv0 = sys.argv[0]
        original_stdin = sys.stdin
        sys.argv[0] = str(repository / "main.py")
        extra: dict[str, Any] = {}
        if role.startswith("gui-"):
            result, extra = _run_gui_workload(role)
        elif role.startswith("table-"):
            result, extra = _run_table_workload(role)
        else:
            import main as application

            if role == "provider-host":
                sys.stdin = io.TextIOWrapper(io.BytesIO(b"{}\n"), encoding="utf-8")
            elif role == "plugin-host":
                sys.stdin = io.StringIO("")
            try:
                result = application.main(
                    _application_arguments(role, repository, runtime_root)
                )
            except SystemExit as error:
                result = error.code
        exit_code = result if isinstance(result, int) else (1 if result else 0)
        payload = {
            "app_exit_code": exit_code,
            "cpu_time_ms": round(time.process_time() * 1_000, 3),
            "network_attempts": list(attempts),
            "graphical_shell_loaded": "trusted_ui.main_window" in sys.modules,
            **_windows_process_metrics(),
            **extra,
        }
        print(
            _MARKER + json.dumps(payload, sort_keys=True),
            file=sys.stderr,
            flush=True,
        )
        return 0
    finally:
        sys.argv[0] = original_argv0
        sys.stdin = original_stdin


SampleRunner = Callable[[str, Path, Path, dict[str, str]], dict[str, Any]]


def _run_role_sample(
    role: str,
    repository: Path,
    runtime_root: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    interpreter = Path(getattr(sys, "_base_executable", sys.executable))
    command = (
        str(interpreter),
        "-B",
        "-m",
        "tools.startup_baseline",
        "--_probe",
        role,
        str(repository),
        str(runtime_root),
    )
    started = time.perf_counter_ns()
    completed = subprocess.run(
        command,
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    marker_line = next(
        (line for line in reversed(completed.stderr.splitlines()) if line.startswith(_MARKER)),
        None,
    )
    if completed.returncode != 0 or marker_line is None:
        raise RuntimeError(f"startup probe failed for role {role}")
    payload = json.loads(marker_line.removeprefix(_MARKER))
    if payload["app_exit_code"] not in _EXPECTED_EXIT_CODES[role]:
        raise RuntimeError(f"startup role returned an unexpected code: {role}")
    if payload["network_attempts"]:
        raise RuntimeError(f"startup role attempted network access: {role}")
    expected_graphical_shell = role.startswith("gui-")
    if payload["graphical_shell_loaded"] is not expected_graphical_shell:
        raise RuntimeError(f"startup role loaded an unexpected shell: {role}")
    payload["elapsed_ms"] = round(elapsed_ms, 3)
    return payload


def _role_summary(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "samples": len(samples),
        "elapsed_ms": _stats([sample["elapsed_ms"] for sample in samples], digits=3),
        "cpu_time_ms": _stats([sample["cpu_time_ms"] for sample in samples], digits=3),
        "app_exit_codes": sorted({sample["app_exit_code"] for sample in samples}),
    }
    if all(sample["status"] == "supported" for sample in samples):
        summary["process"] = {
            "status": "supported",
            "private_bytes": _stats([sample["private_bytes"] for sample in samples]),
            "working_set_bytes": _stats(
                [sample["working_set_bytes"] for sample in samples]
            ),
            "peak_working_set_bytes": _stats(
                [sample["peak_working_set_bytes"] for sample in samples]
            ),
            "os_threads": _stats([sample["os_threads"] for sample in samples]),
        }
    else:
        summary["process"] = {"status": "unsupported"}
    gui_metrics = (
        "qt_objects",
        "active_repeat_timers",
        "tabs",
        "materialized_workspaces",
        "loaded_deferred_modules",
    )
    if all(all(metric in sample for metric in gui_metrics) for sample in samples):
        summary["gui"] = {
            metric: _stats([sample[metric] for sample in samples])
            for metric in gui_metrics
        }
    table_metrics = (
        "table_workload_ms",
        "rendered_rows",
        "refresh_iterations",
        "item_allocations",
        "progress_allocations",
        "table_qt_objects",
    )
    if all(all(metric in sample for metric in table_metrics) for sample in samples):
        summary["table"] = {
            metric: _stats(
                [sample[metric] for sample in samples],
                digits=3 if metric == "table_workload_ms" else None,
            )
            for metric in table_metrics
        }
    return summary


def run_baseline(
    *,
    repository_root: Path,
    temp_root: Path | None = None,
    warmups: int = 2,
    iterations: int = 7,
    roles: Sequence[str] = _ROLES,
    sample_runner: SampleRunner | None = None,
) -> dict[str, Any]:
    if not 0 <= warmups <= 10:
        raise ValueError("warmups must be between 0 and 10")
    if not 1 <= iterations <= 50:
        raise ValueError("iterations must be between 1 and 50")
    if not roles or any(role not in _ROLES for role in roles):
        raise ValueError("startup baseline role is invalid")
    from tools.g39_baseline import (
        _create_owned_attempt,
        _remove_owned_attempt,
        default_temp_root,
        validate_temp_root,
    )

    repository = repository_root.resolve()
    benchmark_root = validate_temp_root(
        default_temp_root() if temp_root is None else temp_root,
        repository,
    )
    attempt, token = _create_owned_attempt(benchmark_root)
    runner = _run_role_sample if sample_runner is None else sample_runner
    recorded: dict[str, list[dict[str, Any]]] = {role: [] for role in roles}
    try:
        plugin_root = attempt / "plugin"
        runtime_root = attempt / "runtime"
        plugin_root.mkdir()
        runtime_root.mkdir()
        (plugin_root / "plugin.py").write_text(
            "def handle_request(request):\n    return {}\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment.update(
            {
                "APPDATA": str(runtime_root / "Roaming"),
                "LOCALAPPDATA": str(runtime_root / "Local"),
                "TEMP": str(runtime_root / "Temp"),
                "TMP": str(runtime_root / "Temp"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "QT_QPA_PLATFORM": "offscreen",
            }
        )
        for name in ("Roaming", "Local", "Temp"):
            (runtime_root / name).mkdir()
        for role in roles:
            for index in range(warmups + iterations):
                sample = runner(role, repository, attempt, environment)
                if index >= warmups:
                    recorded[role].append(sample)
    finally:
        _remove_owned_attempt(attempt, token)
    from core.version import CORE_VERSION
    from tools.source_fingerprint import source_fingerprint, source_revision

    return {
        "schema_version": _SCHEMA_VERSION,
        "result": "BASELINE_RECORDED",
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
        "workload": {
            "warmups": warmups,
            "iterations": iterations,
            "network_allowed": False,
            "visible_ui_allowed": False,
            "user_data_isolated": True,
        },
        "roles": {role: _role_summary(recorded[role]) for role in roles},
    }


def validate_output_path(output: Path, repository: Path) -> Path:
    from tools.g39_baseline import _existing_components, _is_linklike, _paths_overlap

    candidate = Path(os.path.abspath(output.expanduser()))
    if _paths_overlap(candidate, repository.resolve()):
        raise ValueError("baseline evidence must be written outside the repository")
    if any(_is_linklike(component) for component in _existing_components(candidate.parent)):
        raise ValueError("baseline evidence path must not use a link or junction")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if candidate.exists():
        raise FileExistsError("baseline evidence already exists")
    return candidate


def write_report(report: dict[str, Any], output: Path, repository: Path) -> Path:
    destination = validate_output_path(output, repository)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        if temporary.is_file() and temporary.parent == destination.parent:
            temporary.unlink()
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--role", action="append", choices=_ROLES)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["--_probe"]:
        if len(arguments) != 4:
            return 2
        return _run_probe(
            arguments[1],
            Path(arguments[2]).resolve(),
            Path(arguments[3]).resolve(),
        )
    parsed = _parser().parse_args(arguments)
    repository = Path(__file__).resolve().parents[1]
    try:
        report = run_baseline(
            repository_root=repository,
            temp_root=parsed.temp_root,
            warmups=parsed.warmups,
            iterations=parsed.iterations,
            roles=tuple(parsed.role or _ROLES),
        )
        output = write_report(report, parsed.output, repository)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Startup baseline failed: {error}", file=sys.stderr)
        return 2
    print(f"Startup baseline written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
