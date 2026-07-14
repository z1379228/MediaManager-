"""Download MOD capability negotiation contract for MediaManager 4.x."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.media_options_v1 import FORMAT_PRESET_IDS_V1, SUBTITLE_MODES_V1


class DownloadCapabilityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DownloadCapabilityV2:
    provider_id: str
    sites: tuple[str, ...]
    format_presets: tuple[str, ...]
    subtitle_modes: tuple[str, ...]
    timed_comments: tuple[str, ...]
    supports_playlist: bool
    supports_segments: bool
    supports_resume: bool
    max_batch_size: int

    def __post_init__(self) -> None:
        list_fields = (
            self.sites,
            self.format_presets,
            self.subtitle_modes,
            self.timed_comments,
        )
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise DownloadCapabilityError("download provider id invalid")
        if any(
            not isinstance(values, tuple)
            or not values
            or len(values) != len(set(values))
            or not all(isinstance(item, str) and item for item in values)
            for values in list_fields
        ):
            raise DownloadCapabilityError("download capability lists invalid")
        if not set(self.format_presets) <= set(FORMAT_PRESET_IDS_V1):
            raise DownloadCapabilityError("download format capability invalid")
        if not set(self.subtitle_modes) <= set(SUBTITLE_MODES_V1):
            raise DownloadCapabilityError("download subtitle capability invalid")
        if not set(self.timed_comments) <= {"none", "source", "ass"}:
            raise DownloadCapabilityError("timed comment capability invalid")
        if any(
            not isinstance(value, bool)
            for value in (
                self.supports_playlist,
                self.supports_segments,
                self.supports_resume,
            )
        ):
            raise DownloadCapabilityError("download capability flags invalid")
        if (
            not isinstance(self.max_batch_size, int)
            or isinstance(self.max_batch_size, bool)
            or not 1 <= self.max_batch_size <= 500
        ):
            raise DownloadCapabilityError("download batch capability invalid")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DownloadCapabilityV2":
        required = {
            "provider_id", "sites", "format_presets", "subtitle_modes",
            "timed_comments", "supports_playlist", "supports_segments",
            "supports_resume", "max_batch_size",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise DownloadCapabilityError("download capability fields invalid")
        list_fields = ("sites", "format_presets", "subtitle_modes", "timed_comments")
        if not isinstance(raw["provider_id"], str) or not raw["provider_id"]:
            raise DownloadCapabilityError("download provider id invalid")
        if any(
            not isinstance(raw[field], list)
            or not raw[field]
            or len(raw[field]) != len(set(raw[field]))
            or not all(isinstance(item, str) and item for item in raw[field])
            for field in list_fields
        ):
            raise DownloadCapabilityError("download capability lists invalid")
        if not set(raw["format_presets"]) <= set(FORMAT_PRESET_IDS_V1):
            raise DownloadCapabilityError("download format capability invalid")
        if not set(raw["subtitle_modes"]) <= set(SUBTITLE_MODES_V1):
            raise DownloadCapabilityError("download subtitle capability invalid")
        if not set(raw["timed_comments"]) <= {"none", "source", "ass"}:
            raise DownloadCapabilityError("timed comment capability invalid")
        if any(not isinstance(raw[field], bool) for field in (
            "supports_playlist", "supports_segments", "supports_resume"
        )):
            raise DownloadCapabilityError("download capability flags invalid")
        if not isinstance(raw["max_batch_size"], int) or not 1 <= raw["max_batch_size"] <= 500:
            raise DownloadCapabilityError("download batch capability invalid")
        return cls(
            raw["provider_id"],
            tuple(raw["sites"]),
            tuple(raw["format_presets"]),
            tuple(raw["subtitle_modes"]),
            tuple(raw["timed_comments"]),
            raw["supports_playlist"],
            raw["supports_segments"],
            raw["supports_resume"],
            raw["max_batch_size"],
        )
