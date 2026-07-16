from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_quality_workflow_keeps_hard_test_timeout() -> None:
    text = _workflow_text()

    assert "python -m pytest -vv -rs --timeout=60" in text
    assert "PYTEST_BASETEMP: .work/pytest-ci-${{ github.run_id }}" in text
    assert '--basetemp="$env:PYTEST_BASETEMP"' in text


def test_quality_workflow_runs_release_and_mod_audits() -> None:
    text = _workflow_text()

    required_commands = (
        "python -m tools.audit_versions --root Version",
        "python -m tools.audit_mod_groups",
        "python -m tools.site_quality_audit",
        "python -m tools.dependency_lock_audit",
        "audit_text_pollution.ps1",
    )
    for command in required_commands:
        assert command in text


def test_quality_workflow_is_read_only_for_pull_requests() -> None:
    text = _workflow_text()

    assert "pull_request:" in text
    assert "contents: read" in text
    assert "git push" not in text
