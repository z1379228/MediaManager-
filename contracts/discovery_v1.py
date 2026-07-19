"""Versioned discovery result contract shared by search-oriented MODs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts._additive_result import (
    AdditiveResultError,
    validate_additive_result,
)


class DiscoveryContractError(ValueError):
    pass


_DISCOVERY_FIELDS = frozenset(
    {
        "video_id",
        "url",
        "title",
        "artist",
        "duration",
        "language",
        "category",
        "thumbnail_url",
    }
)


@dataclass(frozen=True, slots=True)
class DiscoveryItemV1:
    video_id: str
    url: str
    title: str
    artist: str
    duration: int | None
    language: str
    category: str
    thumbnail_url: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DiscoveryItemV1":
        try:
            validate_additive_result(raw, required_fields=_DISCOVERY_FIELDS)
        except AdditiveResultError as exc:
            raise DiscoveryContractError(
                "discovery result fields invalid"
            ) from exc
        text_fields = _DISCOVERY_FIELDS - {"duration"}
        if not all(isinstance(raw[key], str) for key in text_fields):
            raise DiscoveryContractError("discovery result text fields invalid")
        if not raw["video_id"] or not raw["url"].startswith("https://"):
            raise DiscoveryContractError("discovery result identity invalid")
        if not 1 <= len(raw["title"]) <= 300 or len(raw["artist"]) > 200:
            raise DiscoveryContractError("discovery result title is invalid")
        thumbnail_url = raw["thumbnail_url"]
        if thumbnail_url and (
            len(thumbnail_url) > 1000 or not thumbnail_url.startswith("https://")
        ):
            raise DiscoveryContractError("discovery result thumbnail is invalid")
        duration = raw["duration"]
        if duration is not None and (
            not isinstance(duration, int) or duration < 0 or duration > 86400
        ):
            raise DiscoveryContractError("discovery result duration invalid")
        return cls(
            video_id=raw["video_id"],
            url=raw["url"],
            title=raw["title"],
            artist=raw["artist"],
            duration=raw["duration"],
            language=raw["language"],
            category=raw["category"],
            thumbnail_url=raw["thumbnail_url"],
        )
