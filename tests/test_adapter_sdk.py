from __future__ import annotations

import json
from pathlib import Path

from core.adapters.developer import (
    create_adapter_template,
    validate_adapter_catalog,
    validate_adapter_project,
)


def test_search_and_download_templates_validate_offline(tmp_path: Path) -> None:
    search = create_adapter_template(
        tmp_path / "search", "example.search", "search"
    )
    download = create_adapter_template(
        tmp_path / "download", "example.download", "download"
    )

    search_report = validate_adapter_project(search, core_version="4.2.0")
    download_report = validate_adapter_project(download, core_version="4.2.0")

    assert search_report.valid and search_report.adapter_type == "search"
    assert download_report.valid and download_report.adapter_type == "download"
    assert "does not install" in search_report.warnings[0]


def test_new_template_supports_current_core_by_default(tmp_path: Path) -> None:
    root = create_adapter_template(
        tmp_path / "adapter", "example.search", "search"
    )

    assert validate_adapter_project(root).valid


def test_adapter_catalog_reports_each_project_and_duplicate_ids(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    create_adapter_template(catalog / "one", "example.search", "search")
    create_adapter_template(catalog / "two", "example.search", "search")
    invalid = catalog / "invalid"
    invalid.mkdir()
    (invalid / "adapter.json").write_text("{}", encoding="utf-8")

    report = validate_adapter_catalog(catalog)

    assert not report.valid
    assert report.checked == 3
    assert report.compatible == 2
    assert "duplicate adapter ids" in report.errors[0]
    assert sum(not item.valid for item in report.reports) == 1


def test_adapter_catalog_is_bounded_before_validation(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    for index in range(3):
        (catalog / str(index)).mkdir()

    report = validate_adapter_catalog(catalog, max_projects=2)

    assert not report.valid and report.checked == 0
    assert "exceeds 2" in report.errors[0]


def test_adapter_capability_and_identity_must_match(tmp_path: Path) -> None:
    root = create_adapter_template(
        tmp_path / "adapter", "example.search", "search"
    )
    manifest_path = root / "adapter.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["capability"]["provider_id"] = "other.search"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_adapter_project(root, core_version="4.2.0")

    assert not report.valid
    assert "provider mismatch" in report.errors[0]


def test_adapter_rejects_undeclared_powerful_permission(tmp_path: Path) -> None:
    root = create_adapter_template(
        tmp_path / "adapter", "example.download", "download"
    )
    manifest_path = root / "adapter.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"].append("credentials.read")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_adapter_project(root, core_version="4.2.0")

    assert not report.valid
    assert "permissions" in report.errors[0]


def test_adapter_report_lists_declared_dependencies(tmp_path: Path) -> None:
    root = create_adapter_template(
        tmp_path / "adapter", "example.download", "download"
    )
    manifest_path = root / "adapter.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["external_tools"] = [
        {"name": "ffmpeg", "minimum_version": "7.0", "required": True}
    ]
    manifest["dependencies"] = [
        {"name": "example-lib", "minimum_version": "1.0", "required": False}
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_adapter_project(root, core_version="4.2.0")

    assert report.valid
    assert report.external_tools == ("ffmpeg",)
    assert report.dependencies == ("example-lib",)
