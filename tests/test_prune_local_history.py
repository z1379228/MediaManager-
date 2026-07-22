from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_versions import VersionAudit
from tools.prune_local_history import (
    APPLY_CONFIRMATION,
    apply_local_history_prune,
    main,
    plan_local_history_prune,
)
from tools.release_preflight import PreflightResult


def _write_release(version_root: Path, relative: str, *, payload: bytes = b"x") -> Path:
    release = version_root.joinpath(*relative.split("/"))
    release.mkdir(parents=True)
    (release / "release-info.json").write_text("{}", encoding="utf-8")
    (release / "payload.bin").write_bytes(payload)
    return release


def _valid_audit(path: Path) -> VersionAudit:
    return VersionAudit(
        folder=path.name,
        core_version="1.0.0",
        checked=1,
        valid=True,
        errors=(),
        track=path.parent.name,
    )


def _ready_preflight(_path: Path) -> PreflightResult:
    return PreflightResult(ready=True, checked=1, errors=())


def test_plan_keeps_current_and_previous_and_lists_only_local_release_dirs(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "Version"
    stable = _write_release(version_root, "Stable/1.0")
    previous = _write_release(version_root, "Development/38.0", payload=b"previous")
    obsolete = _write_release(version_root, "Testing/1.1", payload=b"obsolete")
    update_info = tmp_path / "docs" / "release-39.0-40.0.md"
    update_info.parent.mkdir()
    update_info.write_text("retained update information", encoding="utf-8")

    plan = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=_valid_audit,
        preflight_checker=_ready_preflight,
    )

    assert plan.ready_to_apply
    assert plan.kept == ("Development/38.0", "Stable/1.0")
    assert tuple(item.relative_path for item in plan.candidates) == ("Testing/1.1",)
    assert plan.candidate_files == 2
    assert plan.candidate_bytes == sum(
        path.stat().st_size for path in obsolete.rglob("*") if path.is_file()
    )
    assert stable.is_dir()
    assert previous.is_dir()
    assert update_info.read_text(encoding="utf-8") == "retained update information"


def test_plan_fails_closed_when_old_release_contains_userdata(tmp_path: Path) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "Stable/1.0")
    _write_release(version_root, "Development/38.0")
    obsolete = _write_release(version_root, "Development/16.1")
    protected = obsolete / "UserData" / "Logs" / "audit.jsonl"
    protected.parent.mkdir(parents=True)
    protected.write_text("unique audit evidence", encoding="utf-8")

    plan = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=_valid_audit,
        preflight_checker=_ready_preflight,
    )

    assert not plan.ready_to_apply
    assert plan.blocked == (
        "Development/16.1 contains protected UserData content",
    )


@pytest.mark.parametrize(
    "keep",
    [
        ("Stable/1.0",),
        ("Stable/1.0", "../outside"),
        ("Stable/1.0", "Development\\38.0"),
    ],
)
def test_plan_requires_two_unique_safe_retained_releases(
    tmp_path: Path, keep: tuple[str, ...]
) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "Stable/1.0")
    _write_release(version_root, "Development/38.0")

    with pytest.raises(ValueError):
        plan_local_history_prune(
            version_root,
            keep=keep,
            audit_checker=_valid_audit,
            preflight_checker=_ready_preflight,
        )


def test_plan_requires_valid_retained_versions_and_publish_ready_stable(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "Version"
    stable = _write_release(version_root, "Stable/1.0")
    _write_release(version_root, "Development/38.0")

    invalid = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=lambda path: VersionAudit(
            path.name, "1.0.0", 0, path == stable, (() if path == stable else ("bad",)), path.parent.name
        ),
        preflight_checker=_ready_preflight,
    )
    blocked = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=_valid_audit,
        preflight_checker=lambda _path: PreflightResult(
            ready=False,
            checked=0,
            errors=("signature missing",),
        ),
    )

    assert not invalid.ready_to_apply
    assert "retained release failed audit: Development/38.0" in invalid.blocked
    assert not blocked.ready_to_apply
    assert "Stable/1.0 is not publish-ready: signature missing" in blocked.blocked


def test_apply_requires_exact_confirmation_and_deletes_only_candidates(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "Version"
    stable = _write_release(version_root, "Stable/1.0")
    previous = _write_release(version_root, "Development/38.0")
    obsolete = _write_release(version_root, "Testing/1.1")
    plan = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=_valid_audit,
        preflight_checker=_ready_preflight,
    )

    with pytest.raises(PermissionError):
        apply_local_history_prune(
            plan,
            confirmation="yes",
            audit_checker=_valid_audit,
            preflight_checker=_ready_preflight,
        )

    deleted = apply_local_history_prune(
        plan,
        confirmation=APPLY_CONFIRMATION,
        audit_checker=_valid_audit,
        preflight_checker=_ready_preflight,
    )

    assert deleted == ("Testing/1.1",)
    assert stable.is_dir()
    assert previous.is_dir()
    assert not obsolete.exists()


def test_apply_rechecks_retained_release_after_dry_run(tmp_path: Path) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "Stable/1.0")
    previous = _write_release(version_root, "Development/38.0")
    obsolete = _write_release(version_root, "Testing/1.1")

    def audit_without_invalid_marker(path: Path) -> VersionAudit:
        audit = _valid_audit(path)
        if (path / "invalid-after-plan").exists():
            return VersionAudit(
                folder=audit.folder,
                core_version=audit.core_version,
                checked=audit.checked,
                valid=False,
                errors=("changed after dry-run",),
                track=audit.track,
            )
        return audit

    plan = plan_local_history_prune(
        version_root,
        keep=("Stable/1.0", "Development/38.0"),
        audit_checker=audit_without_invalid_marker,
        preflight_checker=_ready_preflight,
    )
    (previous / "invalid-after-plan").write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="plan changed or is now blocked"):
        apply_local_history_prune(
            plan,
            confirmation=APPLY_CONFIRMATION,
            audit_checker=audit_without_invalid_marker,
            preflight_checker=_ready_preflight,
        )

    assert obsolete.is_dir()


def test_cli_defaults_to_json_dry_run_and_never_deletes(tmp_path: Path, capsys) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "Stable/1.0")
    _write_release(version_root, "Development/38.0")
    obsolete = _write_release(version_root, "Testing/1.1")

    exit_code = main(
        [
            "--root",
            str(version_root),
            "--keep",
            "Stable/1.0",
            "--keep",
            "Development/38.0",
            "--json",
        ],
        audit_checker=_valid_audit,
        preflight_checker=_ready_preflight,
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["mode"] == "dry-run"
    assert output["ready_to_apply"] is True
    assert obsolete.is_dir()
