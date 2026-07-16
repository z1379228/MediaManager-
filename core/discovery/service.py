"""Registry and routing boundary for lightweight discovery MODs."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from typing import Protocol
from urllib.parse import urlsplit

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1
from contracts.recovery_v1 import RecoveryCandidateV1, RecoveryPlanV1
from contracts.similar_v1 import SimilarPlanV1, SimilarSelectionV1
from contracts.split_plan_v1 import SplitPlanV1
from contracts.search_v2 import SearchCapabilityV2, SearchPageV2, SearchQueryV2
from core.discovery.adapters import FederatedSearchResult, SearchAdapterRegistry
from core.downloads.provider_registry import (
    DownloadProviderRegistry,
    ProviderStatus,
)
from core.site_routing import YOUTUBE_HOSTS


_SIMILAR_SEARCH_BINDINGS = {"youtube-similar": "youtube-search"}
_RECOVERY_SEARCH_BINDINGS = {"youtube-recovery": "youtube-search"}
_YOUTUBE_RESULT_HOSTS = YOUTUBE_HOSTS


def _require_bound_original_source(
    original: DiscoveryItemV1,
    search_provider_id: str,
) -> None:
    if search_provider_id != "youtube-search":
        raise RuntimeError("bound search source has no result-host policy")
    try:
        parsed = urlsplit(original.url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("original result source is invalid") from error
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold() not in _YOUTUBE_RESULT_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise ValueError("original result does not match the bound search source")


class SearchProvider(Protocol):
    provider_id: str
    display_name: str

    def search(
        self,
        query: str,
        *,
        limit: int = 12,
        content_type: str = "all",
    ) -> tuple[DiscoveryItemV1, ...]: ...

    def search_page(self, query: SearchQueryV2) -> SearchPageV2: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SearchSourceStatus:
    provider_id: str
    display_name: str
    enabled: bool
    health: str
    message: str = ""
    consecutive_failures: int = 0
    successful_searches: int = 0


@dataclass(slots=True)
class _SearchHealth:
    consecutive_failures: int = 0
    successful_searches: int = 0
    message: str = ""


class SimilarProvider(Protocol):
    provider_id: str
    display_name: str

    def similar_plan(
        self,
        item: DiscoveryItemV1,
        preferences: HistoryPreferencesV1,
    ) -> SimilarPlanV1: ...

    def select_similar(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
        preferences: HistoryPreferencesV1,
    ) -> SimilarSelectionV1 | None: ...

    def rank_similar(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
        preferences: HistoryPreferencesV1,
        *,
        limit: int = 12,
    ) -> tuple[SimilarSelectionV1, ...]: ...

    def close(self) -> None: ...


class RecoveryProvider(Protocol):
    provider_id: str
    display_name: str

    def recovery_plan(self, item: DiscoveryItemV1) -> RecoveryPlanV1: ...

    def rank_recovery(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
    ) -> tuple[RecoveryCandidateV1, ...]: ...

    def close(self) -> None: ...


class HistoryProvider(Protocol):
    provider_id: str
    display_name: str

    def record_history(
        self, event_type: str, query: str, item: DiscoveryItemV1 | None = None
    ) -> None: ...

    def recent_history(self, *, limit: int = 20) -> tuple[HistoryEventV1, ...]: ...

    def history_preferences(self) -> HistoryPreferencesV1: ...

    def close(self) -> None: ...


class SplitProvider(Protocol):
    provider_id: str
    display_name: str

    def split_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        chapters: list[dict[str, object]],
        description: str,
    ) -> SplitPlanV1: ...

    def split_audio_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        input_path: Path,
        threshold_db: float = -35.0,
        min_silence: float = 1.2,
    ) -> SplitPlanV1: ...

    def split_filename(
        self,
        *,
        source_title: str,
        index: int,
        track_title: str,
        start: float,
        duration: float,
        extension: str,
    ) -> str: ...

    def close(self) -> None: ...


class VideoPreviewProvider(Protocol):
    provider_id: str
    display_name: str

    def prepare_video_preview(
        self, url: str, *, duration: float, preview_length: float = 60
    ) -> Path: ...

    def cleanup_video_preview(self, preview_path: Path) -> bool: ...

    def close(self) -> None: ...


class DiscoveryService:
    def __init__(self, state_path: Path) -> None:
        self._registry = DownloadProviderRegistry(state_path)
        self._providers: dict[str, SearchProvider] = {}
        self._search_adapters = SearchAdapterRegistry()
        self._search_health: dict[str, _SearchHealth] = {}
        self._search_cursor_key = secrets.token_bytes(32)
        self._history_providers: dict[str, HistoryProvider] = {}
        self._recovery_providers: dict[str, RecoveryProvider] = {}
        self._similar_providers: dict[str, SimilarProvider] = {}
        self._split_providers: dict[str, SplitProvider] = {}
        self._video_preview_providers: dict[str, VideoPreviewProvider] = {}

    def register(self, provider: SearchProvider, *, enabled: bool = False) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._providers[provider.provider_id] = provider
        declared = getattr(provider, "search_capability", None)
        capability = (
            declared
            if isinstance(declared, SearchCapabilityV2)
            else SearchCapabilityV2(
                provider.provider_id,
                (provider.provider_id,),
                ("all", "music", "video"),
                50,
                "none",
                True,
                True,
            )
        )
        if capability.provider_id != provider.provider_id:
            raise ValueError("search capability provider mismatch")

        def adapter(query: SearchQueryV2) -> SearchPageV2:
            search_page = (
                getattr(provider, "search_page", None)
                if callable(getattr(type(provider), "search_page", None))
                else None
            )
            if callable(search_page):
                page = search_page(query)
                if not isinstance(page, SearchPageV2):
                    raise ValueError("search MOD returned an invalid page")
                return page
            if query.cursor:
                raise ValueError("search MOD does not implement pagination")
            items = provider.search(
                query.query,
                limit=query.page_size,
                content_type=query.content_type,
            )
            return SearchPageV2(provider.provider_id, items)

        self._search_adapters.register(capability, adapter)

    def search_capabilities(self) -> tuple[SearchCapabilityV2, ...]:
        return self._search_adapters.capabilities()

    def search_source_statuses(self) -> tuple[SearchSourceStatus, ...]:
        search_ids = {
            capability.provider_id for capability in self.search_capabilities()
        }
        return tuple(
            SearchSourceStatus(
                status.provider_id,
                status.display_name,
                status.enabled,
                (
                    "disabled"
                    if not status.enabled
                    else "error"
                    if self._search_health.get(
                        status.provider_id, _SearchHealth()
                    ).consecutive_failures
                    else "ready"
                ),
                self._search_health.get(
                    status.provider_id, _SearchHealth()
                ).message,
                self._search_health.get(
                    status.provider_id, _SearchHealth()
                ).consecutive_failures,
                self._search_health.get(
                    status.provider_id, _SearchHealth()
                ).successful_searches,
            )
            for status in self._registry.statuses()
            if status.provider_id in search_ids
        )

    def federated_search(
        self,
        query: str,
        *,
        provider_ids: tuple[str, ...] | None = None,
        limit: int = 50,
        content_type: str = "all",
        cursor: str = "",
    ) -> FederatedSearchResult:
        selected = (
            tuple(
                capability.provider_id
                for capability in self.search_capabilities()
                if self._registry.is_enabled(capability.provider_id)
            )
            if provider_ids is None
            else tuple(provider_ids)
        )
        if len(set(selected)) != len(selected):
            raise ValueError("duplicate search MOD selection")
        available = {
            capability.provider_id for capability in self.search_capabilities()
        }
        unavailable = tuple(
            provider_id for provider_id in selected if provider_id not in available
        )
        if unavailable:
            raise RuntimeError(f"search MOD is unavailable: {unavailable[0]}")
        disabled = tuple(
            provider_id
            for provider_id in selected
            if not self._registry.is_enabled(provider_id)
        )
        if disabled:
            raise RuntimeError(f"search MOD is disabled: {disabled[0]}")
        if cursor and len(selected) != 1:
            raise ValueError("pagination requires one selected search MOD")
        provider_cursor = ""
        if cursor:
            provider_cursor = self._decode_search_cursor(
                cursor,
                provider_id=selected[0],
                query=query,
                content_type=content_type,
            )
        result = self._search_adapters.search(
            SearchQueryV2(query, content_type, limit, provider_cursor),
            provider_ids=selected,
            limit=limit,
        )
        failures = {
            failure.provider_id: failure.message for failure in result.failures
        }
        for provider_id in selected:
            health = self._search_health.setdefault(provider_id, _SearchHealth())
            if provider_id in failures:
                health.consecutive_failures = min(
                    health.consecutive_failures + 1, 1_000_000
                )
                health.message = failures[provider_id]
            else:
                health.consecutive_failures = 0
                health.successful_searches = min(
                    health.successful_searches + 1, 1_000_000
                )
                health.message = ""
        return FederatedSearchResult(
            result.items,
            result.failures,
            result.sources,
            tuple(
                (
                    provider_id,
                    self._encode_search_cursor(
                        provider_id=provider_id,
                        query=query,
                        content_type=content_type,
                        provider_cursor=next_cursor,
                    ),
                )
                for provider_id, next_cursor in result.next_cursors
            ),
        )

    @staticmethod
    def _normalized_search_text(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("search query invalid")
        normalized = " ".join(query.split())[:200]
        if not normalized:
            raise ValueError("search query is empty")
        return normalized

    def _encode_search_cursor(
        self,
        *,
        provider_id: str,
        query: str,
        content_type: str,
        provider_cursor: str,
    ) -> str:
        payload = json.dumps(
            [
                1,
                provider_id,
                self._normalized_search_text(query),
                content_type,
                provider_cursor,
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.new(
            self._search_cursor_key, payload, hashlib.sha256
        ).digest()[:16]
        encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
        encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
        token = b"sc1." + encoded_payload + b"." + encoded_signature
        if len(token) > 2048:
            raise ValueError("search cursor is too large")
        return token.decode("ascii")

    def _decode_search_cursor(
        self,
        token: str,
        *,
        provider_id: str,
        query: str,
        content_type: str,
    ) -> str:
        if not isinstance(token, str) or not 1 <= len(token) <= 2048:
            raise ValueError("search cursor invalid")
        try:
            prefix, payload_text, signature_text = token.split(".")
            if prefix != "sc1":
                raise ValueError
            payload = base64.urlsafe_b64decode(
                payload_text + "=" * (-len(payload_text) % 4)
            )
            signature = base64.urlsafe_b64decode(
                signature_text + "=" * (-len(signature_text) % 4)
            )
            if (
                base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
                != payload_text
                or base64.urlsafe_b64encode(signature)
                .rstrip(b"=")
                .decode("ascii")
                != signature_text
            ):
                raise ValueError
            expected = hmac.new(
                self._search_cursor_key, payload, hashlib.sha256
            ).digest()[:16]
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            values = json.loads(payload.decode("utf-8"))
        except (
            binascii.Error,
            UnicodeDecodeError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            raise ValueError("search cursor invalid") from None
        if (
            not isinstance(values, list)
            or len(values) != 5
            or values[0] != 1
            or values[1] != provider_id
            or values[2] != self._normalized_search_text(query)
            or values[3] != content_type
            or not isinstance(values[4], str)
            or len(values[4]) > 500
        ):
            raise ValueError("search cursor does not match this search")
        return values[4]

    def register_video_preview(
        self, provider: VideoPreviewProvider, *, enabled: bool = False
    ) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._video_preview_providers[provider.provider_id] = provider

    def video_preview_provider(
        self, provider_id: str = "youtube-player"
    ) -> VideoPreviewProvider:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("video player MOD is disabled")
        provider = self._video_preview_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("video player MOD is unavailable")
        return provider




    def register_similar(
        self, provider: SimilarProvider, *, enabled: bool = False
    ) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._similar_providers[provider.provider_id] = provider

    def register_split(
        self, provider: SplitProvider, *, enabled: bool = False
    ) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._split_providers[provider.provider_id] = provider

    def split_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        chapters: list[dict[str, object]],
        description: str,
        provider_id: str = "youtube-auto-split",
    ) -> SplitPlanV1:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("auto-split MOD is disabled")
        provider = self._split_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("auto-split MOD is unavailable")
        return provider.split_plan(
            source_url=source_url,
            source_title=source_title,
            duration=duration,
            chapters=chapters,
            description=description,
        )

    def split_audio_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        input_path: Path,
        threshold_db: float = -35.0,
        min_silence: float = 1.2,
        provider_id: str = "youtube-auto-split",
    ) -> SplitPlanV1:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("auto-split MOD is disabled")
        provider = self._split_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("auto-split MOD is unavailable")
        return provider.split_audio_plan(
            source_url=source_url,
            source_title=source_title,
            duration=duration,
            input_path=input_path,
            threshold_db=threshold_db,
            min_silence=min_silence,
        )

    def split_filename(
        self,
        *,
        source_title: str,
        index: int,
        track_title: str,
        start: float,
        duration: float,
        extension: str,
        provider_id: str = "youtube-auto-split",
    ) -> str:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("auto-split MOD is disabled")
        provider = self._split_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("auto-split MOD is unavailable")
        return provider.split_filename(
            source_title=source_title,
            index=index,
            track_title=track_title,
            start=start,
            duration=duration,
            extension=extension,
        )

    def similar_candidate(
        self,
        original: DiscoveryItemV1,
        *,
        provider_id: str = "youtube-similar",
        limit: int = 12,
    ) -> SimilarSelectionV1 | None:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("similar MOD is disabled")
        provider = self._similar_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("similar MOD is unavailable")
        search_provider_id = _SIMILAR_SEARCH_BINDINGS.get(provider_id)
        if search_provider_id is None:
            raise RuntimeError("similar MOD has no bound search source")
        _require_bound_original_source(original, search_provider_id)
        preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
        if self._registry.is_enabled("youtube-history"):
            try:
                preferences = self.history_preferences()
            except (OSError, RuntimeError, ValueError):
                pass
        plan = provider.similar_plan(original, preferences)
        bounded_limit = max(1, min(int(limit), 50))
        unique: dict[str, DiscoveryItemV1] = {}
        for query in plan.queries:
            for item in self.search(
                query,
                provider_id=search_provider_id,
                limit=bounded_limit,
            ):
                if item.video_id != original.video_id:
                    unique.setdefault(item.video_id, item)
        return provider.select_similar(
            original, tuple(unique.values()), preferences
        )

    def similar_candidates(
        self,
        original: DiscoveryItemV1,
        *,
        provider_id: str = "youtube-similar",
        limit: int = 12,
    ) -> tuple[SimilarSelectionV1, ...]:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("similar MOD is disabled")
        provider = self._similar_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("similar MOD is unavailable")
        search_provider_id = _SIMILAR_SEARCH_BINDINGS.get(provider_id)
        if search_provider_id is None:
            raise RuntimeError("similar MOD has no bound search source")
        _require_bound_original_source(original, search_provider_id)
        preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
        if self._registry.is_enabled("youtube-history"):
            try:
                preferences = self.history_preferences()
            except (OSError, RuntimeError, ValueError):
                pass
        plan = provider.similar_plan(original, preferences)
        bounded_limit = max(1, min(int(limit), 50))
        unique: dict[str, DiscoveryItemV1] = {}
        for query in plan.queries:
            for item in self.search(
                query,
                provider_id=search_provider_id,
                limit=bounded_limit,
            ):
                if item.video_id != original.video_id:
                    unique.setdefault(item.video_id, item)
        return provider.rank_similar(
            original,
            tuple(unique.values()),
            preferences,
            limit=bounded_limit,
        )

    def register_recovery(
        self, provider: RecoveryProvider, *, enabled: bool = False
    ) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._recovery_providers[provider.provider_id] = provider

    def replacement_candidates(
        self,
        original: DiscoveryItemV1,
        *,
        provider_id: str = "youtube-recovery",
        limit: int = 12,
    ) -> tuple[RecoveryCandidateV1, ...]:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("recovery MOD is disabled")
        provider = self._recovery_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("recovery MOD is unavailable")
        search_provider_id = _RECOVERY_SEARCH_BINDINGS.get(provider_id)
        if search_provider_id is None:
            raise RuntimeError("recovery MOD has no bound search source")
        _require_bound_original_source(original, search_provider_id)
        bounded_limit = max(1, min(int(limit), 50))
        plan = provider.recovery_plan(original)
        for query in (plan.primary_query, *plan.fallback_queries):
            results = self.search(
                query,
                provider_id=search_provider_id,
                limit=bounded_limit,
            )
            ranked = provider.rank_recovery(original, results)
            if ranked:
                return ranked[:bounded_limit]
        return ()

    def register_history(
        self, provider: HistoryProvider, *, enabled: bool = False
    ) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._history_providers[provider.provider_id] = provider

    def record_history(
        self,
        event_type: str,
        query: str,
        item: DiscoveryItemV1 | None = None,
        *,
        provider_id: str = "youtube-history",
    ) -> None:
        provider = self._enabled_history_provider(provider_id)
        provider.record_history(event_type, query, item)

    def recent_history(
        self, *, provider_id: str = "youtube-history", limit: int = 20
    ) -> tuple[HistoryEventV1, ...]:
        return self._enabled_history_provider(provider_id).recent_history(limit=limit)

    def history_preferences(
        self, *, provider_id: str = "youtube-history"
    ) -> HistoryPreferencesV1:
        return self._enabled_history_provider(provider_id).history_preferences()

    def _enabled_history_provider(self, provider_id: str) -> HistoryProvider:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("history MOD is disabled")
        provider = self._history_providers.get(provider_id)
        if provider is None:
            raise RuntimeError("history MOD is unavailable")
        return provider

    def statuses(self) -> tuple[ProviderStatus, ...]:
        return self._registry.statuses()

    def is_enabled(self, provider_id: str) -> bool:
        return self._registry.is_enabled(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        self._registry.set_enabled(provider_id, enabled)

    def search(
        self,
        query: str,
        *,
        provider_id: str = "youtube-search",
        limit: int = 12,
        content_type: str = "all",
    ) -> tuple[DiscoveryItemV1, ...]:
        if not self._registry.is_enabled(provider_id):
            raise RuntimeError("search MOD is disabled")
        provider = self._providers.get(provider_id)
        if provider is None:
            raise RuntimeError("search MOD is unavailable")
        if content_type not in {"all", "music", "video"}:
            raise ValueError("search content type is invalid")
        return provider.search(
            query,
            limit=limit,
            content_type=content_type,
        )

    def close(self) -> None:
        self._registry.close()
