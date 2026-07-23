"""Run Repository tests from a fixed root with an isolated temporary directory."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TestRunPaths:
    attempt: Path
    runtime_temp: Path
    pytest_temp: Path


def repository_root() -> Path:
    """Return the Repository root independently of the caller's current directory."""

    return Path(__file__).resolve().parents[1]


def default_temp_root(
    environment: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> Path:
    """Select a user-local pytest root without changing filesystem ACLs."""

    values = os.environ if environment is None else environment
    platform_name = os.name if platform is None else platform
    local_app_data = values.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).resolve() / "MediaManager-TestRuns"
    if platform_name == "nt":
        raise RuntimeError(
            "LOCALAPPDATA is unavailable; select a writable --temp-root"
        )
    cache_root = values.get("XDG_CACHE_HOME")
    if cache_root:
        return Path(cache_root).resolve() / "mediamanager" / "pytest-temp"
    return Path.home().resolve() / ".cache" / "mediamanager" / "pytest-temp"


def create_test_run_paths(temp_root: Path) -> TestRunPaths:
    """Reserve one owned attempt directory and describe its isolated roots."""

    selected_temp_root = temp_root.resolve()
    selected_temp_root.mkdir(parents=True, exist_ok=True)
    attempt = Path(
        tempfile.mkdtemp(prefix="pytest-", dir=selected_temp_root)
    ).resolve()
    if attempt.parent != selected_temp_root:
        raise RuntimeError("pytest temporary directory escapes the selected root")
    return TestRunPaths(
        attempt=attempt,
        runtime_temp=attempt / "runtime",
        pytest_temp=attempt / "pytest",
    )


def test_environment(runtime_temp: Path) -> dict[str, str]:
    """Route Python and native temporary files into this test invocation."""

    environment = os.environ.copy()
    # Inherited addopts can inject positional paths outside ``tests`` and undo
    # the collection boundary enforced by ``pytest_command``.
    environment.pop("PYTEST_ADDOPTS", None)
    temporary_path = str(runtime_temp.resolve())
    environment.update(
        {
            "TEMP": temporary_path,
            "TMP": temporary_path,
            "TMPDIR": temporary_path,
        }
    )
    return environment


def remove_test_tree(path: Path, *, attempts: int = 3) -> None:
    """Remove an owned test tree with bounded retries for transient Windows locks."""

    if attempts < 1:
        raise ValueError("cleanup attempts must be positive")
    for attempt in range(1, attempts + 1):
        if not path.exists() and not path.is_symlink():
            return
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt == attempts:
                raise
            time.sleep(0.1 * attempt)


def resolve_test_targets(root: Path, targets: Sequence[str]) -> tuple[str, ...]:
    """Resolve explicit targets while confining collection to Repository tests."""

    root = root.resolve()
    tests_path = root / "tests"
    if tests_path.is_symlink():
        raise ValueError("Repository tests root must not be a symbolic link")
    if not tests_path.is_dir():
        raise FileNotFoundError(f"Repository tests root does not exist: {tests_path}")
    tests_root = tests_path.resolve()
    requested = tuple(targets) or ("tests",)
    resolved: list[str] = []
    for raw_target in requested:
        path_text, separator, node_id = raw_target.partition("::")
        if not path_text:
            raise ValueError("pytest target path is empty")
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(tests_root)
        except ValueError as exc:
            raise ValueError(
                f"pytest target must stay under {tests_root}: {raw_target}"
            ) from exc
        if not candidate.exists():
            raise FileNotFoundError(f"pytest target does not exist: {candidate}")
        resolved.append(
            str(candidate) + (f"::{node_id}" if separator else "")
        )
    return tuple(resolved)


def pytest_command(
    root: Path,
    basetemp: Path,
    *,
    targets: Sequence[str] = (),
) -> list[str]:
    """Build a pytest command with controlled collection and temporary roots."""

    root = root.resolve()
    return [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--rootdir",
        str(root),
        "--basetemp",
        str(basetemp.resolve()),
        *resolve_test_targets(root, targets),
    ]


def run_tests(
    root: Path,
    *,
    temp_root: Path | None = None,
    targets: Sequence[str] = (),
    keep_temp: bool = False,
) -> int:
    """Run pytest in the Repository and clean only this invocation's temp path."""

    root = root.resolve()
    selected_temp_root = (
        default_temp_root() if temp_root is None else temp_root.resolve()
    )
    paths = create_test_run_paths(selected_temp_root)
    completed: subprocess.CompletedProcess[str] | None = None
    failure: BaseException | None = None
    cleanup_error: OSError | None = None
    try:
        paths.runtime_temp.mkdir()
        command = pytest_command(
            root,
            paths.pytest_temp,
            targets=targets,
        )
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            env=test_environment(paths.runtime_temp),
        )
    except BaseException as error:
        failure = error
    finally:
        if keep_temp:
            print(
                f"pytest temporary directory preserved: {paths.attempt}",
                file=sys.stderr,
            )
        else:
            if paths.attempt.parent != selected_temp_root:
                raise RuntimeError("refusing to clean an unsafe pytest temporary path")
            try:
                remove_test_tree(paths.attempt)
            except OSError as error:
                cleanup_error = error

    if failure is not None:
        if cleanup_error is not None:
            failure.add_note(f"pytest temporary cleanup failed: {cleanup_error}")
        raise failure
    if completed is None:
        raise RuntimeError("pytest did not return a result")
    if cleanup_error is not None:
        print(f"FAIL: pytest temporary cleanup failed: {cleanup_error}", file=sys.stderr)
        return completed.returncode or 2
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="Writable root for an invocation-specific pytest temporary directory",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Preserve this invocation's temporary directory for diagnostics",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Test path or node under tests; repeat for multiple targets",
    )
    args = parser.parse_args()
    try:
        return run_tests(
            repository_root(),
            temp_root=args.temp_root,
            targets=args.target,
            keep_temp=args.keep_temp,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
