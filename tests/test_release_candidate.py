import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.release_candidate import CandidateEvidence, assess_candidate


def evidence(**changes) -> CandidateEvidence:
    values = {
        "schema_version": 2,
        "tool_schema_version": 2,
        "development_version": "6.0.0",
        "release_build_id": "a" * 64,
        "source_fingerprint": "b" * 64,
        "checksums_sha256": hashlib.sha256(b"checksums\n").hexdigest(),
        "ruff": True,
        "pytest": True,
        "copied_folder_smoke": True,
        "upgrade": True,
        "rollback": True,
        "mod_wiring": True,
        "p0_open": 0,
        "p1_open": 0,
    }
    values.update(changes)
    return CandidateEvidence.from_dict(values)


def write_info(
    root: Path,
    *,
    channel: str = "development",
    schema_version: int = 2,
    tool_schema_version: int | None = None,
) -> None:
    if tool_schema_version is None:
        tool_schema_version = schema_version
    root.mkdir()
    (root / "release-info.json").write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "tool_schema_version": tool_schema_version,
                "core_version": "6.0.0",
                "build_channel": channel,
                "build_id": "a" * 64,
                "source_fingerprint": "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    (root / "SHA256SUMS.txt").write_bytes(b"checksums\n")


def test_candidate_assessment_preserves_schema_two_support(tmp_path: Path) -> None:
    write_info(tmp_path / "release")
    result = assess_candidate(
        tmp_path / "release",
        evidence(),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=True),
        preflight_checker=lambda _root: SimpleNamespace(ready=True, errors=()),
    )

    assert result.ready
    assert "等待使用者決定是否包裝" in result.action


def test_candidate_assessment_accepts_matching_schema_three(tmp_path: Path) -> None:
    write_info(tmp_path / "release", schema_version=3)
    result = assess_candidate(
        tmp_path / "release",
        evidence(schema_version=3, tool_schema_version=3),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=True),
        preflight_checker=lambda _root: SimpleNamespace(ready=True, errors=()),
    )

    assert result.ready


@pytest.mark.parametrize(
    ("schema_version", "tool_schema_version"),
    ((2, 3), (3, 2), (4, 4)),
)
def test_candidate_evidence_rejects_mixed_or_unknown_schema(
    schema_version: int,
    tool_schema_version: int,
) -> None:
    with pytest.raises(ValueError, match="unsupported or inconsistent"):
        evidence(
            schema_version=schema_version,
            tool_schema_version=tool_schema_version,
        )


@pytest.mark.parametrize(
    ("evidence_schema", "release_schema"),
    ((2, 3), (3, 2)),
)
def test_candidate_assessment_rejects_mixed_supported_schemas(
    tmp_path: Path,
    evidence_schema: int,
    release_schema: int,
) -> None:
    write_info(tmp_path / "release", schema_version=release_schema)
    result = assess_candidate(
        tmp_path / "release",
        evidence(
            schema_version=evidence_schema,
            tool_schema_version=evidence_schema,
        ),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=True),
        preflight_checker=lambda _root: SimpleNamespace(ready=True, errors=()),
    )

    assert not result.ready
    assert "candidate evidence does not match schema_version" in result.blockers
    assert "candidate evidence does not match tool_schema_version" in result.blockers


@pytest.mark.parametrize(
    ("schema_version", "tool_schema_version"),
    ((4, 4), (3, 2)),
)
def test_candidate_assessment_rejects_unknown_or_inconsistent_release_schema(
    tmp_path: Path,
    schema_version: int,
    tool_schema_version: int,
) -> None:
    write_info(
        tmp_path / "release",
        schema_version=schema_version,
        tool_schema_version=tool_schema_version,
    )
    result = assess_candidate(
        tmp_path / "release",
        evidence(),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=True),
        preflight_checker=lambda _root: SimpleNamespace(ready=True, errors=()),
    )

    assert not result.ready
    assert (
        "candidate release metadata schema is unsupported or inconsistent"
        in result.blockers
    )


def test_candidate_assessment_blocks_quality_signing_and_wrong_channel(
    tmp_path: Path,
) -> None:
    write_info(tmp_path / "release", channel="preview")
    result = assess_candidate(
        tmp_path / "release",
        evidence(pytest=False, mod_wiring=False, p1_open=2),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=False),
        preflight_checker=lambda _root: SimpleNamespace(
            ready=False, errors=("Authenticode signature is not valid",)
        ),
    )

    assert not result.ready
    assert "candidate must come from a development build" in result.blockers
    assert "Pytest has not passed" in result.blockers
    assert "P1 issues remain open: 2" in result.blockers
    assert "MOD visibility and enablement audit has not passed" in result.blockers
    assert "不得包裝 Stable" in result.action


def test_candidate_evidence_is_strict() -> None:
    with pytest.raises(ValueError):
        CandidateEvidence.from_dict({"ruff": True})


def test_candidate_assessment_rejects_stale_or_different_build_evidence(
    tmp_path: Path,
) -> None:
    write_info(tmp_path / "release")
    result = assess_candidate(
        tmp_path / "release",
        evidence(release_build_id="c" * 64),
        suggested_stable_version="1.0.0",
        audit_checker=lambda _root: SimpleNamespace(valid=True),
        preflight_checker=lambda _root: SimpleNamespace(ready=True, errors=()),
    )

    assert not result.ready
    assert "candidate evidence does not match release_build_id" in result.blockers
