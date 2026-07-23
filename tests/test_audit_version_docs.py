from pathlib import Path

from tools.audit_version_docs import audit_version_docs, main


ROOT = Path(__file__).parents[1]


def _write_repository(
    root: Path,
    *,
    core_version: str = "32.1.0",
    project_version: str = "32.1.0",
    readme_version: str = "32.1.0",
) -> None:
    (root / "core").mkdir()
    (root / "docs").mkdir()
    generation = core_version.rsplit(".", 1)[0]
    (root / "core/version.py").write_text(
        f'CORE_VERSION = "{core_version}"\n'
        f'DEVELOPMENT_GENERATION = "{generation}"\n',
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        f'[project]\nversion = "{project_version}"\n', encoding="utf-8"
    )
    documented_generation = readme_version.rsplit(".", 1)[0]
    declaration = (
        f"目前來源版本為開發版 {documented_generation}"
        f"（核心相容版本 {readme_version}）\n"
    )
    (root / "README.md").write_text(declaration, encoding="utf-8")
    (root / "docs/README.md").write_text(
        f"- {declaration}", encoding="utf-8"
    )


def test_repository_version_documentation_is_consistent() -> None:
    report = audit_version_docs(ROOT)

    assert report.valid, report.errors
    assert report.checked == 4
    assert report.core_version == "39.0.10"


def test_audit_rejects_canonical_source_mismatch(tmp_path: Path) -> None:
    _write_repository(tmp_path, project_version="32.0.0")

    report = audit_version_docs(tmp_path)

    assert not report.valid
    assert any("canonical version mismatch" in error for error in report.errors)


def test_audit_rejects_stale_current_documentation(tmp_path: Path) -> None:
    _write_repository(tmp_path, readme_version="29.3.0")

    report = audit_version_docs(tmp_path)

    assert not report.valid
    assert sum("version mismatch" in error for error in report.errors) == 4


def test_audit_rejects_duplicate_current_version_declaration(
    tmp_path: Path,
) -> None:
    _write_repository(tmp_path)
    with (tmp_path / "README.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "目前來源版本為開發版 29.3（核心相容版本 29.3.0）\n"
        )

    report = audit_version_docs(tmp_path)

    assert not report.valid
    assert any("found 2" in error for error in report.errors)


def test_cli_returns_nonzero_for_documentation_divergence(
    tmp_path: Path,
) -> None:
    _write_repository(tmp_path, readme_version="29.3.0")

    assert main(["--root", str(tmp_path)]) == 1


def test_audit_reports_invalid_utf8_document(tmp_path: Path) -> None:
    _write_repository(tmp_path)
    (tmp_path / "docs/README.md").write_bytes(b"\xff")

    report = audit_version_docs(tmp_path)

    assert not report.valid
    assert any("docs/README.md cannot be read" in error for error in report.errors)
