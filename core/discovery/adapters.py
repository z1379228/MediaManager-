"""Bounded federated search routing for independently maintained MODs."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.search_v2 import SearchCapabilityV2, SearchPageV2, SearchQueryV2
from core.logging.redaction import bounded_redacted_text

SearchCallable = Callable[[SearchQueryV2], SearchPageV2]
_MAX_SEARCH_SOURCES = 16
_MAX_RESULTS_PER_SOURCE = 20


@dataclass(frozen=True, slots=True)
class SearchAdapterFailure:
    provider_id: str
    message: str
    category: str = "error"


@dataclass(frozen=True, slots=True)
class FederatedSearchResult:
    items: tuple[DiscoveryItemV1, ...]
    failures: tuple[SearchAdapterFailure, ...]
    sources: tuple[str, ...]
    next_cursors: tuple[tuple[str, str], ...] = ()


def canonical_result_key(item: DiscoveryItemV1) -> str:
    """Remove common tracking parameters while preserving media identity."""

    parts = urlsplit(item.url)
    host = (parts.hostname or parts.netloc).casefold()
    if item.video_id:
        return f"{host}|id:{item.video_id.casefold()}"
    tracking_keys = {"fbclid", "si"}
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in tracking_keys
        )
    )
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path, query, "")
    )


class SearchAdapterRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[SearchCapabilityV2, SearchCallable]] = {}

    def register(self, capability: SearchCapabilityV2, search: SearchCallable) -> None:
        if capability.provider_id in self._entries:
            raise ValueError("search adapter is already registered")
        self._entries[capability.provider_id] = (capability, search)

    def capabilities(self) -> tuple[SearchCapabilityV2, ...]:
        return tuple(value[0] for value in self._entries.values())

    def search(
        self,
        query: SearchQueryV2,
        *,
        provider_ids: Iterable[str] | None = None,
        limit: int = 50,
    ) -> FederatedSearchResult:
        selected = tuple(provider_ids) if provider_ids is not None else tuple(self._entries)
        bounded_limit = max(1, min(int(limit), 50))
        if len(selected) > _MAX_SEARCH_SOURCES:
            raise ValueError("too many search MODs selected")
        collected: list[tuple[str, tuple[DiscoveryItemV1, ...]]] = []
        next_cursors: list[tuple[str, str]] = []
        failures: list[SearchAdapterFailure] = []
        for provider_id in selected:
            entry = self._entries.get(provider_id)
            if entry is None:
                failures.append(
                    SearchAdapterFailure(provider_id, "search MOD is unavailable")
                )
                continue
            capability, adapter = entry
            try:
                normalized = SearchQueryV2(
                    query.query,
                    query.content_type,
                    min(query.page_size, bounded_limit, _MAX_RESULTS_PER_SOURCE),
                    query.cursor,
                ).normalized(capability)
                page = adapter(normalized)
                if page.provider_id != provider_id:
                    raise ValueError("search page provider mismatch")
                if page.next_cursor:
                    next_cursors.append((provider_id, page.next_cursor))
                collected.append(
                    (provider_id, tuple(page.items[:_MAX_RESULTS_PER_SOURCE]))
                )
            except Exception as error:
                category = (
                    "timeout"
                    if isinstance(error, TimeoutError)
                    else "invalid-response"
                    if isinstance(error, (TypeError, ValueError))
                    else "unavailable"
                    if isinstance(error, (ConnectionError, OSError))
                    else "error"
                )
                failures.append(
                    SearchAdapterFailure(
                        provider_id,
                        bounded_redacted_text(
                            str(error),
                            max_utf8_bytes=300,
                        )
                        or type(error).__name__,
                        category,
                    )
                )
        unique: dict[str, DiscoveryItemV1] = {}
        sources: dict[str, str] = {}
        largest_page = max((len(items) for _, items in collected), default=0)
        for position in range(largest_page):
            for provider_id, items in collected:
                if position >= len(items):
                    continue
                item = items[position]
                key = canonical_result_key(item)
                if key not in unique:
                    unique[key] = item
                    sources[key] = provider_id
                if len(unique) >= bounded_limit:
                    break
            if len(unique) >= bounded_limit:
                break
        return FederatedSearchResult(
            tuple(unique.values()),
            tuple(failures),
            tuple(sources[key] for key in unique),
            tuple(next_cursors),
        )
