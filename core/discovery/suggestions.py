"""Local-only, bounded search suggestions derived from explicit history."""

from __future__ import annotations

from collections.abc import Iterable

from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1


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
        return max(values.items(), key=lambda item: (item[1], item[0]))[0]

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
    candidates.extend(event.query for event in events)

    result: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        value = " ".join(raw.split())[:200]
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= bounded:
            break
    return tuple(result)
