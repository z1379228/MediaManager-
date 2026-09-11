"""Build and compare isolated onefile and onedir PyInstaller prototypes.

The command is a development experiment, not a release builder.  Its default
mode only prints the plan; ``--execute`` is required before it invokes
PyInstaller.  Artifacts and JSON evidence must stay outside the repository.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.version import CORE_VERSION
from core.downloads.windows_job import ProviderJob
from tools.build_version import (
    PYINSTALLER_LAYOUT_ENVIRONMENT,
    pyinstaller_build_environment,
    validate_clean_source,
)
from tools.g39_baseline import (
    _create_owned_attempt,
    _is_linklike,
    _remove_owned_attempt,
    default_temp_root,
    validate_temp_root,
)
from tools.source_fingerprint import source_fingerprint
from tools.startup_baseline import (
    _ProcessMemoryCountersEx,
    _stats,
    _windows_thread_count,
    validate_output_path,
    write_report,
)


SCHEMA_VERSION = 1
PACKAGE_LAYOUTS = ("onefile", "onedir")
BENCHMARK_ROLES = ("version", "verify-only", "provider-host")
_MAX_TREE_FILES = 200_000
_MAX_TREE_BYTES = 8 * 1024 * 1024 * 1024
_CREATE_SUSPENDED = 0x00000004


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    files: int
    bytes: int
    manifest_sha256: str


BuildRunner = Callable[..., subprocess.CompletedProcess[Any]]
SampleRunner = Callable[..., dict[str, Any]]
SourceValidator = Callable[[Path], str]


def package_layout_plan(repository_root: Path) -> dict[str, Any]:
    """Return the side-effect-free experiment plan."""

    root = repository_root.resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "result": "BUILD_NOT_EXECUTED",
        "repository": str(root),
        "layouts": list(PACKAGE_LAYOUTS),
        "release_builder_layout": "onefile",
        "build_environment": PYINSTALLER_LAYOUT_ENVIRONMENT,
        "roles": list(BENCHMARK_ROLES),
        "execute_required": True,
        "writes_inside_repository": False,
    }


def pyinstaller_command(
    pyinstaller: Path,
    repository_root: Path,
    build_root: Path,
) -> tuple[str, ...]:
    """Return a bounded command whose outputs stay below *build_root*."""

    return (
        str(pyinstaller),
        "--clean",
        "--noconfirm",
        "--workpath",
        str(build_root / "work"),
        "--distpath",
        str(build_root / "dist"),
        str(repository_root / "MediaManager.spec"),
    )


def artifact_paths(build_root: Path, layout: str) -> tuple[Path, Path]:
    if layout == "onefile":
        artifact_root = build_root / "dist"
    elif layout == "onedir":
        artifact_root = build_root / "dist" / "MediaManager"
    else:
        raise ValueError("package layout must be onefile or onedir")
    return artifact_root, artifact_root / "MediaManager.exe"


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot_tree(root: Path) -> tuple[FileEntry, ...]:
    """Hash a regular, non-reparse artifact tree in deterministic order."""

    if not root.is_dir() or _is_linklike(root):
        raise ValueError("artifact root is missing or link-like")
    resolved = root.resolve(strict=True)
    entries: list[FileEntry] = []
    total_bytes = 0
    for directory, names, filenames in os.walk(root, followlinks=False):
        names.sort()
        filenames.sort()
        directory_path = Path(directory)
        for name in names:
            child = directory_path / name
            if _is_linklike(child):
                raise ValueError("artifact tree contains a link-like directory")
        for name in filenames:
            child = directory_path / name
            if _is_linklike(child) or not child.is_file():
                raise ValueError("artifact tree contains a non-regular file")
            resolved_child = child.resolve(strict=True)
            if not resolved_child.is_relative_to(resolved):
                raise ValueError("artifact file escapes its root")
            size = child.stat().st_size
            total_bytes += size
            if total_bytes > _MAX_TREE_BYTES:
                raise ValueError("artifact tree exceeds the byte limit")
            entries.append(
                FileEntry(
                    child.relative_to(root).as_posix(),
                    size,
                    _sha256(child),
                )
            )
            if len(entries) > _MAX_TREE_FILES:
                raise ValueError("artifact tree exceeds the file-count limit")
    if not entries:
        raise ValueError("artifact tree is empty")
    return tuple(entries)


def artifact_identity(entries: Sequence[FileEntry]) -> ArtifactIdentity:
    if not entries:
        raise ValueError("artifact identity requires at least one file")
    digest = hashlib.sha256()
    total = 0
    for entry in entries:
        encoded_path = entry.path.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(entry.size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(entry.sha256))
        total += entry.size
    return ArtifactIdentity(len(entries), total, digest.hexdigest())


def validate_runtime_materialization(
    before: Sequence[FileEntry],
    after: Sequence[FileEntry],
    expected_hashes: Mapping[str, Mapping[str, str]] = BUILTIN_PROVIDER_HASHES,
) -> dict[str, Any]:
    """Allow only the pinned built-in MODs materialized on first verification."""

    before_by_path = {entry.path: entry for entry in before}
    after_by_path = {entry.path: entry for entry in after}
    expected = {
        f"mod/builtin/{provider_id}/{relative}": digest
        for provider_id, files in expected_hashes.items()
        for relative, digest in files.items()
    }
    changed_existing = {
        path
        for path, entry in before_by_path.items()
        if after_by_path.get(path) != entry
    }
    missing_expected = set(expected).difference(after_by_path)
    unexpected = set(after_by_path).difference(before_by_path, expected)
    mismatched = {
        path
        for path, digest in expected.items()
        if path in after_by_path and after_by_path[path].sha256 != digest
    }
    if changed_existing:
        raise RuntimeError("artifact content changed during runtime verification")
    if missing_expected:
        raise RuntimeError("runtime verification did not materialize every built-in MOD")
    if unexpected:
        raise RuntimeError("runtime verification created unexpected artifact files")
    if mismatched:
        raise RuntimeError("runtime verification materialized an invalid built-in MOD")
    added = [
        after_by_path[path]
        for path in sorted(set(after_by_path).difference(before_by_path))
    ]
    return {
        "passed": True,
        "added_files": len(added),
        "added_bytes": sum(entry.size for entry in added),
    }


def _runtime_environment(root: Path) -> dict[str, str]:
    paths = {
        "LOCALAPPDATA": root / "Local",
        "APPDATA": root / "Roaming",
        "USERPROFILE": root / "Home",
        "HOME": root / "Home",
        "TEMP": root / "Temp",
        "TMP": root / "Temp",
    }
    for path in set(paths.values()):
        path.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({name: str(path) for name, path in paths.items()})
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "QT_QPA_PLATFORM": "offscreen",
        }
    )
    return environment


def _filetime_ticks(value: wintypes.FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _windows_child_metrics(process: subprocess.Popen[str]) -> dict[str, int]:
    if os.name != "nt":
        raise OSError("Windows process metrics are unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCountersEx),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    )
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    handle = wintypes.HANDLE(int(process._handle))  # noqa: SLF001
    counters = _ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel = wintypes.FILETIME()
    user = wintypes.FILETIME()
    if not kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
    return {
        "private_bytes": int(counters.PrivateUsage),
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        "os_threads": _windows_thread_count(kernel32, process.pid),
        "cpu_time_ms": (_filetime_ticks(kernel) + _filetime_ticks(user)) // 10_000,
    }


def _resume_suspended_process(process_handle: int) -> None:
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtResumeProcess.restype = wintypes.LONG
    status = ntdll.NtResumeProcess(wintypes.HANDLE(process_handle))
    if status != 0:
        raise RuntimeError(
            f"NtResumeProcess failed with status 0x{status & 0xFFFFFFFF:08x}"
        )


def _reap_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return stdout or "", stderr or ""


def run_process_sample(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    expected_codes: frozenset[int],
    input_text: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run one bounded, non-graphical sample and capture peak process metrics."""

    if timeout <= 0 or timeout > 300:
        raise ValueError("sample timeout must be between 0 and 300 seconds")
    started = time.perf_counter_ns()
    job = ProviderJob(active_process_limit=16) if os.name == "nt" else None
    process: subprocess.Popen[str] | None = None
    observed: list[dict[str, int]] = []
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                subprocess.CREATE_NO_WINDOW | _CREATE_SUSPENDED
                if os.name == "nt"
                else 0
            ),
        )
        if job is not None:
            try:
                process_handle = int(
                    process._handle  # noqa: SLF001 - Windows Popen handle
                )
                job.assign(process_handle)
                _resume_suspended_process(process_handle)
            except Exception:
                job.close()
                if process.poll() is None:
                    process.kill()
                _reap_process(process)
                raise
        if input_text is not None and process.stdin is not None:
            process.stdin.write(input_text)
            process.stdin.close()
            process.stdin = None
        while process.poll() is None:
            if (time.perf_counter_ns() - started) / 1_000_000_000 > timeout:
                if job is not None:
                    job.close()
                if process.poll() is None:
                    process.kill()
                _reap_process(process)
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                observed.append(_windows_child_metrics(process))
            except OSError:
                pass
            time.sleep(0.005)
        stdout, stderr = _reap_process(process)
    except BaseException:
        if job is not None:
            job.close()
        if process is not None and process.poll() is None:
            process.kill()
            _reap_process(process)
        raise
    finally:
        if job is not None:
            job.close()
    if process is None:
        raise RuntimeError("startup sample process was not created")
    if len(stdout) > 64 * 1024 or len(stderr) > 64 * 1024:
        raise RuntimeError("startup sample output exceeds the safety limit")
    if process.returncode not in expected_codes:
        raise RuntimeError(
            f"startup sample returned {process.returncode}; expected "
            f"{sorted(expected_codes)}"
        )
    result: dict[str, Any] = {
        "returncode": process.returncode,
        "elapsed_ms": round(
            (time.perf_counter_ns() - started) / 1_000_000,
            3,
        ),
        "status": "supported" if observed else "unsupported",
    }
    if observed:
        for name in (
            "private_bytes",
            "working_set_bytes",
            "peak_working_set_bytes",
            "os_threads",
            "cpu_time_ms",
        ):
            result[name] = max(sample[name] for sample in observed)
    return result


