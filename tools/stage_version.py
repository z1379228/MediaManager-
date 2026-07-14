"""Stage a complete MediaManager build under Version/<major>.<minor>."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Mapping

from core.security.release_layout import SOURCE_RELEASE_FILES
from core.version import BUILD_CHANNEL, CORE_VERSION, release_track, release_version
from tools.release_inventory import build_cyclonedx_sbom, build_inventory


_REPLACE_ATTEMPTS = 5
_REPLACE_DELAY_SECONDS = 0.05


def version_folder_name(version: str) -> str:
    major, minor, _ = release_version(version)
    return f"{major}.{minor}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace_with_retry(source: Path, target: Path) -> Path:
    """Retry short Windows scanner locks without hiding persistent failures."""

    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            return source.replace(target)
        except PermissionError:
            if attempt + 1 == _REPLACE_ATTEMPTS:
                raise
            time.sleep(_REPLACE_DELAY_SECONDS * (attempt + 1))
    raise AssertionError("unreachable replace retry state")


def _recover_stage_transaction(
    target: Path, staging: Path, backup: Path
) -> None:
    target_exists = target.exists()
    staging_exists = staging.exists()
    backup_exists = backup.exists()
    if target_exists and staging_exists and backup_exists:
        raise RuntimeError("ambiguous version staging transaction requires review")
    try:
        if backup_exists and not target_exists:
            if staging_exists:
                shutil.rmtree(staging)
            _replace_with_retry(backup, target)
            return
        if backup_exists and target_exists:
            shutil.rmtree(backup)
        if staging_exists:
            shutil.rmtree(staging)
    except OSError as error:
        raise RuntimeError(
            "cannot recover version staging; close any running MediaManager.exe "
            "from this version and retry"
        ) from error


def stage_version(
    source_root: Path,
    *,
    output_root: Path | None = None,
    version: str = CORE_VERSION,
    executable: Path | None = None,
    wheel: Path | None = None,
    portable_tools: Mapping[str, Path] | None = None,
    channel: str = BUILD_CHANNEL,
    confirm_stable: bool = False,
) -> Path:
    source_root = source_root.resolve()
    output_root = (output_root or source_root / "Version").resolve()
    track = release_track(channel)
    if channel == "stable" and not confirm_stable:
        raise PermissionError(
            "stable packaging requires explicit user confirmation"
        )
    output_root = (output_root / track).resolve()
    folder = version_folder_name(version)
    target = output_root / folder
    staging = output_root / f".{folder}.staging"
    backup = output_root / f".{folder}.backup"
    output_root.mkdir(parents=True, exist_ok=True)
    for candidate in (target, staging, backup):
        if candidate.parent != output_root:
            raise ValueError("unsafe version output path")
    _recover_stage_transaction(target, staging, backup)

    executable = (executable or source_root / "dist" / "MediaManager.exe").resolve()
    wheel = (
        wheel
        or source_root
        / "dist-packages"
        / f"mediamanager-{version}-py3-none-any.whl"
    ).resolve()
    if not executable.is_file() or executable.is_symlink():
        raise FileNotFoundError(f"executable missing or unsafe: {executable}")
    if not wheel.is_file() or wheel.is_symlink():
        raise FileNotFoundError(f"wheel missing or unsafe: {wheel}")

    try:
        staging.mkdir()
        shutil.copy2(executable, staging / "MediaManager.exe")
        shutil.copy2(wheel, staging / wheel.name)
        staged_tools: list[str] = []
        for name, raw_source in sorted((portable_tools or {}).items()):
            if Path(name).name != name or not name:
                raise ValueError(f"unsafe portable tool name: {name}")
            source = raw_source.resolve()
            if not source.is_file() or source.is_symlink():
                raise FileNotFoundError(f"portable tool missing or unsafe: {source}")
            destination = staging / "tools" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            staged_tools.append(name)
        for name in SOURCE_RELEASE_FILES[1:]:
            source = source_root / Path(*name.split("/"))
            destination = staging / Path(*name.split("/"))
            if not source.is_file() or source.is_symlink():
                raise FileNotFoundError(f"release file missing or unsafe: {name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        info = {
            "schema_version": 1,
            "core_version": version,
            "build_channel": channel,
            "release_track": track,
            "version_folder": folder,
            "portable_tools": staged_tools,
        }
        (staging / "release-info.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        inventory = build_inventory(core_version=version)
        (staging / "dependency-inventory.json").write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (staging / "sbom.cdx.json").write_text(
            json.dumps(
                build_cyclonedx_sbom(inventory),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        checksum_files = sorted(
            path
            for path in staging.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        )
        lines = [
            f"{_sha256(path)}  {path.relative_to(staging).as_posix()}"
            for path in checksum_files
        ]
        (staging / "SHA256SUMS.txt").write_text(
            "\n".join(lines) + "\n", encoding="ascii"
        )
        if target.exists():
            _replace_with_retry(target, backup)
        _replace_with_retry(staging, target)
        if backup.exists():
            shutil.rmtree(backup)
        return target
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists() and not target.exists():
            _replace_with_retry(backup, target)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage the current build in Version/<major>.<minor>."
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--version", default=CORE_VERSION)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument(
        "--channel", choices=("development", "stable"), default=BUILD_CHANNEL
    )
    parser.add_argument("--confirm-stable", action="store_true")
    args = parser.parse_args()
    target = stage_version(
        args.source_root,
        output_root=args.output_root,
        version=args.version,
        executable=args.executable,
        wheel=args.wheel,
        channel=args.channel,
        confirm_stable=args.confirm_stable,
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
