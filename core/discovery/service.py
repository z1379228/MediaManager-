"""Registry and routing boundary for lightweight discovery MODs."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1
from contracts.recovery_v1 import RecoveryCandidateV1, RecoveryPlanV1
from contracts.similar_v1 import SimilarPlanV1, SimilarSelectionV1
from contracts.split_plan_v1 import SplitPlanV1
from core.downloads.provider_registry import (
    DownloadProviderRegistry,
    ProviderStatus,
)


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

    def close(self) -> None: ...


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
        self._history_providers: dict[str, HistoryProvider] = {}
        self._recovery_providers: dict[str, RecoveryProvider] = {}
        self._similar_providers: dict[str, SimilarProvider] = {}
        self._split_providers: dict[str, SplitProvider] = {}
        self._video_preview_providers: dict[str, VideoPreviewProvider] = {}

    def register(self, provider: SearchProvider, *, enabled: bool = False) -> None:
        self._registry.register(provider, enabled=enabled)  # type: ignore[arg-type]
        self._providers[provider.provider_id] = provider

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
        preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
        if self._registry.is_enabled("youtube-history"):
            try:
                preferences = self.history_preferences()
            except (OSError, RuntimeError, ValueError):
                pass
        plan = provider.similar_plan(original, preferences)
        bounded_limit = max(1, min(int(limit), 20))
        unique: dict[str, DiscoveryItemV1] = {}
        for query in plan.queries:
            for item in self.search(query, limit=bounded_limit):
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
        preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
        if self._registry.is_enabled("youtube-history"):
            try:
                preferences = self.history_preferences()
            except (OSError, RuntimeError, ValueError):
                pass
        plan = provider.similar_plan(original, preferences)
        bounded_limit = max(1, min(int(limit), 20))
        unique: dict[str, DiscoveryItemV1] = {}
        for query in plan.queries:
            for item in self.search(query, limit=bounded_limit):
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
        bounded_limit = max(1, min(int(limit), 20))
        plan = provider.recovery_plan(original)
        for query in (plan.primary_query, *plan.fallback_queries):
            results = self.search(query, limit=bounded_limit)
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
