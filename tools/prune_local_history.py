"""Plan or apply a fail-closed prune of ignored local release history.

The default operation is read-only.  Applying a plan requires a publish-ready
Stable release, two explicitly retained releases, an exact confirmation value,
and a clean scan showing that no deletion candidate contains UserData or a
link-like filesystem entry.  Git-tracked release notes are outside ``Version``
and are never part of this tool's scope.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

from tools.audit_versions import VersionAudit, audit_version
from tools.release_preflight import PreflightResult, check_release


APPLY_CONFIRMATION = "DELETE-LOCAL-RELEASE-HISTORY"
_RELEASE_TRACKS = frozenset({"Development", "Testing", "Stable"})
_VERSION_FOLDER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_PROTECTED_PARTS = frozenset({"userdata"})


@dataclass(frozen=True, slots=True)
class PruneCandidate:
    relative_path: str
    files: int
    bytes: int


@dataclass(frozen=True, slots=True)
class LocalHistoryPrunePlan:
    root: str
    kept: tuple[str, ...]
    candidates: tuple[PruneCandidate, ...]
    blocked: tuple[str, ...]
    candidate_files: int
    candidate_bytes: int
    ready_to_apply: bool


def _is_linklike(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse)


def _safe_release_relative(value: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise ValueError("retained release path must use safe forward slashes")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or relative.as_posix() != value
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError("retained release path is unsafe")
    if len(relative.parts) == 1:
        version = relative.parts[0]
    elif len(relative.parts) == 2 and relative.parts[0] in _RELEASE_TRACKS:
        version = relative.parts[1]
    else:
        raise ValueError("retained release path must name one exact release")
    if _VERSION_FOLDER.fullmatch(version) is None:
        raise ValueError("retained release folder must use major.minor")
    return relative


def _safe_root(root: Path) -> Path:
    expanded = root.expanduser()
    if not expanded.is_dir() or _is_linklike(expanded):
        raise ValueError("version root is missing or unsafe")
    return expanded.resolve()


def _discover_releases(root: Path) -> tuple[dict[str, Path], tuple[str, ...]]:
    releases: dict[str, Path] = {}
    errors: list[str] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
        if _is_linklike(entry) or not entry.is_dir():
            errors.append(f"unexpected or link-like version root entry: {entry.name}")
            continue
        if _VERSION_FOLDER.fullmatch(entry.name):
            releases[entry.name] = entry
            continue
        if entry.name not in _RELEASE_TRACKS:
            errors.append(f"unexpected version root entry: {entry.name}")
            continue
        for release in sorted(
            entry.iterdir(), key=lambda path: path.name.casefold()
        ):
            relative = f"{entry.name}/{release.name}"
            if (
                _is_linklike(release)
                or not release.is_dir()
                or _VERSION_FOLDER.fullmatch(release.name) is None
            ):
                errors.append(f"unexpected or link-like release entry: {relative}")
                continue
            releases[relative] = release
    if not releases:
        errors.append("no local release folders found")
    return releases, tuple(dict.fromkeys(errors))


def _scan_candidate(path: Path, relative: str) -> tuple[PruneCandidate, tuple[str, ...]]:
    files = 0
    total_bytes = 0
    errors: list[str] = []
    try:
        entries = tuple(path.rglob("*"))
    except OSError as error:
        return PruneCandidate(relative, 0, 0), (
            f"{relative} cannot be read safely: {error}",
        )
    for entry in entries:
        child_relative = entry.relative_to(path)
        if any(part.casefold() in _PROTECTED_PARTS for part in child_relative.parts):
            errors.append(f"{relative} contains protected UserData content")
        if _is_linklike(entry):
            errors.append(
                f"{relative} contains link-like entry: {child_relative.as_posix()}"
            )
            continue
        if entry.is_file():
            try:
                total_bytes += entry.stat().st_size
            except OSError as error:
                errors.append(
                    f"{relative} file metadata cannot be read: "
                    f"{child_relative.as_posix()}: {error}"
                )
                continue
            files += 1
    return (
        PruneCandidate(relative, files, total_bytes),
        tuple(dict.fromkeys(errors)),
    )


def plan_local_history_prune(
    root: Path,
    *,
    keep: Sequence[str],
    audit_checker: Callable[[Path], VersionAudit] = audit_version,
    preflight_checker: Callable[[Path], PreflightResult] = check_release,
) -> LocalHistoryPrunePlan:
    """Create a read-only local-release deletion plan."""

    version_root = _safe_root(root)
    kept = tuple(sorted({_safe_release_relative(value).as_posix() for value in keep}))
    if len(kept) < 2:
        raise ValueError("at least two unique releases must be retained")
    releases, discovery_errors = _discover_releases(version_root)
    missing = tuple(value for value in kept if value not in releases)
    if missing:
        raise ValueError(f"retained release is missing: {', '.join(missing)}")

    blocked: list[str] = list(discovery_errors)
    stable_kept = tuple(value for value in kept if value.startswith("Stable/"))
    if not stable_kept:
        blocked.append("at least one retained Stable release is required")
    for relative in kept:
        audit = audit_checker(releases[relative])
        if not audit.valid:
            blocked.append(f"retained release failed audit: {relative}")
    for relative in stable_kept:
        preflight = preflight_checker(releases[relative])
        if not preflight.ready:
            detail = "; ".join(preflight.errors) or "preflight did not pass"
            blocked.append(f"{relative} is not publish-ready: {detail}")

    candidates: list[PruneCandidate] = []
    for relative in sorted(set(releases) - set(kept)):
        candidate, errors = _scan_candidate(releases[relative], relative)
        candidates.append(candidate)
        blocked.extend(errors)
    unique_blocked = tuple(dict.fromkeys(blocked))
    return LocalHistoryPrunePlan(
        root=str(version_root),
        kept=kept,
        candidates=tuple(candidates),
        blocked=unique_blocked,
        candidate_files=sum(item.files for item in candidates),
        candidate_bytes=sum(item.bytes for item in candidates),
        ready_to_apply=not unique_blocked,
    )


def apply_local_history_prune(
    plan: LocalHistoryPrunePlan,
    *,
    confirmation: str,
    audit_checker: Callable[[Path], VersionAudit] = audit_version,
    preflight_checker: Callable[[Path], PreflightResult] = check_release,
) -> tuple[str, ...]:
    """Apply one already validated plan after exact operator confirmation."""

    if confirmation != APPLY_CONFIRMATION:
        raise PermissionError("local history prune confirmation does not match")
    if not plan.ready_to_apply:
        raise PermissionError("local history prune plan is blocked")
    root = _safe_root(Path(plan.root))
    current_plan = plan_local_history_prune(
        root,
        keep=plan.kept,
        audit_checker=audit_checker,
        preflight_checker=preflight_checker,
    )
    if not current_plan.ready_to_apply or current_plan != plan:
        raise RuntimeError("local history prune plan changed or is now blocked")
    kept = set(plan.kept)
    prepared: list[Path] = []
    for expected in plan.candidates:
        relative = _safe_release_relative(expected.relative_path)
        if relative.as_posix() in kept:
            raise RuntimeError("prune candidate overlaps a retained release")
        candidate = root.joinpath(*relative.parts)
        if (
            not candidate.is_dir()
            or _is_linklike(candidate)
            or candidate.parent not in {root, *(root / track for track in _RELEASE_TRACKS)}
        ):
            raise RuntimeError(f"prune candidate changed or is unsafe: {expected.relative_path}")
        current, errors = _scan_candidate(candidate, expected.relative_path)
        if errors or current != expected:
            raise RuntimeError(f"prune candidate changed or is unsafe: {expected.relative_path}")
        prepared.append(candidate)
    for candidate in prepared:
        shutil.rmtree(candidate)
    return tuple(item.relative_path for item in plan.candidates)


def _print_human(plan: LocalHistoryPrunePlan, *, mode: str, deleted: tuple[str, ...]) -> None:
    print(f"MODE {mode}")
    print(f"ROOT {plan.root}")
    print(f"KEEP {', '.join(plan.kept)}")
    for candidate in plan.candidates:
        print(
            f"DELETE {candidate.relative_path} "
            f"files={candidate.files} bytes={candidate.bytes}"
        )
    for blocker in plan.blocked:
        print(f"BLOCKED {blocker}")
    if deleted:
        print(f"DELETED {', '.join(deleted)}")
    print("READY" if plan.ready_to_apply else "NOT READY")


def main(
    argv: Sequence[str] | None = None,
    *,
    audit_checker: Callable[[Path], VersionAudit] = audit_version,
    preflight_checker: Callable[[Path], PreflightResult] = check_release,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("Version"))
    parser.add_argument(
        "--keep",
        action="append",
        required=True,
        help="Exact retained release path, for example Stable/1.0",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        plan = plan_local_history_prune(
            args.root,
            keep=args.keep,
            audit_checker=audit_checker,
            preflight_checker=preflight_checker,
        )
        deleted = (
            apply_local_history_prune(
                plan,
                confirmation=args.confirm,
                audit_checker=audit_checker,
                preflight_checker=preflight_checker,
            )
            if args.apply
            else ()
        )
    except (OSError, PermissionError, RuntimeError, ValueError) as error:
        if args.as_json:
            print(json.dumps({"ready_to_apply": False, "errors": [str(error)]}))
        else:
            print(f"BLOCKED {error}")
        return 2
    mode = "apply" if args.apply else "dry-run"
    if args.as_json:
        result = asdict(plan)
        result.update({"mode": mode, "deleted": deleted})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(plan, mode=mode, deleted=deleted)
    return 0 if plan.ready_to_apply else 1


if __name__ == "__main__":
    raise SystemExit(main())
