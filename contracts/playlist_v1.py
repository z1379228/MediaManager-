"""Versioned, transport-neutral playlist entry contract."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any
from urllib.parse import urlparse


MAX_PLAYLIST_ENTRIES_V1 = 500


class PlaylistContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlaylistEntryV1:
    entry_id: str
    url: str
    title: str
    artist: str
    duration: float | None
    position: int
    available: bool
    unavailable_reason: str = ""
    thumbnail_url: str = ""

    def __post_init__(self) -> None:
        if not 1 <= len(self.entry_id) <= 100:
            raise ValueError("playlist entry id is invalid")
        if not 1 <= len(self.title) <= 300 or len(self.artist) > 200:
            raise ValueError("playlist entry metadata is invalid")
        if (
            not isinstance(self.position, int)
            or isinstance(self.position, bool)
            or not 1 <= self.position <= MAX_PLAYLIST_ENTRIES_V1
        ):
            raise ValueError("playlist entry position is invalid")
        if self.duration is not None and (
            not isinstance(self.duration, (int, float))
            or isinstance(self.duration, bool)
            or not math.isfinite(self.duration)
            or not 0 < self.duration <= 604_800
        ):
            raise ValueError("playlist entry duration is invalid")
        if not isinstance(self.available, bool):
            raise ValueError("playlist entry availability is invalid")
        if len(self.unavailable_reason) > 200:
            raise ValueError("playlist unavailable reason is invalid")
        if len(self.thumbnail_url) > 1000:
            raise ValueError("playlist thumbnail URL is invalid")
        parsed = urlparse(self.url)
        valid_url = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        if self.available and not valid_url:
            raise ValueError("available playlist entry URL is invalid")
        if not self.available and self.url and not valid_url:
            raise ValueError("playlist entry URL is invalid")
        if self.thumbnail_url:
            thumbnail = urlparse(self.thumbnail_url)
            if thumbnail.scheme != "https" or not thumbnail.hostname:
                raise ValueError("playlist thumbnail URL is invalid")

    @classmethod
    def from_dict(cls, raw: Any) -> PlaylistEntryV1:
        required_fields = {
            "entry_id",
            "url",
            "title",
            "artist",
            "duration",
            "position",
            "available",
            "unavailable_reason",
        }
        if not isinstance(raw, dict) or not (
            set(raw) == required_fields
            or set(raw) == required_fields | {"thumbnail_url"}
        ):
            raise PlaylistContractError("playlist entry fields are invalid")
        text_fields = {
            "entry_id",
            "url",
            "title",
            "artist",
            "unavailable_reason",
        }
        if not all(isinstance(raw[key], str) for key in text_fields):
            raise PlaylistContractError("playlist entry text fields are invalid")
        if not isinstance(raw.get("thumbnail_url", ""), str):
            raise PlaylistContractError("playlist thumbnail URL is invalid")
        if (
            not isinstance(raw["position"], int)
            or isinstance(raw["position"], bool)
            or not isinstance(raw["available"], bool)
        ):
            raise PlaylistContractError("playlist entry state fields are invalid")
        duration = raw["duration"]
        if duration is not None and (
            not isinstance(duration, (int, float)) or isinstance(duration, bool)
        ):
            raise PlaylistContractError("playlist entry duration is invalid")
        return cls(
            entry_id=raw["entry_id"],
            url=raw["url"],
            title=raw["title"],
            artist=raw["artist"],
            duration=float(duration) if duration is not None else None,
            position=raw["position"],
            available=raw["available"],
            unavailable_reason=raw["unavailable_reason"],
            thumbnail_url=raw.get("thumbnail_url", ""),
        )
