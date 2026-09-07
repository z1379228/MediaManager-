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


def merge_federated_search_pages(
    existing: FederatedSearchResult,
    incoming: FederatedSearchResult,
    *,
    limit: int = MAX_WORKSPACE_SEARCH_RESULTS,
) -> FederatedSearchResult:
    """Append one federated page while retaining source identity and retry state."""

    bounded_limit = max(1, min(int(limit), MAX_WORKSPACE_SEARCH_RESULTS))
    merged_items: list[DiscoveryItemV1] = []
    merged_sources: list[str] = []
    seen: set[str] = set()
    for response in (existing, incoming):
        for index, item in enumerate(response.items):
            key = canonical_result_key(item)
            if key in seen:
                continue
            seen.add(key)
            merged_items.append(item)
            merged_sources.append(
                response.sources[index] if index < len(response.sources) else ""
            )
            if len(merged_items) >= bounded_limit:
                break
        if len(merged_items) >= bounded_limit:
            break
    if len(merged_items) >= bounded_limit:
        next_cursors = ()
    else:
        next_cursors = incoming.next_cursors
        if not incoming.items and incoming.failures and not next_cursors:
            next_cursors = existing.next_cursors
    return FederatedSearchResult(
        tuple(merged_items),
        incoming.failures,
        tuple(merged_sources),
        next_cursors,
    )
