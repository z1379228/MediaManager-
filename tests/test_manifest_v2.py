from __future__ import annotations

import pytest

from core.plugins.manifest import ManifestError, PluginManifest


def manifest_v2(**changes):
    raw = {
        "schema_version": 2,
        "id": "example.plugin",
        "name": "Example",
        "version": "2.0.0",
        "publisher": "example.publisher",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "2.0.0",
        "maximum_core_version": "2.9.9",
        "permissions": ["media.read"],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
        "runtime": "python-subprocess",
        "runtime_protocol": "1.0",
        "ui_descriptor": "ui.json",
    }
    raw.update(changes)
    return raw


def test_manifest_v2_declares_runtime_and_ui_descriptor() -> None:
    manifest = PluginManifest.from_dict(manifest_v2())
    assert manifest.execution_ready
    assert manifest.ui_descriptor == "ui.json"


def test_manifest_v2_rejects_unknown_privileged_field() -> None:
    with pytest.raises(ManifestError, match="unknown"):
        PluginManifest.from_dict(
            manifest_v2(unexpected_privileged_field=True)
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("runtime", "native", "runtime"),
        ("runtime_protocol", "latest", "runtime"),
        ("ui_descriptor", "../ui.json", "UI descriptor"),
    ],
)
def test_manifest_v2_rejects_unsafe_runtime_declarations(
    field: str, value: str, message: str
) -> None:
    with pytest.raises(ManifestError, match=message):
        PluginManifest.from_dict(manifest_v2(**{field: value}))


def test_data_only_manifest_v2_has_no_runtime() -> None:
    manifest = PluginManifest.from_dict(
        manifest_v2(
            plugin_type="data-only",
            entry_point="",
            runtime="none",
            runtime_protocol="none",
            ui_descriptor="",
        )
    )
    assert not manifest.executable
    assert not manifest.execution_ready
