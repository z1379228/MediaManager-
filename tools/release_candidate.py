"""Read-only stable-candidate assessment; never signs or packages a release."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from core.version import release_version
from tools.audit_versions import VersionAudit, audit_version
from tools.release_preflight import PreflightResult, check_release


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    ruff: bool
    pytest: bool
    copied_folder_smoke: bool
    upgrade: bool
    rollback: bool
    p0_open: int
    p1_open: int

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CandidateEvidence":
        required = {
            "ruff",
            "pytest",
            "copied_folder_smoke",
            "upgrade",
            "rollback",
            "p0_open",
            "p1_open",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise ValueError("candidate evidence fields are invalid")
        for field in (
            "ruff",
            "pytest",
            "copied_folder_smoke",
            "upgrade",
            "rollback",
        ):
            if not isinstance(raw[field], bool):
                raise ValueError("candidate evidence checks must be booleans")
        for field in ("p0_open", "p1_open"):
            if (
                not isinstance(raw[field], int)
                or isinstance(raw[field], bool)
                or not 0 <= raw[field] <= 10000
            ):
                raise ValueError("candidate open issue counts are invalid")
        return cls(**raw)


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    ready: bool
    development_version: str
    suggested_stable_version: str
    blockers: tuple[str, ...]
    action: str


def assess_candidate(
    release_root: Path,
    evidence: CandidateEvidence,
    *,
    suggested_stable_version: str,
    audit_checker: Callable[[Path], VersionAudit] = audit_version,
    preflight_checker: Callable[[Path], PreflightResult] = check_release,
) -> CandidateAssessment:
    """Assess readiness without writing, signing, building, or uploading anything."""

    release_version(suggested_stable_version)
    release_root = release_root.resolve()
    blockers: list[str] = []
    try:
        info = json.loads(
            (release_root / "release-info.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        info = {}
        blockers.append("release-info.json is missing or invalid")
    development_version = str(info.get("core_version") or "")
    if info.get("build_channel") != "development":
        blockers.append("candidate must come from a development build")
    audit = audit_checker(release_root)
    if not audit.valid:
        blockers.append("version checksum audit failed")
    preflight = preflight_checker(release_root)
    blockers.extend(preflight.errors)
    labels = {
        "ruff": "Ruff has not passed",
        "pytest": "Pytest has not passed",
        "copied_folder_smoke": "copied-folder smoke has not passed",
        "upgrade": "upgrade validation has not passed",
        "rollback": "rollback validation has not passed",
    }
    for field, label in labels.items():
        if not getattr(evidence, field):
            blockers.append(label)
    if evidence.p0_open:
        blockers.append(f"P0 issues remain open: {evidence.p0_open}")
    if evidence.p1_open:
        blockers.append(f"P1 issues remain open: {evidence.p1_open}")
    unique = tuple(dict.fromkeys(blockers))
    ready = not unique
    action = (
        f"開發版 {development_version} 已符合正式版 "
        f"{suggested_stable_version} 候選條件；等待使用者決定是否包裝。"
        if ready
        else "尚未達到正式版候選條件；維持開發版且不得包裝 Stable。"
    )
    return CandidateAssessment(
        ready,
        development_version,
        suggested_stable_version,
        unique,
        action,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assess a development build as a stable candidate without packaging."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--suggest-stable", required=True)
    args = parser.parse_args()
    try:
        raw = json.loads(args.evidence.read_text(encoding="utf-8"))
        evidence = CandidateEvidence.from_dict(raw)
        result = assess_candidate(
            args.root,
            evidence,
            suggested_stable_version=args.suggest_stable,
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"ready": False, "errors": [str(error)]}, ensure_ascii=False))
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
