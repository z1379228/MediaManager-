"""Versioned provider capability contract validated by core self-check.

The contract is intentionally declarative: it describes what a provider may
offer, not how a website is accessed.  Unknown operations are rejected so a
manifest cannot silently grant a new network or playback behaviour.  Trusted UI
and MOD routing may adopt it later; this module does not claim that wiring exists.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CAPABILITY_SCHEMA_VERSION = 1

SUPPORTED_OPERATIONS = frozenset(
    {
        "search",
        "preview",
        "download",
        "playlist",
        "subtitles",
        "timed-comments",
        "offline-archive",
        "local-playback",
    }
)

BUILTIN_PROVIDER_CAPABILITY_IDS = frozenset(
    {"youtube", "generic-ytdlp", "bilibili", "facebook", "mega", "direct-http"}
)


class ProviderCapabilityError(ValueError):
    """Raised when a provider capability declaration is unsafe or malformed."""


@dataclass(frozen=True, slots=True)
class ProviderCapabilityV1:
    """Conservative capability declaration for one provider or parent MOD."""

    provider_id: str
    sites: tuple[str, ...]
    operations: tuple[str, ...]
    requires_official_page: bool
    supports_local_playback: bool
    supports_offline_archive: bool
    max_batch_size: int
    schema_version: int = CAPABILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_SCHEMA_VERSION:
            raise ProviderCapabilityError("provider capability schema version invalid")
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise ProviderCapabilityError("provider id invalid")
        for values, label in ((self.sites, "sites"), (self.operations, "operations")):
            if (
                not isinstance(values, tuple)
                or not values
                or len(values) != len(set(values))
                or not all(isinstance(item, str) and item for item in values)
            ):
                raise ProviderCapabilityError(f"provider {label} invalid")
        if not set(self.operations) <= SUPPORTED_OPERATIONS:
            raise ProviderCapabilityError("provider operation is unsupported")
        if any(
            not isinstance(value, bool)
            for value in (
                self.requires_official_page,
                self.supports_local_playback,
                self.supports_offline_archive,
            )
        ):
            raise ProviderCapabilityError("provider capability flags invalid")
        if (
            not isinstance(self.max_batch_size, int)
            or isinstance(self.max_batch_size, bool)
            or not 1 <= self.max_batch_size <= 500
        ):
            raise ProviderCapabilityError("provider batch size invalid")
        if self.supports_local_playback and "local-playback" not in self.operations:
            raise ProviderCapabilityError("local playback operation is missing")
        if self.supports_offline_archive and "offline-archive" not in self.operations:
            raise ProviderCapabilityError("offline archive operation is missing")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe declaration for audits and UI snapshots."""

        payload = asdict(self)
        payload["sites"] = list(self.sites)
        payload["operations"] = list(self.operations)
        return payload

    @classmethod
    def from_dict(cls, raw: object) -> "ProviderCapabilityV1":
        if not isinstance(raw, dict):
            raise ProviderCapabilityError("provider capability payload invalid")
        required = {
            "provider_id",
            "sites",
            "operations",
            "requires_official_page",
            "supports_local_playback",
            "supports_offline_archive",
            "max_batch_size",
            "schema_version",
        }
        if set(raw) != required:
            raise ProviderCapabilityError("provider capability fields invalid")
        if not isinstance(raw["sites"], list) or not isinstance(raw["operations"], list):
            raise ProviderCapabilityError("provider capability lists invalid")
        return cls(
            provider_id=raw["provider_id"],
            sites=tuple(raw["sites"]),
            operations=tuple(raw["operations"]),
            requires_official_page=raw["requires_official_page"],
            supports_local_playback=raw["supports_local_playback"],
            supports_offline_archive=raw["supports_offline_archive"],
            max_batch_size=raw["max_batch_size"],
            schema_version=raw["schema_version"],
        )
