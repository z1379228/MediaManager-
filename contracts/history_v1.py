"""Versioned bounded history contract for discovery MODs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts._additive_result import (
    AdditiveResultError,
    validate_additive_result,
)
from contracts.discovery_v1 import DiscoveryItemV1


class HistoryContractError(ValueError):
    pass


_HISTORY_EVENT_FIELDS = frozenset(
    {"event_type", "query", "timestamp", "item"}
)
_HISTORY_PREFERENCE_FIELDS = frozenset(
    {
        "total_searches",
        "total_selections",
        "content_types",
        "languages",
        "artists",
        "categories",
    }
)


@dataclass(frozen=True, slots=True)
class HistoryEventV1:
    event_type: str
    query: str
    timestamp: str
    item: DiscoveryItemV1 | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HistoryEventV1":
        try:
            validate_additive_result(
                raw,
                required_fields=_HISTORY_EVENT_FIELDS,
            )
        except AdditiveResultError as exc:
            raise HistoryContractError("history event fields invalid") from exc
        if raw["event_type"] not in {"search", "selection"}:
            raise HistoryContractError("history event type invalid")
        query, timestamp = raw["query"], raw["timestamp"]
        if not isinstance(query, str) or not 1 <= len(query) <= 200:
            raise HistoryContractError("history query invalid")
        if not isinstance(timestamp, str) or not 20 <= len(timestamp) <= 40:
            raise HistoryContractError("history timestamp invalid")
        item_raw = raw["item"]
        if raw["event_type"] == "search" and item_raw is not None:
            raise HistoryContractError("search history item must be empty")
        if raw["event_type"] == "selection" and not isinstance(item_raw, dict):
            raise HistoryContractError("selection history item missing")
        item = DiscoveryItemV1.from_dict(item_raw) if item_raw is not None else None
        return cls(raw["event_type"], query, timestamp, item)


@dataclass(frozen=True, slots=True)
class HistoryPreferencesV1:
    total_searches: int
    total_selections: int
    content_types: dict[str, int]
    languages: dict[str, int]
    artists: dict[str, int]
    categories: dict[str, int]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HistoryPreferencesV1":
        try:
            validate_additive_result(
                raw,
                required_fields=_HISTORY_PREFERENCE_FIELDS,
            )
        except AdditiveResultError as exc:
            raise HistoryContractError(
                "history preferences fields invalid"
            ) from exc
        if not all(
            isinstance(raw[key], int) and 0 <= raw[key] <= 100000
            for key in ("total_searches", "total_selections")
        ):
            raise HistoryContractError("history preference totals invalid")
        for field in ("content_types", "languages", "artists", "categories"):
            values = raw[field]
            if not isinstance(values, dict) or len(values) > 100:
                raise HistoryContractError("history preference counters invalid")
            if not all(
                isinstance(key, str) and 1 <= len(key) <= 200
                and isinstance(value, int) and 0 < value <= 100000
                for key, value in values.items()
            ):
                raise HistoryContractError("history preference counters invalid")
        return cls(
            total_searches=raw["total_searches"],
            total_selections=raw["total_selections"],
            content_types=raw["content_types"],
            languages=raw["languages"],
            artists=raw["artists"],
            categories=raw["categories"],
        )
