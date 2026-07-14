"""Offline manifest contract for third-party Search/Download adapters."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from contracts.download_capability_v2 import DownloadCapabilityV2
from contracts.search_v2 import SearchCapabilityV2
from core.version import release_version


_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{2,63}$")
_TOOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


class AdapterManifestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdapterDependencyV1:
    name: str
    minimum_version: str
    required: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AdapterDependencyV1":
        if not isinstance(raw, dict) or set(raw) != {
            "name",
            "minimum_version",
            "required",
        }:
            raise AdapterManifestError("adapter dependency fields invalid")
        if (
            not isinstance(raw["name"], str)
            or not _TOOL.fullmatch(raw["name"])
            or not isinstance(raw["minimum_version"], str)
            or len(raw["minimum_version"]) > 32
            or not isinstance(raw["required"], bool)
        ):
            raise AdapterManifestError("adapter dependency values invalid")
        return cls(raw["name"], raw["minimum_version"], raw["required"])


@dataclass(frozen=True, slots=True)
class AdapterManifestV1:
    adapter_id: str
    display_name: str
    adapter_type: str
    entry_point: str
    minimum_core_version: str
    maximum_core_version: str
    permissions: tuple[str, ...]
    external_tools: tuple[AdapterDependencyV1, ...]
    dependencies: tuple[AdapterDependencyV1, ...]
    capability: SearchCapabilityV2 | DownloadCapabilityV2

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AdapterManifestV1":
        required = {
            "schema_version",
            "adapter_id",
            "display_name",
            "adapter_type",
            "entry_point",
            "minimum_core_version",
            "maximum_core_version",
            "permissions",
            "external_tools",
            "dependencies",
            "capability",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise AdapterManifestError("adapter manifest fields invalid")
        if raw["schema_version"] != 1:
            raise AdapterManifestError("adapter schema version unsupported")
        adapter_id = raw["adapter_id"]
        adapter_type = raw["adapter_type"]
        if not isinstance(adapter_id, str) or not _ID.fullmatch(adapter_id):
            raise AdapterManifestError("adapter id invalid")
        if adapter_type not in {"search", "download"}:
            raise AdapterManifestError("adapter type invalid")
        if (
            not isinstance(raw["display_name"], str)
            or not 1 <= len(raw["display_name"]) <= 100
            or not isinstance(raw["entry_point"], str)
            or not raw["entry_point"].endswith(".py")
            or len(raw["entry_point"]) > 120
        ):
            raise AdapterManifestError("adapter identity invalid")
        try:
            minimum = release_version(raw["minimum_core_version"])
            maximum = release_version(raw["maximum_core_version"])
        except (TypeError, ValueError) as error:
            raise AdapterManifestError("adapter core versions invalid") from error
        if minimum > maximum:
            raise AdapterManifestError("adapter core version range invalid")
        permissions = raw["permissions"]
        allowed = {
            "search": {"network.public", "process.javascript"},
            "download": {
                "network.public",
                "storage.downloads.write",
                "process.ffmpeg",
                "process.javascript",
            },
        }[adapter_type]
        if (
            not isinstance(permissions, list)
            or len(permissions) > 8
            or len(permissions) != len(set(permissions))
            or not all(isinstance(item, str) and item in allowed for item in permissions)
        ):
            raise AdapterManifestError("adapter permissions invalid")
        external_tools = cls._dependencies(raw["external_tools"], "external tools")
        dependencies = cls._dependencies(raw["dependencies"], "dependencies")
        try:
            capability = (
                SearchCapabilityV2.from_dict(raw["capability"])
                if adapter_type == "search"
                else DownloadCapabilityV2.from_dict(raw["capability"])
            )
        except ValueError as error:
            raise AdapterManifestError(f"adapter capability invalid: {error}") from error
        if capability.provider_id != adapter_id:
            raise AdapterManifestError("adapter capability provider mismatch")
        return cls(
            adapter_id,
            raw["display_name"],
            adapter_type,
            raw["entry_point"],
            raw["minimum_core_version"],
            raw["maximum_core_version"],
            tuple(permissions),
            external_tools,
            dependencies,
            capability,
        )

    @staticmethod
    def _dependencies(raw: object, label: str) -> tuple[AdapterDependencyV1, ...]:
        if not isinstance(raw, list) or len(raw) > 16:
            raise AdapterManifestError(f"adapter {label} invalid")
        values = tuple(AdapterDependencyV1.from_dict(item) for item in raw)
        if len({item.name.casefold() for item in values}) != len(values):
            raise AdapterManifestError(f"adapter {label} duplicated")
        return values
