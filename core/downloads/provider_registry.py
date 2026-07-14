"""Provider registration, routing and enable/disable boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
from threading import Event, RLock
from typing import Any

from contracts.playlist_v1 import PlaylistEntryV1
from contracts.download_provider import DownloadProvider
from core.downloads.models import DownloadRequest


class ProviderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider_id: str
    display_name: str
    enabled: bool


class DownloadProviderRegistry:
    def __init__(self, state_path: Path | None = None) -> None:
        self._providers: dict[str, DownloadProvider] = {}
        self._enabled: set[str] = set()
        self._lock = RLock()
        self._state_path = state_path
        self._saved = self._load_state()

    def register(self, provider: DownloadProvider, *, enabled: bool = False) -> None:
        if not provider.provider_id or provider.provider_id in self._providers:
            raise ValueError("download provider id is empty or already registered")
        with self._lock:
            self._providers[provider.provider_id] = provider
            if self._saved.get(provider.provider_id, enabled):
                self._enabled.add(provider.provider_id)

    def statuses(self) -> tuple[ProviderStatus, ...]:
        with self._lock:
            return tuple(
                ProviderStatus(key, provider.display_name, key in self._enabled)
                for key, provider in sorted(self._providers.items())
            )

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        with self._lock:
            if provider_id not in self._providers:
                raise KeyError(provider_id)
            if enabled:
                self._enabled.add(provider_id)
            else:
                self._enabled.discard(provider_id)
            self._saved[provider_id] = enabled
            self._save_state()

    def is_enabled(self, provider_id: str) -> bool:
        with self._lock:
            return provider_id in self._enabled

    def matching_provider_id(self, url: str) -> str | None:
        """Return the registered owner of a URL regardless of enabled state."""

        with self._lock:
            providers = tuple(self._providers.items())
        for provider_id, provider in providers:
            if provider.supports(url):
                return provider_id
        return None

    def provider_for(self, url: str) -> DownloadProvider:
        with self._lock:
            providers = tuple(
                provider for key, provider in self._providers.items() if key in self._enabled
            )
        for provider in providers:
            if provider.supports(url):
                return provider
        raise ProviderUnavailableError("no enabled MOD supports this URL")

    def analyze(self, url: str) -> dict[str, Any]:
        return self.provider_for(url).analyze(url)

    def playlist(
        self, url: str, *, limit: int = 500
    ) -> tuple[PlaylistEntryV1, ...]:
        return self.provider_for(url).playlist(url, limit=limit)

    def download(
        self,
        request: DownloadRequest,
        progress: Callable[[dict[str, Any]], None],
        cancel_event: Event,
    ) -> str:
        return self.provider_for(request.url).download(request, progress, cancel_event)

    def _load_state(self) -> dict[str, bool]:
        if self._state_path is None or not self._state_path.is_file():
            return {}
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            return {str(key): value for key, value in raw.items() if isinstance(value, bool)} if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._saved, indent=2), encoding="utf-8")
        temporary.replace(self._state_path)

    def close(self) -> None:
        with self._lock:
            providers = tuple(self._providers.values())
            self._enabled.clear()
        for provider in providers:
            provider.close()


