"""Search MOD capability and paged-result contracts for MediaManager 4.x."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.discovery_v1 import DiscoveryItemV1


class SearchContractV2Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SearchCapabilityV2:
    provider_id: str
    sites: tuple[str, ...]
    content_types: tuple[str, ...]
    max_page_size: int
    pagination: str
    audio_preview: bool
    video_preview: bool

    def __post_init__(self) -> None:
        allowed_types = {"all", "music", "video", "playlist", "live"}
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise SearchContractV2Error("search provider id invalid")
        if (
            not isinstance(self.sites, tuple)
            or not 1 <= len(self.sites) <= 32
            or len(self.sites) != len(set(self.sites))
            or not all(isinstance(item, str) and item for item in self.sites)
        ):
            raise SearchContractV2Error("search sites invalid")
        if (
            not isinstance(self.content_types, tuple)
            or not self.content_types
            or len(self.content_types) != len(set(self.content_types))
            or not set(self.content_types) <= allowed_types
        ):
            raise SearchContractV2Error("search content types invalid")
        if (
            not isinstance(self.max_page_size, int)
            or isinstance(self.max_page_size, bool)
            or not 1 <= self.max_page_size <= 50
            or self.pagination not in {"none", "offset", "cursor"}
            or not isinstance(self.audio_preview, bool)
            or not isinstance(self.video_preview, bool)
        ):
            raise SearchContractV2Error("search capability values invalid")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SearchCapabilityV2":
        required = {
            "provider_id",
            "sites",
            "content_types",
            "max_page_size",
            "pagination",
            "audio_preview",
            "video_preview",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise SearchContractV2Error("search capability fields invalid")
        provider_id = raw["provider_id"]
        sites = raw["sites"]
        content_types = raw["content_types"]
        if not isinstance(provider_id, str) or not provider_id:
            raise SearchContractV2Error("search provider id invalid")
        if (
            not isinstance(sites, list)
            or not 1 <= len(sites) <= 32
            or len(sites) != len(set(sites))
            or not all(isinstance(item, str) and item for item in sites)
        ):
            raise SearchContractV2Error("search sites invalid")
        allowed_types = {"all", "music", "video", "playlist", "live"}
        if (
            not isinstance(content_types, list)
            or not content_types
            or len(content_types) != len(set(content_types))
            or not set(content_types) <= allowed_types
        ):
            raise SearchContractV2Error("search content types invalid")
        if (
            not isinstance(raw["max_page_size"], int)
            or isinstance(raw["max_page_size"], bool)
            or not 1 <= raw["max_page_size"] <= 50
            or raw["pagination"] not in {"none", "offset", "cursor"}
            or not isinstance(raw["audio_preview"], bool)
            or not isinstance(raw["video_preview"], bool)
        ):
            raise SearchContractV2Error("search capability values invalid")
        return cls(
            provider_id,
            tuple(sites),
            tuple(content_types),
            raw["max_page_size"],
            raw["pagination"],
            raw["audio_preview"],
            raw["video_preview"],
        )


@dataclass(frozen=True, slots=True)
class SearchQueryV2:
    query: str
    content_type: str = "all"
    page_size: int = 12
    cursor: str = ""

    def normalized(self, capability: SearchCapabilityV2) -> "SearchQueryV2":
        if not isinstance(self.query, str):
            raise SearchContractV2Error("search query invalid")
        query = " ".join(self.query.split())[:200]
        if not query:
            raise SearchContractV2Error("search query is empty")
        if self.content_type not in capability.content_types:
            raise SearchContractV2Error("content type is unsupported by this MOD")
        if not isinstance(self.cursor, str) or len(self.cursor) > 500:
            raise SearchContractV2Error("search cursor invalid")
        if self.cursor and capability.pagination == "none":
            raise SearchContractV2Error("search MOD does not support pagination")
        if not isinstance(self.page_size, int) or isinstance(self.page_size, bool):
            raise SearchContractV2Error("search page size invalid")
        return SearchQueryV2(
            query,
            self.content_type,
            max(1, min(self.page_size, capability.max_page_size)),
            self.cursor,
        )


@dataclass(frozen=True, slots=True)
class SearchPageV2:
    provider_id: str
    items: tuple[DiscoveryItemV1, ...]
    next_cursor: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider_id, str)
            or not self.provider_id
            or not isinstance(self.items, tuple)
            or any(not isinstance(item, DiscoveryItemV1) for item in self.items)
            or len(self.items) > 50
            or not isinstance(self.next_cursor, str)
            or len(self.next_cursor) > 500
        ):
            raise SearchContractV2Error("search page invalid")
