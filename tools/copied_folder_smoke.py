"""Fail-closed copied-folder and rollback smoke validation.

The default library runner cannot guarantee termination of a complete Windows
process tree after a timeout, so it stops after ``--verify-only``.  The CLI uses
a kill-on-close Windows Job Object runner for the complete headless sequence.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time

from core.downloads.windows_job import ProviderJob
from tools.audit_versions import VersionAudit, audit_version


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
AuditChecker = Callable[[Path], VersionAudit]
_ATTEMPT_PREFIX = "copied-folder-"
_OWNER_MARKER = ".mediamanager-smoke-owner"
_ROLLBACK_SENTINEL = ".mediamanager-rollback-token"
_SEQUENCE = ("current", "previous", "current")
_CREATE_SUSPENDED = 0x00000004


@dataclass(frozen=True, slots=True)
class CommandStatus:
    name: str
    command: tuple[str, ...]
    returncode: int | None
    passed: bool
    timed_out: bool
    error: str


@dataclass(frozen=True, slots=True)
class VersionCommandStatus:
    phase: int
    label: str
    source: str
    copied_root: str
    portable_data_root: str
    commands: tuple[CommandStatus, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class CopiedFolderSmokeReport:
    schema_version: int
    copied_folder_smoke: bool
    rollback: bool
    source_unchanged: bool
    process_tree_safe: bool
    attempt: str
    kept_temp: bool
    errors: tuple[str, ...]
    versions: tuple[VersionCommandStatus, ...]


@dataclass(frozen=True, slots=True)
class OwnedAttempt:
    root: Path
    token: str


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _absolute_without_links(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _paths_overlap(first: Path, second: Path) -> bool:
    first = first.expanduser().resolve(strict=False)
    second = second.expanduser().resolve(strict=False)
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def _version_folder_key(folder: str) -> tuple[int, int]:
    major, minor = folder.split(".")
    return int(major), int(minor)


def default_temp_root(
    environment: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> Path:
    """Return a user-writable smoke root without falling back on Windows TEMP."""

    values = os.environ if environment is None else environment
    local_app_data = values.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MediaManager-SmokeRuns"
    platform_name = os.name if platform is None else platform
    if platform_name == "nt":
        raise RuntimeError(
            "LOCALAPPDATA is unavailable; provide an explicit --temp-root"
        )
    cache = values.get("XDG_CACHE_HOME")
    return (
        Path(cache) if cache else Path.home() / ".cache"
    ) / "mediamanager" / "smoke-runs"


def create_owned_attempt(temp_root: Path) -> OwnedAttempt:
    temp_root = temp_root.expanduser()
    if _is_linklike(temp_root):
        raise ValueError("smoke temp root must not be a symbolic link or junction")
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_root = temp_root.resolve()
    token = secrets.token_hex(32)
    attempt = Path(tempfile.mkdtemp(prefix=_ATTEMPT_PREFIX, dir=temp_root))
    if attempt.parent != temp_root or not attempt.name.startswith(_ATTEMPT_PREFIX):
        raise RuntimeError("owned smoke attempt escaped its temp root")
    (attempt / _OWNER_MARKER).write_text(token, encoding="ascii")
    return OwnedAttempt(attempt, token)


def remove_owned_attempt(attempt: OwnedAttempt, *, retries: int = 3) -> None:
    """Remove only the uniquely marked attempt created by this invocation."""

    root = attempt.root
    marker = root / _OWNER_MARKER
    if (
        not root.name.startswith(_ATTEMPT_PREFIX)
        or root.parent == root
        or _is_linklike(root)
    ):
        raise RuntimeError("refusing to clean an unsafe smoke attempt")
    try:
        recorded = marker.read_text(encoding="ascii")
    except OSError as error:
        raise RuntimeError("smoke ownership marker is missing") from error
    if not secrets.compare_digest(recorded, attempt.token):
        raise RuntimeError("smoke ownership marker does not match")
    last_error: OSError | None = None
    for retry in range(retries):
        try:
            shutil.rmtree(root)
            return
        except OSError as error:
            last_error = error
            if retry + 1 < retries:
                time.sleep(0.1 * (retry + 1))
    raise RuntimeError("failed to clean the owned smoke attempt") from last_error


def _iter_tree(root: Path) -> tuple[tuple[str, str, str], ...]:
    entries: list[tuple[str, str, str]] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        names.sort()
        filenames.sort()
        for name in names:
            child = directory_path / name
            if _is_linklike(child):
                raise ValueError(
                    f"symbolic link or junction is not allowed: "
                    f"{child.relative_to(root).as_posix()}"
                )
            entries.append(("directory", child.relative_to(root).as_posix(), ""))
        for name in filenames:
            child = directory_path / name
            if _is_linklike(child) or not child.is_file():
                raise ValueError(
                    f"unsafe file is not allowed: "
                    f"{child.relative_to(root).as_posix()}"
                )
            digest = hashlib.sha256(child.read_bytes()).hexdigest()
            entries.append(("file", child.relative_to(root).as_posix(), digest))
    return tuple(entries)


def _tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for kind, relative, content_digest in _iter_tree(root):
        digest.update(kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_source(
    source: Path,
    retained_root: Path,
    *,
    audit_checker: AuditChecker,
) -> tuple[Path, VersionAudit, str]:
    retained_absolute = _absolute_without_links(retained_root.expanduser())
    source_absolute = _absolute_without_links(source.expanduser())
    if not retained_absolute.is_dir() or _is_linklike(retained_absolute):
        raise ValueError("retained version root is missing or unsafe")
    if not source_absolute.is_relative_to(retained_absolute):
        raise ValueError("version root escapes the retained version root")
    relative = source_absolute.relative_to(retained_absolute)
    if not relative.parts:
        raise ValueError("a retained version root cannot be used as a release")
    cursor = retained_absolute
    for part in relative.parts:
        cursor /= part
        if _is_linklike(cursor):
            raise ValueError("version root contains a symbolic link or junction")
    try:
        retained_resolved = retained_absolute.resolve(strict=True)
        source_resolved = source_absolute.resolve(strict=True)
    except OSError as error:
        raise ValueError("version root is missing or inaccessible") from error
    if (
        not source_resolved.is_dir()
        or not source_resolved.is_relative_to(retained_resolved)
    ):
        raise ValueError("version root is missing or escapes retained versions")
    _iter_tree(source_resolved)
    audit = audit_checker(source_resolved)
    if not audit.valid:
        details = "; ".join(audit.errors) or "unknown audit failure"
        raise ValueError(f"version checksum audit failed: {details}")
    return source_resolved, audit, _tree_fingerprint(source_resolved)


def _copy_release(
    source: Path,
    destination: Path,
    *,
    audit_checker: AuditChecker,
) -> None:
    shutil.copytree(source, destination, symlinks=True)
    _iter_tree(destination)
    copied_audit = audit_checker(destination)
    if not copied_audit.valid:
        details = "; ".join(copied_audit.errors) or "unknown audit failure"
        raise RuntimeError(f"copied version audit failed: {details}")
    if _tree_fingerprint(source) != _tree_fingerprint(destination):
        raise RuntimeError("copied version does not match its retained source")


def _copy_destination(attempt: Path, label: str, source: Path) -> Path:
    """Preserve a release track parent so the copied audit has identical semantics."""

    label_root = attempt / label
    if source.parent.name in {"Development", "Testing", "Stable"}:
        return label_root / source.parent.name / source.name
    return label_root / source.name


def _portable_data(copy_root: Path) -> Path:
    return copy_root / "UserData"


def _validate_shared_data(copy_root: Path, token: str) -> None:
    data_root = _portable_data(copy_root)
    sentinel = data_root / _ROLLBACK_SENTINEL
    if (
        not data_root.is_dir()
        or _is_linklike(data_root)
        or not data_root.resolve().is_relative_to(copy_root.resolve())
        or not sentinel.is_file()
        or _is_linklike(sentinel)
    ):
        raise RuntimeError("shared portable data or rollback sentinel is unsafe")
    try:
        recorded = sentinel.read_text(encoding="ascii")
    except OSError as error:
        raise RuntimeError("rollback sentinel is unreadable") from error
    if not secrets.compare_digest(recorded, token):
        raise RuntimeError("rollback sentinel does not match this smoke attempt")


def _validate_shared_owner(
    owner: Path,
    other: Path,
    token: str,
) -> None:
    _validate_shared_data(owner, token)
    if _portable_data(other).exists():
        raise RuntimeError("shared portable data exists in both rollback copies")


def _initialize_shared_data(current: Path, previous: Path, token: str) -> None:
    current_data = _portable_data(current)
    previous_data = _portable_data(previous)
    if current_data.exists() or previous_data.exists():
        raise RuntimeError("copied release already contains portable UserData")
    current_data.mkdir(parents=True)
    pending = current_data / f"{_ROLLBACK_SENTINEL}.pending"
    pending.write_text(token, encoding="ascii")
    pending.replace(current_data / _ROLLBACK_SENTINEL)
    _validate_shared_owner(current, previous, token)


def _move_shared_data(source: Path, destination: Path, token: str) -> None:
    """Atomically move the complete portable state between owned copies."""

    source_data = _portable_data(source)
    destination_data = _portable_data(destination)
    _validate_shared_data(source, token)
    if destination_data.exists():
        raise RuntimeError("rollback destination already contains UserData")
    source_data.rename(destination_data)
    _validate_shared_owner(destination, source, token)


def _recover_shared_data(current: Path, previous: Path, token: str) -> None:
    """Best-effort recovery always leaves the owned shared state at current."""

    current_data = _portable_data(current)
    previous_data = _portable_data(previous)
    if previous_data.exists() and not current_data.exists():
        previous_data.rename(current_data)
    elif previous_data.exists() and current_data.exists():
        raise RuntimeError("cannot recover duplicate rollback UserData")
    _validate_shared_owner(current, previous, token)


def _blocked_headless(executable: Path) -> CommandStatus:
    return CommandStatus(
        name="headless-portable",
        command=(str(executable), "--headless", "--portable"),
        returncode=None,
        passed=False,
        timed_out=False,
        error=(
            "headless smoke blocked: the configured runner does not guarantee "
            "termination of the complete process tree"
        ),
    )


def _reap_contained_process(
    process: subprocess.Popen[str],
) -> tuple[str, str]:
    """Reap a process after its kill-on-close Job has been closed."""

    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return stdout or "", stderr or ""


def _resume_suspended_process(process_handle: int) -> None:
    """Resume a process only after it is contained by the Job Object."""

    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtResumeProcess.restype = wintypes.LONG
    status = ntdll.NtResumeProcess(wintypes.HANDLE(process_handle))
    if status != 0:
        raise RuntimeError(f"NtResumeProcess failed with status 0x{status & 0xFFFFFFFF:08x}")


def contained_windows_runner(
    command: list[str] | tuple[str, ...],
    *,
    cwd: Path,
    shell: bool,
    timeout: float,
    check: bool,
    capture_output: bool,
    text: bool,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run a command in a Windows kill-on-close Job and always reap it.

    ``ProviderJob.close`` terminates every process assigned to the Job.  It is
    called on success too, preventing a command that exits after spawning a
    detached child from leaving that child behind.
    """

    if os.name != "nt":
        raise RuntimeError("Windows Job Object containment is unavailable")
    if shell or not capture_output or not text:
        raise ValueError("contained runner requires shell=False and text capture")
    job = ProviderJob(active_process_limit=16)
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(env),
            creationflags=subprocess.CREATE_NO_WINDOW | _CREATE_SUSPENDED,
        )
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
            _reap_contained_process(process)
            raise
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            job.close()
            if process.poll() is None:
                process.kill()
            final_stdout, final_stderr = _reap_contained_process(process)
            raise subprocess.TimeoutExpired(
                command,
                timeout,
                output=error.output or final_stdout,
                stderr=error.stderr or final_stderr,
            ) from error
        completed = subprocess.CompletedProcess(
            list(command), process.returncode, stdout, stderr
        )
        if check:
            completed.check_returncode()
        return completed
    finally:
        job.close()


