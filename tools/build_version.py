"""Build and stage a version without scattering build directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import re
import shutil
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping

from core.version import (
    BUILD_CHANNEL,
    CORE_VERSION,
    release_identity_version,
    release_track,
)
from tools.portable_runtime import cached_ffmpeg_paths, cached_runtime_path
from tools.release_preflight import authenticode_status
from tools.stage_version import stage_version, version_folder_name


BUILD_RECEIPT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class VersionBuildPaths:
    work: Path
    temp: Path
    pyinstaller_work: Path
    executable_output: Path
    wheel_output: Path


def version_build_paths(
    root: Path,
    version: str,
    *,
    channel: str = BUILD_CHANNEL,
    release_version: str | None = None,
    attempt_id: str | None = None,
) -> VersionBuildPaths:
    if attempt_id is not None and not re.fullmatch(r"[a-z0-9-]{1,32}", attempt_id):
        raise ValueError("build attempt id is invalid")
    folder = version_folder_name(release_version or version)
    if attempt_id is not None:
        folder = f"{folder}-attempt-{attempt_id}"
    work = (
        root.resolve()
        / ".work"
        / release_track(channel)
        / folder
    )
    return VersionBuildPaths(
        work=work,
        temp=work / "temp",
        pyinstaller_work=work / "pyinstaller",
        executable_output=work / "exe",
        wheel_output=work / "wheel",
    )


def configured_project_version(root: Path) -> str:
    document = tomllib.loads((root.resolve() / "pyproject.toml").read_text(encoding="utf-8"))
    project = document.get("project")
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject project.version is missing")
    return version


def validate_build_version(root: Path, version: str) -> None:
    project_version = configured_project_version(root)
    if project_version != CORE_VERSION:
        raise ValueError(
            "version mismatch: core/version.py and pyproject.toml must match"
        )
    if version != CORE_VERSION:
        raise ValueError(
            "build version override is not allowed; update the canonical version sources"
        )


def validate_clean_source(root: Path) -> str:
    """Return the exact Git revision, rejecting uncommitted release sources."""

    if shutil.which("git") is None:
        raise FileNotFoundError("Git is required to verify the release source")
    status = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stderr.strip():
        raise RuntimeError(
            "release source inspection is incomplete; Git reported a diagnostic"
        )
    if status.stdout.strip():
        raise RuntimeError(
            "release source is dirty; commit or intentionally remove every listed "
            "change before packaging"
        )
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("release source revision is invalid")
    return revision


def portable_release_tools(root: Path, *, enabled: bool) -> dict[str, Path]:
    if not enabled:
        return {}
    deno = cached_runtime_path(root)
    if deno is None:
        raise FileNotFoundError(
            "verified portable Deno is missing; run "
            "'python -m tools.portable_runtime' first"
        )
    license_file = root / "third_party" / "deno" / "LICENSE.md"
    if not license_file.is_file() or license_file.is_symlink():
        raise FileNotFoundError(f"Deno license is missing or unsafe: {license_file}")
    ffmpeg = cached_ffmpeg_paths(root)
    if ffmpeg is None:
        raise FileNotFoundError(
            "verified portable FFmpeg is missing; run "
            "'python -m tools.portable_runtime' first"
        )
    return {
        "deno.exe": deno,
        "DENO-LICENSE.md": license_file,
        **ffmpeg,
    }


def wheel_build_command(python: Path, wheel_output: Path) -> list[str]:
    return [
        str(python),
        "-m",
        "pip",
        "wheel",
        ".",
        "--no-deps",
        "--no-build-isolation",
        "--wheel-dir",
        str(wheel_output),
    ]


def wheel_build_environment(
    environment: Mapping[str, str], temp_root: Path
) -> dict[str, str]:
    """Keep every pip-created wheel artifact inside the current build attempt."""

    temp_root.mkdir(parents=True, exist_ok=True)
    tracker = temp_root / "build-tracker"
    cache = temp_root / "cache"
    tracker.mkdir()
    cache.mkdir()
    result = dict(environment)
    result.update(
        {
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "PIP_BUILD_TRACKER": str(tracker),
            "PIP_CACHE_DIR": str(cache),
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
    )
    return result


def remove_build_tree(path: Path, *, attempts: int = 3) -> None:
    """Remove one build-owned directory without touching release output."""

    if attempts < 1:
        raise ValueError("cleanup attempts must be positive")
    for attempt in range(1, attempts + 1):
        if not path.exists():
            return
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt == attempts:
                raise
            time.sleep(0.1 * attempt)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_build_receipt(
    paths: VersionBuildPaths,
    *,
    version: str,
    release_version: str,
    channel: str,
    source_revision: str,
) -> Path:
    """Bind a build-only handoff to its clean source revision and wheel bytes."""

    wheel = paths.wheel_output / f"mediamanager-{version}-py3-none-any.whl"
    executable = paths.executable_output / "MediaManager.exe"
    if not executable.is_file() or executable.is_symlink():
        raise FileNotFoundError(f"build executable missing or unsafe: {executable}")
    if not wheel.is_file() or wheel.is_symlink():
        raise FileNotFoundError(f"build wheel missing or unsafe: {wheel}")
    receipt = paths.work / "build-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": BUILD_RECEIPT_SCHEMA_VERSION,
                "core_version": version,
                "release_version": release_version,
                "build_channel": channel,
                "source_revision": source_revision,
                "wheel_sha256": _sha256(wheel),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt


def _validated_built_artifacts(
    root: Path,
    work: Path,
    *,
    version: str,
    release_version: str,
    channel: str,
    source_revision: str,
) -> tuple[Path, Path]:
    work = work.resolve()
    expected_parent = (root / ".work" / release_track(channel)).resolve()
    folder = re.escape(version_folder_name(release_version))
    if work.parent != expected_parent or not re.fullmatch(
        rf"{folder}-attempt-[a-z0-9-]{{1,32}}", work.name
    ):
        raise ValueError("built work directory is outside the selected release track")
    if not work.is_dir() or work.is_symlink():
        raise FileNotFoundError(f"built work directory is missing or unsafe: {work}")
    receipt_path = work / "build-receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("build receipt is missing or invalid") from exc
    expected = {
        "schema_version": BUILD_RECEIPT_SCHEMA_VERSION,
        "core_version": version,
        "release_version": release_version,
        "build_channel": channel,
        "source_revision": source_revision,
    }
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("build receipt does not match the selected release source")
    executable = work / "exe" / "MediaManager.exe"
    wheel = work / "wheel" / f"mediamanager-{version}-py3-none-any.whl"
    if not executable.is_file() or executable.is_symlink():
        raise FileNotFoundError(f"build executable missing or unsafe: {executable}")
    if not wheel.is_file() or wheel.is_symlink():
        raise FileNotFoundError(f"build wheel missing or unsafe: {wheel}")
    if receipt.get("wheel_sha256") != _sha256(wheel):
        raise ValueError("built wheel does not match the build receipt")
    return executable, wheel


def stage_built_version(
    root: Path,
    work: Path,
    version: str = CORE_VERSION,
    *,
    portable_runtime: bool = True,
    channel: str = BUILD_CHANNEL,
    confirm_stable: bool = False,
    authenticode_checker: Callable[[Path], str] = authenticode_status,
) -> Path:
    """Stage a receipt-bound build after an external Authenticode signing step."""

    root = root.resolve()
    if channel == "stable" and not confirm_stable:
        raise PermissionError("stable packaging requires explicit user confirmation")
    validate_build_version(root, version)
    source_revision = validate_clean_source(root)
    public_version = release_identity_version(channel)
    executable, wheel = _validated_built_artifacts(
        root,
        work,
        version=version,
        release_version=public_version,
        channel=channel,
        source_revision=source_revision,
    )
    if channel == "stable":
        status = authenticode_checker(executable)
        if status != "Valid":
            raise PermissionError(
                f"stable executable Authenticode signature is not valid: {status}"
            )
    return stage_version(
        root,
        version=version,
        release_version=public_version,
        executable=executable,
        wheel=wheel,
        portable_tools=portable_release_tools(root, enabled=portable_runtime),
        channel=channel,
        confirm_stable=confirm_stable,
    )


def _record_cleanup_failure(
    failure: BaseException | None,
    errors: list[tuple[Path, OSError]],
) -> None:
    if not errors:
        return
    details = "; ".join(f"{path}: {error}" for path, error in errors)
    message = (
        "build temporary cleanup failed; close processes using these paths and run "
        f"the project cleanup tool after restart: {details}"
    )
    if failure is not None:
        failure.add_note(message)
        return
    raise OSError(message) from errors[0][1]


def build_version(
    root: Path,
    version: str = CORE_VERSION,
    *,
    keep_work: bool = False,
    portable_runtime: bool = True,
    channel: str = BUILD_CHANNEL,
    confirm_stable: bool = False,
    temp_root: Path | None = None,
    stage_output: bool = True,
) -> Path:
    root = root.resolve()
    if channel == "stable" and not confirm_stable:
        raise PermissionError(
            "stable packaging requires explicit user confirmation"
        )
    validate_build_version(root, version)
    source_revision = validate_clean_source(root)
    generated_targets = (root / "build", root / "mediamanager.egg-info")
    preexisting_targets = tuple(
        target
        for target in generated_targets
        if target.exists() or target.is_symlink()
    )
    if preexisting_targets:
        names = ", ".join(str(target) for target in preexisting_targets)
        raise FileExistsError(
            "refusing to build over pre-existing generated paths; "
            f"move or remove them explicitly first: {names}"
        )
    public_version = release_identity_version(channel)
    attempt_id = secrets.token_hex(4)
    paths = version_build_paths(
        root,
        version,
        channel=channel,
        release_version=public_version,
        attempt_id=attempt_id,
    )
    external_temp_root = None if temp_root is None else temp_root.resolve()
    build_temp = paths.temp
    if external_temp_root is not None:
        build_temp = external_temp_root / f"mediamanager-build-{attempt_id}"
        if build_temp.parent != external_temp_root:
            raise ValueError("build temporary directory escapes the selected root")
    portable_tools = portable_release_tools(root, enabled=portable_runtime)
    failure: BaseException | None = None
    work_created = False
    build_temp_created = False
    try:
        paths.work.parent.mkdir(parents=True, exist_ok=True)
        paths.work.mkdir(exist_ok=False)
        work_created = True
        build_temp.mkdir(
            parents=True,
            exist_ok=False,
        )
        build_temp_created = True
        build_environment = os.environ.copy()
        build_environment["TEMP"] = str(build_temp)
        build_environment["TMP"] = str(build_temp)
        pyinstaller = Path(sys.executable).with_name("pyinstaller.exe")
        if not pyinstaller.is_file():
            raise FileNotFoundError(
                f"PyInstaller executable is missing: {pyinstaller}"
            )
        subprocess.run(
            [
                str(pyinstaller),
                "--clean",
                "--noconfirm",
                "--workpath",
                str(paths.pyinstaller_work),
                "--distpath",
                str(paths.executable_output),
                str(root / "MediaManager.spec"),
            ],
            cwd=root,
            check=True,
            env=build_environment,
        )
        if paths.wheel_output.exists():
            remove_build_tree(paths.wheel_output)
        paths.wheel_output.mkdir(parents=True)
        wheel_environment = wheel_build_environment(
            build_environment, build_temp / "pip-wheel"
        )
        subprocess.run(
            wheel_build_command(Path(sys.executable), paths.wheel_output),
            cwd=root,
            check=True,
            env=wheel_environment,
        )
        executable = paths.executable_output / "MediaManager.exe"
        wheel = paths.wheel_output / f"mediamanager-{version}-py3-none-any.whl"
        if not stage_output:
            write_build_receipt(
                paths,
                version=version,
                release_version=public_version,
                channel=channel,
                source_revision=source_revision,
            )
            return paths.work
        return stage_version(
            root,
            version=version,
            release_version=public_version,
            executable=executable,
            wheel=wheel,
            portable_tools=portable_tools,
            channel=channel,
            confirm_stable=confirm_stable,
        )
    except BaseException as exc:
        failure = exc
        raise
    finally:
        cleanup_errors: list[tuple[Path, OSError]] = []
        cleanup_targets = (
            [paths.work]
            if work_created and not keep_work and stage_output
            else []
        )
        # ``build`` and ``mediamanager.egg-info`` are fixed setuptools paths
        # under the source root.  A different process may create them after
        # our preflight check, so this build cannot prove ownership at cleanup
        # time.  Preserve them and let the next preflight fail closed instead
        # of recursively deleting another process's output.
        for target in cleanup_targets:
            if target.parent not in {root, root / ".work" / release_track(channel)}:
                continue
            try:
                remove_build_tree(target)
            except OSError as exc:
                cleanup_errors.append((target, exc))
        if (
            not keep_work
            and external_temp_root is not None
            and build_temp_created
        ):
            if build_temp.parent != external_temp_root:
                raise RuntimeError("refusing to clean an unsafe build temporary path")
            try:
                remove_build_tree(build_temp)
            except OSError as exc:
                cleanup_errors.append((build_temp, exc))
        _record_cleanup_failure(failure, cleanup_errors)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build into .work and stage into Version/<major>.<minor>."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--version", default=CORE_VERSION)
    parser.add_argument("--keep-work", action="store_true")
    parser.add_argument(
        "--channel",
        choices=("development", "testing", "stable"),
        default=BUILD_CHANNEL,
    )
    parser.add_argument("--confirm-stable", action="store_true")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "--build-only",
        action="store_true",
        help="retain receipt-bound artifacts for Authenticode signing before staging",
    )
    operation.add_argument(
        "--stage-built",
        type=Path,
        help="stage a receipt-bound build directory after external signing",
    )
    parser.add_argument(
        "--without-portable-runtime",
        action="store_true",
        help="build without pinned Deno and FFmpeg runtimes",
    )
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="Writable user-local root for isolated build temporary directories",
    )
    args = parser.parse_args()
    if args.stage_built is not None:
        result = stage_built_version(
            args.root,
            args.stage_built,
            args.version,
            portable_runtime=not args.without_portable_runtime,
            channel=args.channel,
            confirm_stable=args.confirm_stable,
        )
    else:
        result = build_version(
            args.root,
            args.version,
            keep_work=args.keep_work,
            portable_runtime=not args.without_portable_runtime,
            channel=args.channel,
            confirm_stable=args.confirm_stable,
            temp_root=args.temp_root,
            stage_output=not args.build_only,
        )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
