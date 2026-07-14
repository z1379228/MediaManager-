"""Side-effect-free third-party adapter project validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from contracts.adapter_manifest_v1 import AdapterManifestError, AdapterManifestV1
from core.version import CORE_VERSION, release_version


@dataclass(frozen=True, slots=True)
class AdapterCompatibilityReport:
    valid: bool
    adapter_id: str = ""
    adapter_type: str = ""
    core_version: str = CORE_VERSION
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    external_tools: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_adapter_project(
    root: Path, *, core_version: str = CORE_VERSION
) -> AdapterCompatibilityReport:
    root = root.resolve()
    manifest_path = root / "adapter.json"
    try:
        if root.is_symlink() or not root.is_dir():
            raise AdapterManifestError("adapter root is unavailable or unsafe")
        if manifest_path.stat().st_size > 128 * 1024:
            raise AdapterManifestError("adapter manifest is too large")
        raw = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        manifest = AdapterManifestV1.from_dict(raw)
        entry = (root / manifest.entry_point).resolve()
        if (
            not entry.is_relative_to(root)
            or not entry.is_file()
            or entry.is_symlink()
            or entry.stat().st_size > 1024 * 1024
        ):
            raise AdapterManifestError("adapter entry point is unsafe")
    except (OSError, ValueError, AdapterManifestError) as error:
        return AdapterCompatibilityReport(False, core_version=core_version, errors=(str(error),))
    current = release_version(core_version)
    compatible = (
        release_version(manifest.minimum_core_version)
        <= current
        <= release_version(manifest.maximum_core_version)
    )
    errors = () if compatible else (f"core {core_version} is outside compatibility range",)
    warnings = (
        "offline validation does not install, trust, sign, or execute the adapter",
    )
    return AdapterCompatibilityReport(
        not errors,
        manifest.adapter_id,
        manifest.adapter_type,
        core_version,
        errors,
        warnings,
        tuple(item.name for item in manifest.external_tools),
        tuple(item.name for item in manifest.dependencies),
    )


def create_adapter_template(root: Path, adapter_id: str, adapter_type: str) -> Path:
    if root.exists():
        raise FileExistsError(f"adapter target already exists: {root}")
    if adapter_type not in {"search", "download"}:
        raise ValueError("adapter type must be search or download")
    capability = (
        {
            "provider_id": adapter_id,
            "sites": ["example"],
            "content_types": ["all", "video"],
            "max_page_size": 20,
            "pagination": "none",
            "audio_preview": False,
            "video_preview": False,
        }
        if adapter_type == "search"
        else {
            "provider_id": adapter_id,
            "sites": ["example"],
            "format_presets": ["best"],
            "subtitle_modes": ["none"],
            "timed_comments": ["none"],
            "supports_playlist": False,
            "supports_segments": False,
            "supports_resume": True,
            "max_batch_size": 20,
        }
    )
    manifest = {
        "schema_version": 1,
        "adapter_id": adapter_id,
        "display_name": "Example Adapter",
        "adapter_type": adapter_type,
        "entry_point": "adapter.py",
        "minimum_core_version": "4.2.0",
        "maximum_core_version": "6.0.0",
        "permissions": ["network.public"],
        "external_tools": [],
        "dependencies": [],
        "capability": capability,
    }
    AdapterManifestV1.from_dict(manifest)
    root.mkdir(parents=True)
    (root / "adapter.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "adapter.py").write_text(
        '"""Unsigned example adapter; package and sign before installation."""\n',
        encoding="utf-8",
    )
    return root