def _run_command(
    name: str,
    command: tuple[str, ...],
    *,
    cwd: Path,
    timeout: float,
    runner: CommandRunner,
    environment: Mapping[str, str],
) -> CommandStatus:
    try:
        result = runner(
            list(command),
            cwd=cwd,
            shell=False,
            timeout=timeout,
            check=False,
            capture_output=True,
            text=True,
            env=dict(environment),
        )
    except subprocess.TimeoutExpired:
        return CommandStatus(
            name,
            command,
            None,
            False,
            True,
            f"command timed out after {timeout:g} seconds",
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        return CommandStatus(name, command, None, False, False, str(error))
    passed = result.returncode == 0
    return CommandStatus(
        name,
        command,
        result.returncode,
        passed,
        False,
        "" if passed else f"command exited with status {result.returncode}",
    )


def _run_version_phase(
    phase: int,
    label: str,
    source: Path,
    copied_root: Path,
    *,
    timeout: float,
    runner: CommandRunner,
    process_tree_safe: bool,
) -> VersionCommandStatus:
    executable = copied_root / "MediaManager.exe"
    portable_data = copied_root / "UserData"
    environment_root = portable_data / "Environment"
    environment_paths = {
        "LOCALAPPDATA": environment_root / "LocalAppData",
        "APPDATA": environment_root / "Roaming",
        "USERPROFILE": environment_root / "Home",
        "HOME": environment_root / "Home",
        "TEMP": environment_root / "Temp",
        "TMP": environment_root / "Temp",
        "TMPDIR": environment_root / "Temp",
    }
    for path in set(environment_paths.values()):
        path.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {name: str(path) for name, path in environment_paths.items()}
    )
    commands: list[CommandStatus] = []
    specifications = (
        ("version", (str(executable), "--version")),
        ("verify-only", (str(executable), "--portable", "--verify-only")),
    )
    for name, command in specifications:
        status = _run_command(
            name,
            command,
            cwd=copied_root,
            timeout=timeout,
            runner=runner,
            environment=environment,
        )
        commands.append(status)
        if not status.passed:
            return VersionCommandStatus(
                phase,
                label,
                str(source),
                str(copied_root),
                str(portable_data),
                tuple(commands),
                False,
            )
    if not process_tree_safe:
        commands.append(_blocked_headless(executable))
    else:
        commands.append(
            _run_command(
                "headless-portable",
                (str(executable), "--headless", "--portable"),
                cwd=copied_root,
                timeout=timeout,
                runner=runner,
                environment=environment,
            )
        )
    return VersionCommandStatus(
        phase,
        label,
        str(source),
        str(copied_root),
        str(portable_data),
        tuple(commands),
        all(command.passed for command in commands),
    )


