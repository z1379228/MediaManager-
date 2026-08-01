"""Versioned discovery result contract shared by search-oriented MODs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

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
_MAX_DISCOVERY_URL_LENGTH = 4096
_MAX_THUMBNAIL_URL_LENGTH = 1000


def _is_plain_https_url(value: str, *, maximum: int) -> bool:
    if (
        not 1 <= len(value) <= maximum
        or any(character.isspace() for character in value)
        or any(character in value for character in ('"', "'", "\\"))
    ):
        return False
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme == "https"
        and hostname
        and parsed.username is None
        and parsed.password is None
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

    def __post_init__(self) -> None:
        text_values = (
            self.video_id,
            self.url,
            self.title,
            self.artist,
            self.language,
            self.category,
            self.thumbnail_url,
        )
        if not all(isinstance(value, str) for value in text_values):
            raise DiscoveryContractError("discovery result text fields invalid")
        if not self.video_id or not _is_plain_https_url(
            self.url,
            maximum=_MAX_DISCOVERY_URL_LENGTH,
        ):
            raise DiscoveryContractError("discovery result identity invalid")
        if not 1 <= len(self.title) <= 300 or len(self.artist) > 200:
            raise DiscoveryContractError("discovery result title is invalid")
        if self.thumbnail_url and not _is_plain_https_url(
            self.thumbnail_url,
            maximum=_MAX_THUMBNAIL_URL_LENGTH,
        ):
            raise DiscoveryContractError("discovery result thumbnail is invalid")
        if self.duration is not None and (
            not isinstance(self.duration, int)
            or self.duration < 0
            or self.duration > 86400
        ):
            raise DiscoveryContractError("discovery result duration invalid")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DiscoveryItemV1":
        try:
            validate_additive_result(raw, required_fields=_DISCOVERY_FIELDS)
        except AdditiveResultError as exc:
            raise DiscoveryContractError(
                "discovery result fields invalid"
            ) from exc
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
