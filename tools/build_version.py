"""Build and stage a version without scattering build directories."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from core.version import CORE_VERSION
from tools.portable_runtime import cached_ffmpeg_paths, cached_runtime_path
from tools.stage_version import stage_version, version_folder_name


@dataclass(frozen=True, slots=True)
class VersionBuildPaths:
    work: Path
    temp: Path
    pyinstaller_work: Path
    executable_output: Path
    wheel_output: Path


def version_build_paths(root: Path, version: str) -> VersionBuildPaths:
    work = root.resolve() / ".work" / version_folder_name(version)
    return VersionBuildPaths(
        work=work,
        temp=work / "temp",
        pyinstaller_work=work / "pyinstaller",
        executable_output=work / "exe",
        wheel_output=work / "wheel",
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
) -> Path:
    root = root.resolve()
    paths = version_build_paths(root, version)
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
    subprocess.run(
        wheel_build_command(Path(sys.executable), paths.wheel_output),
        cwd=root,
        check=True,
        env=wheel_environment,
    )
    executable = paths.executable_output / "MediaManager.exe"
    wheel = paths.wheel_output / f"mediamanager-{version}-py3-none-any.whl"
    target = stage_version(
        root,
        version=version,
        executable=executable,
        wheel=wheel,
        portable_tools=portable_tools,
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
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
