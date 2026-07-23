from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.localization import SUPPORTED_LOCALE_CODES
from core.plugins.developer import (
    create_mod_template,
    create_site_mod_template,
    validate_mod_manifest,
    validate_site_mod_project,
)
from core.version import CORE_VERSION


def test_create_template_is_schema_v2_and_valid_for_current_core(tmp_path: Path) -> None:
    target = create_mod_template(tmp_path / "sample", "sample.processor")
    report = validate_mod_manifest(target / "plugin.json")
    assert report.valid
    assert report.plugin_id == "sample.processor"
    manifest = json.loads((target / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["runtime"] == "python-subprocess"
    assert manifest["minimum_core_version"] == CORE_VERSION
    ui = json.loads((target / "ui.json").read_text(encoding="utf-8"))
    assert set(ui["translations"]) == set(SUPPORTED_LOCALE_CODES)


def test_site_template_has_valid_parent_child_and_four_locale_contract(
    tmp_path: Path,
) -> None:
    target = create_site_mod_template(tmp_path / "site", "example.site")
    report = validate_site_mod_project(target)

    assert report.valid
    assert report.plugin_id == "example.site"
    parent = json.loads((target / "parent" / "plugin.json").read_text(encoding="utf-8"))
    child = json.loads((target / "download" / "plugin.json").read_text(encoding="utf-8"))
    family = json.loads((target / "site-family.json").read_text(encoding="utf-8"))
    assert parent["plugin_type"] == "data-only"
    assert parent["runtime"] == "none"
    assert child["dependencies"] == ["example.site"]
    assert child["runtime"] == "python-subprocess"
    assert child["permissions"] == ["network.example.site", "media.write"]
    assert family["schema_version"] == 2
    assert family["host_ownership"] == ["replace-with-owned-host.invalid"]
    assert family["runtime_policy"] == {
        "request_timeout_seconds": 30,
        "cancel_grace_seconds": 3,
        "terminate_process_tree": True,
    }
    assert not (target / "parent" / "plugin.py").exists()
    assert not tuple(target.rglob("*.sig"))


def test_site_template_validation_detects_detached_child(tmp_path: Path) -> None:
    target = create_site_mod_template(tmp_path / "site", "example.site")
    path = target / "download" / "plugin.json"
    child = json.loads(path.read_text(encoding="utf-8"))
    child["dependencies"] = []
    path.write_text(json.dumps(child), encoding="utf-8")

    report = validate_site_mod_project(target)
    assert not report.valid
    assert "parent/child dependency" in " ".join(report.errors)


def test_site_template_validates_host_ownership_and_runtime_policy(
    tmp_path: Path,
) -> None:
    target = create_site_mod_template(
        tmp_path / "site",
        "example.site",
        hosts=("media.example.test", "cdn.example.test"),
    )
    descriptor_path = target / "site-family.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    assert descriptor["host_ownership"] == [
        "media.example.test",
        "cdn.example.test",
    ]

    descriptor["runtime_policy"]["terminate_process_tree"] = False
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    report = validate_site_mod_project(target)
    assert not report.valid
    assert "runtime policy" in " ".join(report.errors)

    with pytest.raises(ValueError, match="canonical DNS"):
        create_site_mod_template(
            tmp_path / "invalid-site",
            "invalid.site",
            hosts=("https://example.test/path",),
        )


def test_template_refuses_to_replace_existing_directory(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(FileExistsError):
        create_mod_template(target, "sample.processor")


def test_manifest_contract_rejects_unsupported_api(tmp_path: Path) -> None:
    target = create_mod_template(tmp_path / "sample", "sample.processor")
    path = target / "plugin.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["api_version"] = "99.0"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    report = validate_mod_manifest(path)
    assert not report.valid
    assert report.errors == ("unsupported API contract: 99.0",)
