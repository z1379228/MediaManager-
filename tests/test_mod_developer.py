from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.plugins.developer import create_mod_template, validate_mod_manifest


def test_create_template_is_schema_v2_and_valid_for_core_3(tmp_path: Path) -> None:
    target = create_mod_template(tmp_path / "sample", "sample.processor")
    report = validate_mod_manifest(target / "plugin.json", core_version="3.0.0")
    assert report.valid
    assert report.plugin_id == "sample.processor"
    assert json.loads((target / "plugin.json").read_text(encoding="utf-8"))[
        "runtime"
    ] == "python-subprocess"


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
    report = validate_mod_manifest(path, core_version="3.0.0")
    assert not report.valid
    assert report.errors == ("unsupported API contract: 99.0",)
