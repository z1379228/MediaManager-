"""Bounded federated search routing for independently maintained MODs."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.search_v2 import SearchCapabilityV2, SearchPageV2, SearchQueryV2

SearchCallable = Callable[[SearchQueryV2], SearchPageV2]


@dataclass(frozen=True, slots=True)
class SearchAdapterFailure:
    provider_id: str
    message: str


@dataclass(frozen=True, slots=True)
class FederatedSearchResult:
    items: tuple[DiscoveryItemV1, ...]
    failures: tuple[SearchAdapterFailure, ...]


def canonical_result_key(item: DiscoveryItemV1) -> str:
    """Remove common tracking parameters while preserving media identity."""

    if item.video_id:
        return f"id:{item.video_id.casefold()}"
    parts = urlsplit(item.url)
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
        unique: dict[str, DiscoveryItemV1] = {}
        failures: list[SearchAdapterFailure] = []
        for provider_id in selected[:16]:
            entry = self._entries.get(provider_id)
            if entry is None:
                failures.append(
                    SearchAdapterFailure(provider_id, "search MOD is unavailable")
                )
                continue
            capability, adapter = entry
            try:
                normalized = query.normalized(capability)
                page = adapter(normalized)
                if page.provider_id != provider_id:
                    raise ValueError("search page provider mismatch")
                for item in page.items:
                    unique.setdefault(canonical_result_key(item), item)
                    if len(unique) >= bounded_limit:
                        break
            except Exception as error:
                failures.append(
                    SearchAdapterFailure(
                        provider_id, str(error)[:300] or type(error).__name__
                    )
                )
            if len(unique) >= bounded_limit:
                break
        return FederatedSearchResult(tuple(unique.values()), tuple(failures))
