"""Public, side-effect-free helpers for third-party MOD development."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.package_verifier import PackageVerifier
from core.version import CORE_VERSION, release_version


SUPPORTED_API_VERSIONS = frozenset({"1.0"})
SUPPORTED_RUNTIME_PROTOCOLS = frozenset({"1.0"})


@dataclass(frozen=True, slots=True)
class ModValidationReport:
    valid: bool
    plugin_id: str = ""
    plugin_version: str = ""
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def validate_mod_manifest(
    path: Path, *, core_version: str = CORE_VERSION
) -> ModValidationReport:
    """Validate syntax and contracts without installing or executing a MOD."""

    try:
        manifest = PluginManifest.load(path)
    except ManifestError as error:
        return ModValidationReport(False, errors=(str(error),))

    errors: list[str] = []
    warnings: list[str] = []
    current = release_version(core_version)
    minimum = release_version(manifest.minimum_core_version)
    maximum = release_version(manifest.maximum_core_version)
    if not minimum <= current <= maximum:
        errors.append(f"core {core_version} is outside the declared compatibility range")
    if manifest.api_version not in SUPPORTED_API_VERSIONS:
        errors.append(f"unsupported API contract: {manifest.api_version}")
    if (
        manifest.executable
        and manifest.runtime_protocol not in SUPPORTED_RUNTIME_PROTOCOLS
    ):
        errors.append(f"unsupported runtime protocol: {manifest.runtime_protocol}")
    if manifest.schema_version == 1 and manifest.executable:
        warnings.append("schema v1 executable MODs cannot be enabled by core 3.0")
    return ModValidationReport(
        not errors,
        manifest.id,
        manifest.version,
        tuple(errors),
        tuple(warnings),
    )


def validate_mod_package(
    path: Path, *, core_version: str = CORE_VERSION
) -> ModValidationReport:
    """Validate package inventory and embedded manifest without extraction."""

    verified = PackageVerifier().verify(path)
    if not verified.valid or verified.manifest is None:
        return ModValidationReport(False, errors=verified.errors)
    manifest = verified.manifest
    compatibility = validate_manifest_contract(manifest, core_version=core_version)
    return ModValidationReport(
        compatibility.valid,
        manifest.id,
        manifest.version,
        compatibility.errors,
        compatibility.warnings
        + ("publisher signature and trust are checked only during installation",),
    )


def validate_manifest_contract(
    manifest: PluginManifest, *, core_version: str = CORE_VERSION
) -> ModValidationReport:
    """Validate an already parsed manifest against the public core contracts."""

    current = release_version(core_version)
    errors: list[str] = []
    if not (
        release_version(manifest.minimum_core_version)
        <= current
        <= release_version(manifest.maximum_core_version)
    ):
        errors.append(f"core {core_version} is outside the declared compatibility range")
    if manifest.api_version not in SUPPORTED_API_VERSIONS:
        errors.append(f"unsupported API contract: {manifest.api_version}")
    if (
        manifest.executable
        and manifest.runtime_protocol not in SUPPORTED_RUNTIME_PROTOCOLS
    ):
        errors.append(f"unsupported runtime protocol: {manifest.runtime_protocol}")
    warnings = (
        ("schema v1 executable MODs cannot be enabled by core 3.0",)
        if manifest.schema_version == 1 and manifest.executable
        else ()
    )
    return ModValidationReport(
        not errors,
        manifest.id,
        manifest.version,
        tuple(errors),
        warnings,
    )


def create_mod_template(target: Path, plugin_id: str) -> Path:
    """Create a minimal unsigned schema-v2 processor template."""

    manifest = PluginManifest.from_dict(
        {
            "schema_version": 2,
            "id": plugin_id,
            "name": "Example MOD",
            "version": "0.1.0",
            "publisher": "replace-with-your-publisher-id",
            "plugin_type": "processor",
            "entry_point": "plugin.py",
            "api_version": "1.0",
            "minimum_core_version": "3.0.0",
            "maximum_core_version": "3.0.0",
            "permissions": ["media.read"],
            "external_tools": [],
            "dependencies": [],
            "files_manifest": "files.json",
            "signature": "plugin.sig",
            "runtime": "python-subprocess",
            "runtime_protocol": "1.0",
            "ui_descriptor": "",
        }
    )
    if target.exists():
        raise FileExistsError(f"template target already exists: {target}")
    target.mkdir(parents=True)
    data = {
        field: getattr(manifest, field)
        for field in manifest.__dataclass_fields__
    }
    for key in ("permissions", "external_tools", "dependencies"):
        data[key] = list(data[key])
    (target / "plugin.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "plugin.py").write_text(
        '"""Minimal MediaManager MOD entry point."""\n\n'
        "def handle_request(request: dict[str, object]) -> dict[str, object]:\n"
        "    return {\"ok\": True, \"request_id\": request.get(\"id\")}\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "# Example MOD\n\nUnsigned development template. Follow docs/mod-developer-guide.md.\n",
        encoding="utf-8",
    )
    return target
