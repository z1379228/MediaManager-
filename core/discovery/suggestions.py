"""Local-only, bounded search suggestions derived from explicit history."""

from __future__ import annotations

from collections.abc import Iterable

from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1
from core.discovery.text_normalization import normalized_search_text


def _normalized_query_key(value: str) -> str:
    return normalized_search_text(value)


def recent_history_queries(
    events: object,
    *,
    limit: int = 8,
) -> tuple[str, ...]:
    """Return bounded, newest-first unique queries for compact history UIs."""

    if not isinstance(events, (list, tuple)):
        return ()
    bounded_limit = max(1, min(int(limit), 20))
    queries: list[str] = []
    seen: set[str] = set()
    for event in events:
        if getattr(event, "event_type", "") != "search":
            continue
        value = getattr(event, "query", "")
        query = " ".join(value.split()) if isinstance(value, str) else ""
        key = _normalized_query_key(query)
        if not query or key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= bounded_limit:
            break
    return tuple(queries)


def preference_search_queries(
    preferences: HistoryPreferencesV1,
    events: Iterable[HistoryEventV1] = (),
    *,
    limit: int = 6,
) -> tuple[str, ...]:
    """Return explainable suggestions without searching or connecting."""

    bounded = max(1, min(int(limit), 12))
    candidates: list[str] = []

    def top(values: dict[str, int]) -> str:
        if not values:
            return ""
        aggregated: dict[str, tuple[str, int]] = {}
        for value, count in values.items():
            key = _normalized_query_key(value)
            if not key:
                continue
            representative, total = aggregated.get(key, (value, 0))
            aggregated[key] = (representative, total + count)
        if not aggregated:
            return ""
        return max(aggregated.values(), key=lambda item: (item[1], item[0]))[0]

    artist = top(preferences.artists)
    language = top(preferences.languages)
    category = top(preferences.categories)
    content_type = top(preferences.content_types)
    if artist:
        candidates.append(artist)
    if category and language:
        candidates.append(f"{language} {category}")
    elif category or language:
        candidates.append(category or language)
    if content_type:
        candidates.append({"music": "音樂", "video": "影片"}.get(content_type, content_type))

    result: list[str] = []
    seen: set[str] = set()

    def add(raw: object) -> bool:
        if not isinstance(raw, str):
            return False
        value = " ".join(raw.split())[:200]
        key = _normalized_query_key(value)
        if not value or key in seen:
            return False
        seen.add(key)
        result.append(value)
        return len(result) >= bounded

    for raw in candidates:
        if add(raw):
            return tuple(result)
    for event in events:
        if getattr(event, "event_type", "") != "search":
            continue
        if add(getattr(event, "query", "")):
            break
    return tuple(result)
