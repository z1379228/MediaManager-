"""Public, side-effect-free helpers for third-party MOD development."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import uuid

from core.localization import SUPPORTED_LOCALE_CODES
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.package_verifier import PackageVerifier
from core.plugins.ui_descriptor import PluginPage, PluginUIError
from core.version import CORE_VERSION, release_version


SUPPORTED_API_VERSIONS = frozenset({"1.0"})
SUPPORTED_RUNTIME_PROTOCOLS = frozenset({"1.0"})
SITE_TEMPLATE_SCHEMA = 2
_SITE_HOST = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_SITE_RUNTIME_POLICY = {
    "request_timeout_seconds": 30,
    "cancel_grace_seconds": 3,
    "terminate_process_tree": True,
}


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

    contract = validate_manifest_contract(manifest, core_version=core_version)
    errors = list(contract.errors)
    warnings = list(contract.warnings)
    if manifest.ui_descriptor:
        descriptor_path = path.parent / manifest.ui_descriptor
        try:
            if (
                descriptor_path.is_symlink()
                or not descriptor_path.is_file()
                or descriptor_path.stat().st_size > 100_000
            ):
                raise PluginUIError("UI descriptor is missing or unsafe")
            raw = json.loads(descriptor_path.read_text(encoding="utf-8"))
            page = PluginPage.from_dict(raw, locale="en")
            if page.schema_version == 2 and set(page.available_locales) != set(
                SUPPORTED_LOCALE_CODES
            ):
                warnings.append(
                    "localized UI does not provide all four supported locales"
                )
        except (OSError, UnicodeError, ValueError, PluginUIError) as error:
            errors.append(f"invalid declarative UI: {error}")
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


def _manifest_data(
    plugin_id: str,
    *,
    name: str,
    plugin_type: str = "processor",
    dependencies: tuple[str, ...] = (),
    permissions: tuple[str, ...] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 2,
        "id": plugin_id,
        "name": name,
        "version": "0.1.0",
        "publisher": "replace-with-your-publisher-id",
        "plugin_type": plugin_type,
        "entry_point": "" if plugin_type == "data-only" else "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": CORE_VERSION,
        "maximum_core_version": CORE_VERSION,
        "permissions": list(
            permissions
            if permissions is not None
            else (() if plugin_type == "data-only" else ("media.read",))
        ),
        "external_tools": [],
        "dependencies": list(dependencies),
        "files_manifest": "files.json",
        "signature": "plugin.sig",
        "runtime": "none" if plugin_type == "data-only" else "python-subprocess",
        "runtime_protocol": "none" if plugin_type == "data-only" else "1.0",
        "ui_descriptor": "ui.json",
    }
    manifest = PluginManifest.from_dict(data)
    result = {
        field: getattr(manifest, field) for field in manifest.__dataclass_fields__
    }
    for key in ("permissions", "external_tools", "dependencies"):
        result[key] = list(result[key])
    return result


def _localized_ui(plugin_id: str, name: str) -> dict[str, object]:
    translations = {
        "en": (name, "Unsigned development MOD. Review permissions before enabling."),
        "ja": (name, "未署名の開発用 MOD です。有効化する前に権限を確認してください。"),
        "zh-CN": (name, "这是未签名的开发 MOD；启用前请检查权限。"),
        "zh-TW": (name, "這是未簽署的開發用 MOD；啟用前請檢查權限。"),
    }
    return {
        "schema_version": 2,
        "page_id": plugin_id,
        "default_locale": "en",
        "translations": {
            locale: {
                "title": title,
                "blocks": [{"type": "text", "text": message}],
            }
            for locale, (title, message) in translations.items()
        },
    }


def _write_template(root: Path, data: dict[str, object], *, name: str) -> None:
    root.mkdir(parents=True)
    (root / "plugin.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "ui.json").write_text(
        json.dumps(_localized_ui(str(data["id"]), name), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    if data["plugin_type"] != "data-only":
        (root / "plugin.py").write_text(
            '"""Minimal MediaManager MOD entry point."""\n\n'
            "def handle_request(request: dict[str, object]) -> dict[str, object]:\n"
            "    return {\"ok\": True, \"request_id\": request.get(\"id\")}\n",
            encoding="utf-8",
        )
    (root / "README.md").write_text(
        f"# {name}\n\n"
        "Unsigned development template. Follow docs/mod-developer-guide.md.\n",
        encoding="utf-8",
    )


def _temporary_template_root(target: Path) -> Path:
    if target.exists():
        raise FileExistsError(f"template target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")


def create_mod_template(target: Path, plugin_id: str) -> Path:
    """Create an unsigned schema-v2 processor with four-locale declarative UI."""

    data = _manifest_data(plugin_id, name="Example MOD")
    temporary = _temporary_template_root(target)
    try:
        _write_template(temporary, data, name="Example MOD")
        temporary.replace(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return target


def create_site_mod_template(
    target: Path,
    parent_id: str,
    *,
    hosts: tuple[str, ...] = ("replace-with-owned-host.invalid",),
) -> Path:
    """Create one data-only parent and one dependent download child MOD."""

    normalized_hosts = tuple(host.strip().casefold() for host in hosts)
    if (
        not 1 <= len(normalized_hosts) <= 16
        or len(normalized_hosts) != len(set(normalized_hosts))
        or any(not _SITE_HOST.fullmatch(host) for host in normalized_hosts)
    ):
        raise ValueError("site MOD hosts must be unique canonical DNS names")
    child_id = f"{parent_id}.download"
    parent = _manifest_data(
        parent_id, name="Example Site Parent MOD", plugin_type="data-only"
    )
    child = _manifest_data(
        child_id,
        name="Example Site Download MOD",
        dependencies=(parent_id,),
        permissions=(f"network.{parent_id}", "media.write"),
    )
    temporary = _temporary_template_root(target)
    try:
        temporary.mkdir(parents=True)
        (temporary / "site-family.json").write_text(
            json.dumps(
                {
                    "schema_version": SITE_TEMPLATE_SCHEMA,
                    "parent": {"id": parent_id, "path": "parent"},
                    "children": [{"id": child_id, "path": "download"}],
                    "locales": list(SUPPORTED_LOCALE_CODES),
                    "host_ownership": list(normalized_hosts),
                    "runtime_policy": dict(_SITE_RUNTIME_POLICY),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _write_template(
            temporary / "parent", parent, name="Example Site Parent MOD"
        )
        _write_template(
            temporary / "download", child, name="Example Site Download MOD"
        )
        (temporary / "README.md").write_text(
            "# Example Site MOD Family\n\n"
            "Install and trust the parent before the dependent download child. "
            "This scaffold contains no signing key or generated signature.\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return target


def validate_site_mod_project(
    root: Path, *, core_version: str = CORE_VERSION
) -> ModValidationReport:
    """Validate a generated parent/child project without installing code."""

    try:
        descriptor = json.loads(
            (root / "site-family.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as error:
        return ModValidationReport(False, errors=(f"invalid site project: {error}",))
    if (
        not isinstance(descriptor, dict)
        or set(descriptor)
        != {
            "schema_version",
            "parent",
            "children",
            "locales",
            "host_ownership",
            "runtime_policy",
        }
        or descriptor.get("schema_version") != SITE_TEMPLATE_SCHEMA
        or descriptor.get("locales") != list(SUPPORTED_LOCALE_CODES)
        or not isinstance(descriptor.get("parent"), dict)
        or not isinstance(descriptor.get("children"), list)
        or len(descriptor["children"]) != 1
    ):
        return ModValidationReport(False, errors=("site project contract is invalid",))
    hosts = descriptor["host_ownership"]
    runtime_policy = descriptor["runtime_policy"]
    if (
        not isinstance(hosts, list)
        or not 1 <= len(hosts) <= 16
        or len(hosts) != len(set(hosts))
        or any(not isinstance(host, str) or not _SITE_HOST.fullmatch(host) for host in hosts)
        or runtime_policy != _SITE_RUNTIME_POLICY
    ):
        return ModValidationReport(
            False,
            errors=("site host ownership or runtime policy is invalid",),
        )
    parent = descriptor["parent"]
    child = descriptor["children"][0]
    if (
        set(parent) != {"id", "path"}
        or not isinstance(child, dict)
        or set(child) != {"id", "path"}
        or parent["path"] != "parent"
        or child["path"] != "download"
    ):
        return ModValidationReport(False, errors=("site project paths are invalid",))
    parent_path = root / "parent" / "plugin.json"
    child_path = root / "download" / "plugin.json"
    reports = (
        validate_mod_manifest(parent_path, core_version=core_version),
        validate_mod_manifest(child_path, core_version=core_version),
    )
    errors = [error for report in reports for error in report.errors]
    warnings = [warning for report in reports for warning in report.warnings]
    try:
        parent_manifest = PluginManifest.load(parent_path)
        child_manifest = PluginManifest.load(child_path)
        if (
            parent_manifest.id != parent["id"]
            or child_manifest.id != child["id"]
            or parent_manifest.plugin_type != "data-only"
            or child_manifest.dependencies != (parent_manifest.id,)
            or set(child_manifest.permissions)
            != {f"network.{parent_manifest.id}", "media.write"}
        ):
            errors.append("parent/child dependency contract is invalid")
        for path in (root / "parent" / "ui.json", root / "download" / "ui.json"):
            page = PluginPage.from_dict(
                json.loads(path.read_text(encoding="utf-8")), locale="en"
            )
            if set(page.available_locales) != set(SUPPORTED_LOCALE_CODES):
                errors.append("site MOD UI must provide exactly four locales")
    except (ManifestError, OSError, UnicodeError, ValueError, PluginUIError) as error:
        errors.append(f"site project validation failed: {error}")
    return ModValidationReport(
        not errors,
        str(parent.get("id") or ""),
        reports[0].plugin_version,
        tuple(errors),
        tuple(dict.fromkeys(warnings)),
    )
