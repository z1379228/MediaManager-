"""Bounded paging helpers shared by website-specific trusted workspaces."""

from __future__ import annotations

from collections.abc import Iterable

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult, canonical_result_key


MAX_WORKSPACE_SEARCH_RESULTS = 200


def provider_next_cursor(
    response: FederatedSearchResult,
    provider_id: str,
) -> str:
    """Return one bounded cursor without accepting another provider's token."""

    for candidate_provider, cursor in response.next_cursors:
        if candidate_provider == provider_id and 1 <= len(cursor) <= 2048:
            return cursor
    return ""


def merge_search_results(
    existing: Iterable[DiscoveryItemV1],
    incoming: Iterable[DiscoveryItemV1],
    *,
    limit: int = MAX_WORKSPACE_SEARCH_RESULTS,
) -> tuple[DiscoveryItemV1, ...]:
    """Merge pages by canonical media identity while preserving result order."""

    bounded_limit = max(1, min(int(limit), MAX_WORKSPACE_SEARCH_RESULTS))
    merged: list[DiscoveryItemV1] = []
    seen: set[str] = set()
    for item in (*tuple(existing), *tuple(incoming)):
        key = canonical_result_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= bounded_limit:
            break
    return tuple(merged)
