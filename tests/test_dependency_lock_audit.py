from pathlib import Path

from tools.dependency_lock_audit import audit_dependency_lock


ROOT = Path(__file__).parents[1]


def test_repository_dependency_lock_matches_environment() -> None:
    report = audit_dependency_lock(ROOT)

    assert report.valid, report.errors
    assert report.checked >= 8


def test_dependency_lock_requires_exact_pin(tmp_path: Path) -> None:
    (tmp_path / "requirements-lock.txt").write_text(
        "pytest>=9\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies=["pytest>=9"]\n', encoding="utf-8"
    )

    report = audit_dependency_lock(tmp_path)

    assert not report.valid
    assert "not an exact pin" in report.errors[0]
