"""Build and stage a version without scattering build directories."""

from __future__ import annotations

import argparse
import os
import secrets
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from core.version import (
    BUILD_CHANNEL,
    CORE_VERSION,
    release_identity_version,
    release_track,
)
from tools.portable_runtime import cached_ffmpeg_paths, cached_runtime_path
from tools.stage_version import stage_version, version_folder_name


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


def build_version(
    root: Path,
    version: str = CORE_VERSION,
    *,
    keep_work: bool = False,
    portable_runtime: bool = True,
    channel: str = BUILD_CHANNEL,
    confirm_stable: bool = False,
) -> Path:
    root = root.resolve()
    if channel == "stable" and not confirm_stable:
        raise PermissionError(
            "stable packaging requires explicit user confirmation"
        )
    validate_build_version(root, version)
    public_version = release_identity_version(channel)
    paths = version_build_paths(
        root,
        version,
        channel=channel,
        release_version=public_version,
        attempt_id=secrets.token_hex(4),
    )
    portable_tools = portable_release_tools(root, enabled=portable_runtime)
    paths.temp.mkdir(parents=True, exist_ok=True)
    build_environment = os.environ.copy()
    build_environment["TEMP"] = str(paths.temp)
    build_environment["TMP"] = str(paths.temp)
    pyinstaller = Path(sys.executable).with_name("pyinstaller.exe")
    if not pyinstaller.is_file():
        raise FileNotFoundError(f"PyInstaller executable is missing: {pyinstaller}")
    paths.work.mkdir(parents=True, exist_ok=True)
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
        shutil.rmtree(paths.wheel_output)
    paths.wheel_output.mkdir(parents=True)
    wheel_environment = build_environment.copy()
    wheel_environment["PIP_NO_INDEX"] = "1"
    wheel_environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    wheel_temp = Path(tempfile.mkdtemp(prefix="mediamanager-wheel-"))
    wheel_environment["TEMP"] = str(wheel_temp)
    wheel_environment["TMP"] = str(wheel_temp)
    try:
        subprocess.run(
            wheel_build_command(Path(sys.executable), paths.wheel_output),
            cwd=root,
            check=True,
            env=wheel_environment,
        )
    finally:
        shutil.rmtree(wheel_temp, ignore_errors=True)
    executable = paths.executable_output / "MediaManager.exe"
    wheel = paths.wheel_output / f"mediamanager-{version}-py3-none-any.whl"
    target = stage_version(
        root,
        version=version,
        release_version=public_version,
        executable=executable,
        wheel=wheel,
        portable_tools=portable_tools,
        channel=channel,
        confirm_stable=confirm_stable,
    )
    if not keep_work:
        shutil.rmtree(paths.work)
    for residue in (root / "build", root / "mediamanager.egg-info"):
        if residue.is_dir() and residue.parent == root:
            shutil.rmtree(residue)
    return target


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
    parser.add_argument(
        "--without-portable-runtime",
        action="store_true",
        help="build without pinned Deno and FFmpeg runtimes",
    )
    args = parser.parse_args()
    print(
        build_version(
            args.root,
            args.version,
            keep_work=args.keep_work,
            portable_runtime=not args.without_portable_runtime,
            channel=args.channel,
            confirm_stable=args.confirm_stable,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