def _role_specification(
    role: str,
    executable: Path,
    repository: Path,
) -> tuple[tuple[str, ...], frozenset[int], str | None]:
    if role == "version":
        return (str(executable), "--version"), frozenset({0}), None
    if role == "verify-only":
        return (str(executable), "--verify-only"), frozenset({0}), None
    if role == "provider-host":
        builtin = repository / "mod" / "builtin"
        return (
            (
                str(executable),
                "--provider-host",
                str(builtin / "youtube" / "provider.py"),
                "--provider-root",
                str(builtin),
            ),
            frozenset({1}),
            "{}\n",
        )
    raise ValueError(f"unsupported package-layout role: {role}")


def _run_role(
    role: str,
    executable: Path,
    repository: Path,
    environment: Mapping[str, str],
    sample_runner: SampleRunner,
) -> dict[str, Any]:
    command, expected_codes, input_text = _role_specification(
        role,
        executable,
        repository,
    )
    return sample_runner(
        command,
        cwd=executable.parent,
        environment=environment,
        expected_codes=expected_codes,
        input_text=input_text,
    )


def _sample_summary(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        raise ValueError("sample summary requires at least one sample")
    summary: dict[str, Any] = {
        "samples": len(samples),
        "elapsed_ms": _stats(
            [sample["elapsed_ms"] for sample in samples],
            digits=3,
        ),
        "returncodes": sorted({sample["returncode"] for sample in samples}),
    }
    metrics = (
        "cpu_time_ms",
        "private_bytes",
        "working_set_bytes",
        "peak_working_set_bytes",
        "os_threads",
    )
    if all(sample.get("status") == "supported" for sample in samples):
        summary["process"] = {
            "status": "supported",
            **{
                name: _stats([sample[name] for sample in samples])
                for name in metrics
            },
        }
    else:
        summary["process"] = {"status": "unsupported"}
    return summary


def _measure_layout(
    executable: Path,
    repository: Path,
    runtime_root: Path,
    *,
    warmups: int,
    iterations: int,
    sample_runner: SampleRunner,
) -> dict[str, Any]:
    environment = _runtime_environment(runtime_root)
    cold = _run_role(
        "version",
        executable,
        repository,
        environment,
        sample_runner,
    )
    role_samples: dict[str, list[dict[str, Any]]] = {
        role: [] for role in BENCHMARK_ROLES
    }
    for role in BENCHMARK_ROLES:
        for index in range(warmups + iterations):
            sample = _run_role(
                role,
                executable,
                repository,
                environment,
                sample_runner,
            )
            if index >= warmups:
                role_samples[role].append(sample)
    return {
        "cold_version": cold,
        "roles": {
            role: _sample_summary(samples)
            for role, samples in role_samples.items()
        },
    }


def run_layout_experiment(
    repository_root: Path,
    *,
    temp_root: Path | None = None,
    warmups: int = 2,
    iterations: int = 7,
    keep_artifacts: bool = False,
    pyinstaller: Path | None = None,
    build_runner: BuildRunner = subprocess.run,
    sample_runner: SampleRunner = run_process_sample,
    source_validator: SourceValidator = validate_clean_source,
) -> dict[str, Any]:
    """Build, hash, copy and benchmark both layouts outside the source tree."""

    if not 0 <= warmups <= 10:
        raise ValueError("warmups must be between 0 and 10")
    if not 1 <= iterations <= 50:
        raise ValueError("iterations must be between 1 and 50")
    repository = repository_root.resolve(strict=True)
    revision = source_validator(repository)
    executable_builder = (
        Path(sys.executable).with_name("pyinstaller.exe")
        if pyinstaller is None
        else pyinstaller.resolve()
    )
    if not executable_builder.is_file() or executable_builder.is_symlink():
        raise FileNotFoundError("PyInstaller executable is missing or unsafe")
    experiment_root = validate_temp_root(
        default_temp_root() if temp_root is None else temp_root,
        repository,
    )
    attempt, token = _create_owned_attempt(experiment_root)
    report: dict[str, Any] | None = None
    cleanup_error: BaseException | None = None
    try:
        layouts: dict[str, Any] = {}
        for layout in PACKAGE_LAYOUTS:
            build_root = attempt / "builds" / layout
            build_temp = attempt / "build-temp" / layout
            build_temp.mkdir(parents=True)
            environment = pyinstaller_build_environment(
                os.environ,
                python_executable=Path(sys.executable),
                base_prefix=Path(sys.base_prefix),
                temp_dir=build_temp,
                layout=layout,
            )
            command = pyinstaller_command(
                executable_builder,
                repository,
                build_root,
            )
            build_started = time.perf_counter_ns()
            build_runner(
                list(command),
                cwd=repository,
                check=True,
                env=environment,
            )
            build_elapsed_ms = round(
                (time.perf_counter_ns() - build_started) / 1_000_000,
                3,
            )
            artifact_root, executable = artifact_paths(build_root, layout)
            if not executable.is_file() or executable.is_symlink():
                raise FileNotFoundError(
                    f"{layout} prototype executable is missing or unsafe"
                )
            integrity_started = time.perf_counter_ns()
            before = snapshot_tree(artifact_root)
            identity = artifact_identity(before)
            integrity_elapsed_ms = round(
                (time.perf_counter_ns() - integrity_started) / 1_000_000,
                3,
            )
            measured_root = attempt / "measurement-artifacts" / layout
            shutil.copytree(artifact_root, measured_root, symlinks=True)
            if snapshot_tree(measured_root) != before:
                raise RuntimeError(f"{layout} measurement copy hash mismatch")
            measured = _measure_layout(
                measured_root / "MediaManager.exe",
                repository,
                attempt / "runtime" / layout / "original",
                warmups=warmups,
                iterations=iterations,
                sample_runner=sample_runner,
            )
            measured_materialization = validate_runtime_materialization(
                before,
                snapshot_tree(measured_root),
            )
            if snapshot_tree(artifact_root) != before:
                raise RuntimeError(f"{layout} artifact changed during measurement")
            copied_root = attempt / "copies" / layout
            copy_started = time.perf_counter_ns()
            shutil.copytree(artifact_root, copied_root, symlinks=True)
            copied = snapshot_tree(copied_root)
            copy_elapsed_ms = round(
                (time.perf_counter_ns() - copy_started) / 1_000_000,
                3,
            )
            if copied != before:
                raise RuntimeError(f"{layout} copied artifact hash mismatch")
            copied_executable = copied_root / "MediaManager.exe"
            copied_smoke = {
                role: _run_role(
                    role,
                    copied_executable,
                    repository,
                    _runtime_environment(
                        attempt / "runtime" / layout / "copied" / role
                    ),
                    sample_runner,
                )
                for role in BENCHMARK_ROLES
            }
            copied_materialization = validate_runtime_materialization(
                copied,
                snapshot_tree(copied_root),
            )
            if snapshot_tree(artifact_root) != before:
                raise RuntimeError(f"{layout} source artifact changed during smoke")
            layouts[layout] = {
                "build_elapsed_ms": build_elapsed_ms,
                "artifact": asdict(identity),
                "integrity_elapsed_ms": integrity_elapsed_ms,
                "measurement": measured,
                "measurement_materialization": measured_materialization,
                "copied_folder_smoke": {
                    "passed": True,
                    "copy_elapsed_ms": copy_elapsed_ms,
                    "manifest_matches": True,
                    "materialization": copied_materialization,
                    "roles": copied_smoke,
                },
            }
        report = {
            "schema_version": SCHEMA_VERSION,
            "result": "PACKAGE_LAYOUT_EXPERIMENT_RECORDED",
            "source": {
                "core_version": CORE_VERSION,
                "revision": revision,
                "fingerprint_sha256": source_fingerprint(repository),
            },
            "environment": {
                "python": platform.python_version(),
                "os": platform.system(),
                "os_release": platform.release(),
                "machine": platform.machine(),
                "pyinstaller": str(executable_builder),
            },
            "workload": {
                "warmups": warmups,
                "iterations": iterations,
                "roles": list(BENCHMARK_ROLES),
                "visible_ui_allowed": False,
                "user_data_isolated": True,
                "artifacts_inside_repository": False,
            },
            "layouts": layouts,
            "artifacts_retained": keep_artifacts,
            "artifact_root": str(attempt) if keep_artifacts else "",
        }
    finally:
        if not keep_artifacts:
            try:
                _remove_owned_attempt(attempt, token)
            except BaseException as error:
                cleanup_error = error
    if cleanup_error is not None:
        raise RuntimeError("package-layout experiment cleanup failed") from cleanup_error
    if report is None:
        raise RuntimeError("package-layout experiment produced no report")
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="explicitly authorize both isolated prototype builds",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--keep-artifacts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = _parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    if not parsed.execute:
        print(json.dumps(package_layout_plan(repository), ensure_ascii=False, indent=2))
        return 0
    if parsed.output is None:
        print("Package-layout experiment failed: --output is required", file=sys.stderr)
        return 2
    try:
        # Reject repository-overlapping, link-like or existing evidence paths
        # before an expensive build; write_report validates again after the run
        # to close the time-of-check/time-of-use window.
        validate_output_path(parsed.output, repository)
        report = run_layout_experiment(
            repository,
            temp_root=parsed.temp_root,
            warmups=parsed.warmups,
            iterations=parsed.iterations,
            keep_artifacts=parsed.keep_artifacts,
        )
        output = write_report(report, parsed.output, repository)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Package-layout experiment failed: {error}", file=sys.stderr)
        return 2
    print(f"Package-layout experiment written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