def _empty_report(*errors: str, process_tree_safe: bool) -> CopiedFolderSmokeReport:
    return CopiedFolderSmokeReport(
        schema_version=1,
        copied_folder_smoke=False,
        rollback=False,
        source_unchanged=False,
        process_tree_safe=process_tree_safe,
        attempt="",
        kept_temp=False,
        errors=tuple(dict.fromkeys(errors)),
        versions=(),
    )


def run_copied_folder_smoke(
    current_root: Path,
    previous_root: Path,
    *,
    retained_root: Path,
    temp_root: Path | None = None,
    keep_temp: bool = False,
    timeout: float = 30.0,
    runner: CommandRunner = subprocess.run,
    process_tree_safe: bool = False,
    audit_checker: AuditChecker = audit_version,
) -> CopiedFolderSmokeReport:
    """Copy, verify, and exercise current/previous/current without source writes."""

    if timeout <= 0 or timeout > 300:
        return _empty_report(
            "timeout must be greater than zero and no more than 300 seconds",
            process_tree_safe=process_tree_safe,
        )
    try:
        current, current_audit, current_fingerprint = _validate_source(
            current_root, retained_root, audit_checker=audit_checker
        )
        previous, previous_audit, previous_fingerprint = _validate_source(
            previous_root, retained_root, audit_checker=audit_checker
        )
    except (OSError, ValueError) as error:
        return _empty_report(str(error), process_tree_safe=process_tree_safe)
    if current == previous:
        return _empty_report(
            "current and previous version roots must be different",
            process_tree_safe=process_tree_safe,
        )
    if current_audit.track != previous_audit.track:
        return _empty_report(
            "current and previous versions must use the same release track",
            process_tree_safe=process_tree_safe,
        )
    if _version_folder_key(previous_audit.folder) >= _version_folder_key(
        current_audit.folder
    ):
        return _empty_report(
            "previous version folder must be strictly earlier than current",
            process_tree_safe=process_tree_safe,
        )

    try:
        effective_temp_root = (temp_root or default_temp_root()).expanduser()
        retained_resolved = retained_root.expanduser().resolve(strict=True)
        overlaps = {
            "retained": retained_resolved,
            "current": current,
            "previous": previous,
        }
        for label, protected in overlaps.items():
            if _paths_overlap(effective_temp_root, protected):
                return _empty_report(
                    f"smoke temp root overlaps {label} version data",
                    process_tree_safe=process_tree_safe,
                )
    except (OSError, RuntimeError, ValueError) as error:
        return _empty_report(str(error), process_tree_safe=process_tree_safe)

    try:
        attempt = create_owned_attempt(effective_temp_root)
    except (OSError, RuntimeError, ValueError) as error:
        return _empty_report(str(error), process_tree_safe=process_tree_safe)

    sources = {"current": current, "previous": previous}
    source_audits = {"current": current_audit, "previous": previous_audit}
    source_fingerprints = {
        "current": current_fingerprint,
        "previous": previous_fingerprint,
    }
    copies = {
        label: _copy_destination(attempt.root, label, source)
        for label, source in sources.items()
    }
    errors: list[str] = []
    phases: list[VersionCommandStatus] = []
    sequence_complete = False
    shared_sequence_complete = False
    shared_recovered = False
    source_unchanged = False
    cleanup_ok = keep_temp

    try:
        for label in ("current", "previous"):
            _copy_release(
                sources[label], copies[label], audit_checker=audit_checker
            )
        _initialize_shared_data(
            copies["current"], copies["previous"], attempt.token
        )
        shared_owner = "current"
        for phase, label in enumerate(_SEQUENCE, start=1):
            if label != shared_owner:
                _move_shared_data(
                    copies[shared_owner], copies[label], attempt.token
                )
                shared_owner = label
            other = "previous" if label == "current" else "current"
            _validate_shared_owner(
                copies[label], copies[other], attempt.token
            )
            status = _run_version_phase(
                phase,
                label,
                sources[label],
                copies[label],
                timeout=timeout,
                runner=runner,
                process_tree_safe=process_tree_safe,
            )
            phases.append(status)
            try:
                _validate_shared_owner(
                    copies[label], copies[other], attempt.token
                )
            except RuntimeError as error:
                errors.append(f"{label} shared portable data check failed: {error}")
                break
            if not status.passed:
                for command in status.commands:
                    if not command.passed:
                        errors.append(f"{label} {command.name}: {command.error}")
                break
        sequence_complete = (
            len(phases) == len(_SEQUENCE)
            and all(phase.passed for phase in phases)
        )
        shared_sequence_complete = sequence_complete and shared_owner == "current"
    except (OSError, RuntimeError, ValueError) as error:
        errors.append(str(error))
    finally:
        try:
            _recover_shared_data(
                copies["current"], copies["previous"], attempt.token
            )
            shared_recovered = True
        except (OSError, RuntimeError, ValueError) as error:
            shared_recovered = False
            errors.append(f"shared portable data recovery failed: {error}")
        unchanged = True
        for label, source in sources.items():
            try:
                after_audit = audit_checker(source)
                after_fingerprint = _tree_fingerprint(source)
            except (OSError, ValueError) as error:
                unchanged = False
                errors.append(f"{label} retained source re-audit failed: {error}")
                continue
            if (
                not after_audit.valid
                or after_audit != source_audits[label]
                or after_fingerprint != source_fingerprints[label]
            ):
                unchanged = False
                errors.append(f"{label} retained source changed during smoke")
        source_unchanged = unchanged
        if not keep_temp:
            try:
                remove_owned_attempt(attempt)
                cleanup_ok = True
            except (OSError, RuntimeError, ValueError) as error:
                cleanup_ok = False
                errors.append(f"owned attempt cleanup failed: {error}")

    rollback_passed = (
        shared_sequence_complete
        and shared_recovered
        and source_unchanged
        and cleanup_ok
    )
    passed = sequence_complete and rollback_passed
    return CopiedFolderSmokeReport(
        schema_version=1,
        copied_folder_smoke=passed,
        rollback=rollback_passed,
        source_unchanged=source_unchanged,
        process_tree_safe=process_tree_safe,
        attempt=str(attempt.root) if keep_temp or not cleanup_ok else "",
        kept_temp=keep_temp,
        errors=tuple(dict.fromkeys(errors)),
        versions=tuple(phases),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and copy retained versions, then run a fail-closed rollback smoke."
        )
    )
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, default=Path("Version"))
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    report = run_copied_folder_smoke(
        args.current,
        args.previous,
        retained_root=args.retained_root,
        temp_root=args.temp_root,
        keep_temp=args.keep_temp,
        timeout=args.timeout,
        runner=contained_windows_runner,
        process_tree_safe=True,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.copied_folder_smoke and report.rollback else 1


if __name__ == "__main__":
    raise SystemExit(main())
