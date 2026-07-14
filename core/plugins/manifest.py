"""Strict MOD manifest parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from contracts.capabilities import is_valid_capability

_ID = re.compile(r"^[a-z][a-z0-9.-]{1,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_PROTOCOL_VERSION = re.compile(r"^\d+\.\d+$")
PLUGIN_TYPES = frozenset({"platform", "ui", "theme", "processor", "exporter", "filter", "notification", "data-only"})


class ManifestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PluginManifest:
    schema_version: int
    id: str
    name: str
    version: str
    publisher: str
    plugin_type: str
    entry_point: str
    api_version: str
    minimum_core_version: str
    maximum_core_version: str
    permissions: tuple[str, ...]
    external_tools: tuple[str, ...]
    dependencies: tuple[str, ...]
    files_manifest: str
    signature: str
    runtime: str = "legacy-python"
    runtime_protocol: str = "1.0"
    ui_descriptor: str = ""

    @property
    def executable(self) -> bool:
        return self.runtime in {"legacy-python", "python-subprocess"}

    @property
    def execution_ready(self) -> bool:
        return (
            self.schema_version == 2
            and self.runtime == "python-subprocess"
            and self.runtime_protocol == "1.0"
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PluginManifest":
        if not isinstance(raw, dict):
            raise ManifestError("manifest must be an object")
        schema_version = raw.get("schema_version")
        common = {
            "schema_version",
            "id",
            "name",
            "version",
            "publisher",
            "plugin_type",
            "entry_point",
            "api_version",
            "minimum_core_version",
            "maximum_core_version",
            "permissions",
            "external_tools",
            "dependencies",
            "files_manifest",
            "signature",
        }
        required = (
            common | {"runtime", "runtime_protocol", "ui_descriptor"}
            if schema_version == 2
            else common
        )
        missing = required - raw.keys()
        unknown = raw.keys() - required
        if missing or unknown:
            raise ManifestError(f"manifest fields invalid; missing={sorted(missing)}, unknown={sorted(unknown)}")
        if schema_version not in {1, 2} or not _ID.fullmatch(str(raw["id"])):
            raise ManifestError("unsupported schema or invalid plugin id")
        if not _VERSION.fullmatch(str(raw["version"])) or raw["plugin_type"] not in PLUGIN_TYPES:
            raise ManifestError("invalid version or plugin type")
        if not all(
            _RELEASE_VERSION.fullmatch(str(raw[key]))
            for key in ("minimum_core_version", "maximum_core_version")
        ):
            raise ManifestError("invalid core compatibility version")
        minimum = tuple(int(part) for part in raw["minimum_core_version"].split("."))
        maximum = tuple(int(part) for part in raw["maximum_core_version"].split("."))
        if minimum > maximum:
            raise ManifestError("minimum core version exceeds maximum")
        entry_value = str(raw["entry_point"])
        entry = PurePosixPath(entry_value)
        if raw["plugin_type"] == "data-only":
            if entry_value:
                raise ManifestError("data-only plugins cannot have an entry point")
        elif entry.is_absolute() or ".." in entry.parts or entry.suffix != ".py":
            raise ManifestError("unsafe entry point")
        permissions = tuple(raw["permissions"])
        if len(permissions) != len(set(permissions)) or not all(isinstance(item, str) and is_valid_capability(item) for item in permissions):
            raise ManifestError("invalid, duplicate, or forbidden permission")
        dependencies = tuple(raw["dependencies"])
        if (
            not all(isinstance(item, str) and _ID.fullmatch(item) for item in dependencies)
            or str(raw["id"]) in dependencies
            or len(dependencies) != len(set(dependencies))
        ):
            raise ManifestError("invalid, duplicate, or self dependency")
        values = dict(raw)
        if schema_version == 1:
            values.update(
                runtime=(
                    "none"
                    if raw["plugin_type"] == "data-only"
                    else "legacy-python"
                ),
                runtime_protocol=(
                    "none" if raw["plugin_type"] == "data-only" else "1.0"
                ),
                ui_descriptor="",
            )
        runtime = values["runtime"]
        runtime_protocol = values["runtime_protocol"]
        ui_descriptor = values["ui_descriptor"]
        if schema_version == 2:
            if raw["plugin_type"] == "data-only":
                if runtime != "none" or runtime_protocol != "none":
                    raise ManifestError("data-only runtime must be none")
            elif runtime != "python-subprocess" or not _PROTOCOL_VERSION.fullmatch(
                str(runtime_protocol)
            ):
                raise ManifestError("executable plugin runtime is invalid")
        descriptor = PurePosixPath(str(ui_descriptor))
        if ui_descriptor and (
            descriptor.is_absolute()
            or ".." in descriptor.parts
            or descriptor.suffix != ".json"
        ):
            raise ManifestError("unsafe UI descriptor")
        for key in ("permissions", "external_tools", "dependencies"):
            if not isinstance(values[key], list) or not all(isinstance(item, str) for item in values[key]):
                raise ManifestError(f"{key} must be a string list")
            values[key] = tuple(values[key])
        return cls(**values)

    @classmethod
    def load(cls, path: Path) -> "PluginManifest":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ManifestError(f"cannot read manifest: {error}") from error
        if not isinstance(raw, dict):
            raise ManifestError("manifest must be an object")
        return cls.from_dict(raw)
