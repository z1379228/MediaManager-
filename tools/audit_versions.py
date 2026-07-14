"""Read-only integrity audit for retained MediaManager version folders."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


_FOLDER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
_CHECKSUM_PATTERN = re.compile(r"^([0-9a-f]{64})  (.+)$")
_POST_STAGE_SIGNING_FILES = {
    "security/release-manifest.json",
    "security/release-manifest.sig",
}


@dataclass(frozen=True, slots=True)
class VersionAudit:
    folder: str
    core_version: str
    checked: int
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VersionAuditReport:
    root: str
    valid: bool
    errors: tuple[str, ...]
    versions: tuple[VersionAudit, ...]


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _safe_relative(value: str) -> PurePosixPath | None:
    if not value or "\\" in value:
        return None
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or value != relative.as_posix()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return None
    return relative


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _wheel_version(path: Path) -> tuple[str, ...]:
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_names = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                return ()
            lines = archive.read(metadata_names[0]).decode("utf-8").splitlines()
    except (OSError, UnicodeError, zipfile.BadZipFile, KeyError):
        return ()
    names = tuple(line[6:].strip() for line in lines if line.startswith("Name: "))
    versions = tuple(
        line[9:].strip() for line in lines if line.startswith("Version: ")
    )
    if names != ("mediamanager",) or len(versions) != 1:
        return ()
    return versions


def audit_version(root: Path) -> VersionAudit:
    root = root.resolve()
    errors: list[str] = []
    folder = root.name
    core_version = ""
    portable_tools: tuple[str, ...] = ()

    info_path = root / "release-info.json"
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        info = None
        errors.append("release-info.json is missing or invalid")
    if not isinstance(info, dict):
        info = {}
    if info.get("schema_version") != 1:
        errors.append("release-info schema_version must be 1")
    raw_version = info.get("core_version")
    if isinstance(raw_version, str):
        core_version = raw_version
    version_match = _VERSION_PATTERN.fullmatch(core_version)
    if version_match is None:
        errors.append("core_version must use canonical major.minor.patch")
    elif f"{version_match.group(1)}.{version_match.group(2)}" != folder:
        errors.append("core_version does not match the version folder")
    if info.get("version_folder") != folder:
        errors.append("release-info version_folder does not match the folder")

    raw_tools = info.get("portable_tools")
    if (
        not isinstance(raw_tools, list)
        or not all(
            isinstance(name, str) and name and Path(name).name == name
            for name in raw_tools
        )
        or len(raw_tools) != len(set(raw_tools))
    ):
        errors.append("portable_tools must contain unique safe filenames")
    else:
        portable_tools = tuple(raw_tools)
        for name in portable_tools:
            if not _regular_file(root / "tools" / name):
                errors.append(f"portable tool is missing or unsafe: {name}")

    executable = root / "MediaManager.exe"
    if not _regular_file(executable):
        errors.append("MediaManager.exe is missing or unsafe")

    wheels = sorted(root.glob("*.whl"))
    expected_wheel = root / f"mediamanager-{core_version}-py3-none-any.whl"
    if len(wheels) != 1 or not _regular_file(expected_wheel):
        errors.append("exactly one version-matched wheel is required")
    elif _wheel_version(expected_wheel) != (core_version,):
        errors.append("wheel METADATA name or version is invalid")

    checksums_path = root / "SHA256SUMS.txt"
    manifest: dict[str, str] = {}
    try:
        lines = checksums_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        lines = []
        errors.append("SHA256SUMS.txt is missing or invalid")
    for position, line in enumerate(lines, start=1):
        match = _CHECKSUM_PATTERN.fullmatch(line)
        if match is None:
            errors.append(f"invalid checksum line: {position}")
            continue
        digest, name = match.groups()
        relative = _safe_relative(name)
        if relative is None or name == "SHA256SUMS.txt":
            errors.append(f"unsafe checksum path: {name}")
            continue
        if name in manifest:
            errors.append(f"duplicate checksum path: {name}")
            continue
        manifest[name] = digest

    checked = 0
    for name, expected in manifest.items():
        relative = PurePosixPath(name)
        candidate = root.joinpath(*relative.parts)
        if not _regular_file(candidate):
            errors.append(f"listed file is missing or unsafe: {name}")
            continue
        if not candidate.resolve().is_relative_to(root):
            errors.append(f"listed file escapes the version folder: {name}")
            continue
        if _sha256(candidate) != expected:
            errors.append(f"checksum mismatch: {name}")
            continue
        checked += 1

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symbolic link is not allowed: {path.relative_to(root).as_posix()}")
        if path.is_file() and path.name != "SHA256SUMS.txt":
            actual.add(path.relative_to(root).as_posix())
    signing_files = actual.intersection(_POST_STAGE_SIGNING_FILES)
    if signing_files and signing_files != _POST_STAGE_SIGNING_FILES:
        errors.append("release manifest and signature must be present together")
    allowed_unlisted = (
        _POST_STAGE_SIGNING_FILES
        if signing_files == _POST_STAGE_SIGNING_FILES
        else set()
    )
    for name in sorted(actual - set(manifest) - allowed_unlisted):
        errors.append(f"unlisted file: {name}")
    for name in sorted(set(manifest) - actual):
        errors.append(f"listed file is absent: {name}")

    unique_errors = tuple(dict.fromkeys(errors))
    return VersionAudit(
        folder=folder,
        core_version=core_version,
        checked=checked,
        valid=not unique_errors,
        errors=unique_errors,
    )


def audit_versions(
    root: Path, *, full_history: bool = False
) -> VersionAuditReport:
    root = root.resolve()
    errors: list[str] = []
    if not root.is_dir() or root.is_symlink():
        return VersionAuditReport(
            root=str(root),
            valid=False,
            errors=("version root is missing or unsafe",),
            versions=(),
        )
    version_roots: list[Path] = []
    for path in root.iterdir():
        if path.is_dir() and not path.is_symlink() and _FOLDER_PATTERN.fullmatch(path.name):
            version_roots.append(path)
        else:
            errors.append(f"unexpected version root entry: {path.name}")
    version_roots.sort(key=lambda path: tuple(int(part) for part in path.name.split(".")))
    if not version_roots:
        errors.append("no version folders found")
    elif not full_history:
        version_roots = version_roots[-2:]
    versions = tuple(audit_version(path) for path in version_roots)
    unique_errors = tuple(dict.fromkeys(errors))
    return VersionAuditReport(
        root=str(root),
        valid=not unique_errors and all(version.valid for version in versions),
        errors=unique_errors,
        versions=versions,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the current and previous MediaManager versions by default."
        )
    )
    parser.add_argument("--root", type=Path, default=Path("Version"))
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="audit every locally retained version (major-release maintenance)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit_versions(args.root, full_history=args.full_history)
    if args.as_json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        for error in report.errors:
            print(f"ROOT ERROR: {error}")
        for version in report.versions:
            state = "PASS" if version.valid else "FAIL"
            print(
                f"{state} {version.folder} core={version.core_version or '-'} "
                f"checksums={version.checked}"
            )
            for error in version.errors:
                print(f"  - {error}")
        print(
            f"SUMMARY {'PASS' if report.valid else 'FAIL'} "
            f"versions={len(report.versions)}"
        )
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
