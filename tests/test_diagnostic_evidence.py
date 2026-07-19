from __future__ import annotations

import json

import pytest

from contracts.diagnostic_evidence_v1 import DiagnosticEvidenceV1
from core.self_check import SelfCheckReport


def _report(run_id: str = "a" * 32) -> SelfCheckReport:
    return SelfCheckReport(
        1,
        "37.0.0",
        "development",
        (),
        "2026-07-18T19:12:17+00:00",
        run_id,
    )


def test_diagnostic_evidence_normalizes_only_allowlisted_metadata() -> None:
    report = _report()
    evidence = DiagnosticEvidenceV1.from_observation(
        run_id=report.run_id,
        component="wer",
        observed_at="2026-07-18T19:12:17+00:00",
        exit_code=-2_147_483_645,
        faulting_module=r"C:\Users\Alice\Private\Qt6Core.dll",
        faulting_offset="0X00000000000000AB",
        artifact_sha256="b" * 64,
    )

    document = evidence.to_dict()

    assert document == {
        "schema_version": 1,
        "run_id": report.run_id,
        "component": "wer",
        "observed_at": "2026-07-18T19:12:17Z",
        "exit_code": "0x80000003",
        "faulting_module": "qt6core.dll",
        "faulting_offset": "0xab",
        "artifact_sha256": "b" * 64,
    }
    serialized = json.dumps(document, separators=(",", ":"), ensure_ascii=True)
    assert len(serialized.encode("utf-8")) <= 1024
    assert "Alice" not in serialized
    assert "Private" not in serialized
    assert "\\" not in document["faulting_module"]


def test_diagnostic_evidence_reader_is_strict() -> None:
    valid = {
        "schema_version": 1,
        "run_id": "a" * 32,
        "component": "provider",
        "observed_at": "2026-07-18T19:12:17Z",
        "exit_code": "0x00000017",
        "faulting_module": None,
        "faulting_offset": None,
        "artifact_sha256": None,
    }

    assert DiagnosticEvidenceV1.from_dict(valid).to_dict() == valid
    with pytest.raises(ValueError, match="fields"):
        DiagnosticEvidenceV1.from_dict({**valid, "detail": "secret"})
    with pytest.raises(ValueError, match="faulting module"):
        DiagnosticEvidenceV1.from_dict(
            {**valid, "faulting_module": r"C:\Users\Alice\module.dll"}
        )
    with pytest.raises(ValueError, match="UTC"):
        DiagnosticEvidenceV1.from_dict(
            {**valid, "observed_at": "2026-07-18T19:12:17+08:00"}
        )


def test_self_check_attaches_only_matching_bounded_evidence() -> None:
    report = _report()
    evidence = DiagnosticEvidenceV1.from_observation(
        run_id=report.run_id,
        component="provider",
        observed_at="2026-07-18T19:12:17Z",
        exit_code=23,
    )

    attached = report.with_diagnostic_evidence(evidence)
    document = json.loads(attached.to_json())

    assert document["schema_version"] == 1
    assert document["diagnostic_evidence"] == [evidence.to_dict()]
    other = DiagnosticEvidenceV1.from_observation(
        run_id="f" * 32,
        component="provider",
        observed_at="2026-07-18T19:12:17Z",
        exit_code=23,
    )
    with pytest.raises(ValueError, match="run_id"):
        report.with_diagnostic_evidence(other)


def test_self_check_rejects_duck_typed_or_mutable_evidence() -> None:
    class FakeEvidence:
        run_id = "a" * 32

        @staticmethod
        def to_dict() -> dict[str, str]:
            return {"detail": r"C:\Users\Alice\Private\dump.dmp"}

    with pytest.raises(TypeError, match="DiagnosticEvidenceV1"):
        _report().with_diagnostic_evidence(FakeEvidence())
    with pytest.raises(TypeError, match="tuple"):
        SelfCheckReport(
            1,
            "37.0.0",
            "development",
            (),
            "2026-07-18T19:12:17+00:00",
            "a" * 32,
            [],
        )


def test_diagnostic_evidence_module_has_no_io_or_process_surface() -> None:
    import contracts.diagnostic_evidence_v1 as evidence_module

    assert "os" not in evidence_module.__dict__
    assert "socket" not in evidence_module.__dict__
    assert "subprocess" not in evidence_module.__dict__
