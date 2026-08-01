"""Bounded federated search routing for independently maintained MODs."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from itertools import islice
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.search_v2 import (
    SearchCapabilityV2,
    SearchContractV2Error,
    SearchPageV2,
    SearchQueryV2,
)
from core.logging.redaction import bounded_redacted_text
from core.site_routing import classify_site_url

SearchCallable = Callable[[SearchQueryV2], SearchPageV2]
_MAX_SEARCH_SOURCES = 16
_MAX_RESULTS_PER_SOURCE = 20
_MAX_SINGLE_SOURCE_RESULTS = 50
FEDERATED_CURSOR_PROVIDER_ID = "__federated__"


def _bounded_provider_selection(
    provider_ids: Iterable[str] | None,
    *,
    defaults: Iterable[str],
) -> tuple[str, ...]:
    """Normalize provider selection without consuming an unbounded iterable."""

    if provider_ids is None:
        iterator = iter(defaults)
    else:
        if isinstance(provider_ids, (str, bytes)):
            raise ValueError("search MOD selection is invalid")
        try:
            iterator = iter(provider_ids)
        except TypeError:
            raise ValueError("search MOD selection is invalid") from None
    return tuple(islice(iterator, _MAX_SEARCH_SOURCES + 1))


def _bounded_search_limit(limit: int) -> int:
    """Clamp an actual integer limit without silently coercing other types."""

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("search result limit is invalid")
    return max(1, min(limit, _MAX_SINGLE_SOURCE_RESULTS))


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
    """Canonicalize media identity without weakening exact-host access policy."""

    parts = urlsplit(item.url)
    if item.video_id:
        route = classify_site_url(item.url)
        identity_host = (
            "site:youtube"
            if route is not None and route.site_family == "youtube"
            else parts.netloc.casefold()
        )
        return f"{identity_host}|id:{item.video_id}"
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

    def normalize_provider_selection(
        self,
        provider_ids: Iterable[str] | None = None,
    ) -> tuple[str, ...]:
        """Return one bounded, validated provider selection for every caller."""

        selected = _bounded_provider_selection(
            provider_ids,
            defaults=self._entries,
        )
        if any(
            not isinstance(provider_id, str) or not provider_id
            for provider_id in selected
        ):
            raise ValueError("search MOD selection is invalid")
        if len(set(selected)) != len(selected):
            raise ValueError("duplicate search MOD selection")
        if len(selected) > _MAX_SEARCH_SOURCES:
            raise ValueError("too many search MODs selected")
        return selected

    def normalize_result_limit(self, limit: int) -> int:
        """Return the shared bounded result limit used by service and registry."""

        return _bounded_search_limit(limit)

    def normalize_provider_cursors(
        self,
        provider_cursors: Mapping[str, str] | None,
    ) -> dict[str, str] | None:
        """Validate cursor routing without materializing an unbounded mapping."""

        if provider_cursors is None:
            return None
        if not isinstance(provider_cursors, Mapping):
            raise ValueError("federated search cursor mapping is invalid")
        try:
            cursor_items = tuple(
                islice(provider_cursors.items(), _MAX_SEARCH_SOURCES + 1)
            )
        except (KeyError, TypeError):
            raise ValueError("federated search cursor mapping is invalid") from None
        if len(cursor_items) > _MAX_SEARCH_SOURCES:
            raise ValueError("too many federated search cursors")
        if not cursor_items:
            raise ValueError("federated search cursor is empty")
        cursor_map: dict[str, str] = {}
        for item in cursor_items:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("federated search cursor mapping is invalid")
            provider_id, cursor = item
            if (
                not isinstance(provider_id, str)
                or not provider_id
                or provider_id in cursor_map
                or not isinstance(cursor, str)
                or not 1 <= len(cursor) <= 500
            ):
                raise ValueError("federated search cursor is invalid")
            cursor_map[provider_id] = cursor
        return cursor_map

    def search(
        self,
        query: SearchQueryV2,
        *,
        provider_ids: Iterable[str] | None = None,
        limit: int = 50,
        provider_cursors: Mapping[str, str] | None = None,
    ) -> FederatedSearchResult:
        if not isinstance(query, SearchQueryV2):
            raise SearchContractV2Error("search query invalid")
        validated_query = query.validated()
        selected = self.normalize_provider_selection(provider_ids)
        bounded_limit = self.normalize_result_limit(limit)
        if validated_query.cursor and provider_cursors is not None:
            raise ValueError("search cursor routing is ambiguous")
        cursor_map = self.normalize_provider_cursors(provider_cursors)
        if cursor_map is not None:
            unknown_cursor_sources = set(cursor_map) - set(selected)
            if unknown_cursor_sources:
                raise ValueError("federated search cursor source is invalid")
        attempted = tuple(
            provider_id
            for provider_id in selected
            if cursor_map is None or provider_id in cursor_map
        )
        if len(attempted) > bounded_limit:
            raise ValueError("search result limit must cover every selected MOD")
        per_source_limit = (
            _MAX_SINGLE_SOURCE_RESULTS
            if len(selected) == 1
            else _MAX_RESULTS_PER_SOURCE
        )
        source_limits: dict[str, int] = {}
        if attempted:
            base_limit, remainder = divmod(bounded_limit, len(attempted))
            source_limits = {
                provider_id: min(
                    per_source_limit,
                    base_limit + (1 if index < remainder else 0),
                )
                for index, provider_id in enumerate(attempted)
            }
        collected: list[tuple[str, tuple[DiscoveryItemV1, ...]]] = []
        next_cursors: list[tuple[str, str]] = []
        failures: list[SearchAdapterFailure] = []
        for provider_id in selected:
            if cursor_map is not None and provider_id not in cursor_map:
                continue
            entry = self._entries.get(provider_id)
            if entry is None:
                failures.append(
                    SearchAdapterFailure(provider_id, "search MOD is unavailable")
                )
                continue
            capability, adapter = entry
            try:
                normalized = SearchQueryV2(
                    validated_query.query,
                    validated_query.content_type,
                    min(validated_query.page_size, source_limits[provider_id]),
                    (
                        cursor_map[provider_id]
                        if cursor_map is not None
                        else validated_query.cursor
                    ),
                ).normalized(capability)
                page = adapter(normalized)
                if page.provider_id != provider_id:
                    raise ValueError("search page provider mismatch")
                if len(page.items) > normalized.page_size:
                    raise ValueError("search page exceeded requested page size")
                if page.next_cursor:
                    next_cursors.append((provider_id, page.next_cursor))
                collected.append((provider_id, page.items))
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
