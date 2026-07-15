"""Provider registration, routing and enable/disable boundary."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import json
from pathlib import Path
from threading import Event, RLock
from typing import Any
from urllib.parse import urlsplit

from contracts.playlist_v1 import PlaylistEntryV1
from contracts.download_provider import DownloadProvider
from contracts.download_capability_v2 import (
    DownloadCapabilityError,
    DownloadCapabilityV2,
)
from core.downloads.negotiation import negotiate_download
from core.downloads.models import DownloadRequest


class ProviderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider_id: str
    display_name: str
    enabled: bool
    available: bool = True
    reason: str = ""


class DownloadProviderRegistry:
    def __init__(self, state_path: Path | None = None) -> None:
        self._providers: dict[str, DownloadProvider] = {}
        self._capabilities: dict[str, DownloadCapabilityV2] = {}
        self._unavailable: dict[str, tuple[str, str, frozenset[str]]] = {}
        self._enabled: set[str] = set()
        self._lock = RLock()
        self._state_path = state_path
        self._saved = self._load_state()

    def register(self, provider: DownloadProvider, *, enabled: bool = False) -> None:
        if not provider.provider_id or provider.provider_id in self._providers:
            raise ValueError("download provider id is empty or already registered")
        with self._lock:
            self._providers[provider.provider_id] = provider
            self._unavailable.pop(provider.provider_id, None)
            if self._saved.get(provider.provider_id, enabled):
                self._enabled.add(provider.provider_id)

    def register_unavailable(
        self,
        provider_id: str,
        display_name: str,
        reason: str,
        *,
        hosts: Iterable[str] = (),
    ) -> None:
        """Expose a failed built-in MOD without making it routable."""

        normalized_reason = " ".join(str(reason).split())[:240]
        normalized_hosts = frozenset(str(host).strip().casefold() for host in hosts)
        if (
            not provider_id
            or not display_name
            or not normalized_reason
            or any(not host or "/" in host or "\\" in host for host in normalized_hosts)
        ):
            raise ValueError("unavailable provider metadata is invalid")
        with self._lock:
            if provider_id in self._providers:
                raise ValueError("download provider is already registered")
            self._unavailable[provider_id] = (
                display_name,
                normalized_reason,
                normalized_hosts,
            )
            self._enabled.discard(provider_id)

    def statuses(self) -> tuple[ProviderStatus, ...]:
        with self._lock:
            available = {
                key: ProviderStatus(
                    key,
                    provider.display_name,
                    key in self._enabled,
                )
                for key, provider in self._providers.items()
            }
            unavailable = {
                key: ProviderStatus(key, values[0], False, False, values[1])
                for key, values in self._unavailable.items()
            }
            return tuple(
                {**unavailable, **available}[key]
                for key in sorted(set(unavailable) | set(available))
            )

    def register_capability(self, capability: DownloadCapabilityV2) -> None:
        with self._lock:
            if capability.provider_id not in self._providers:
                raise KeyError(capability.provider_id)
            if capability.provider_id in self._capabilities:
                raise ValueError("download capability is already registered")
            self._capabilities[capability.provider_id] = capability

    def capability_for(self, url: str) -> DownloadCapabilityV2 | None:
        provider_id = self.matching_provider_id(url)
        with self._lock:
            return self._capabilities.get(provider_id) if provider_id else None

    def capability_for_provider(
        self, provider_id: str
    ) -> DownloadCapabilityV2 | None:
        with self._lock:
            return self._capabilities.get(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        with self._lock:
            if provider_id not in self._providers:
                unavailable = self._unavailable.get(provider_id)
                if unavailable is not None:
                    raise ProviderUnavailableError(
                        f"{unavailable[0]} MOD 初始化失敗：{unavailable[1]}"
                    )
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
        unavailable = self._unavailable_for_url(url)
        if unavailable is not None:
            return unavailable[0]
        return None

    def provider_for(self, url: str) -> DownloadProvider:
        with self._lock:
            providers = tuple(self._providers.items())
            enabled = frozenset(self._enabled)
        for provider_id, provider in providers:
            if provider.supports(url):
                if provider_id in enabled:
                    return provider
                raise ProviderUnavailableError(
                    f"{provider.display_name} MOD 尚未啟用"
                )
        unavailable = self._unavailable_for_url(url)
        if unavailable is not None:
            _provider_id, display_name, reason = unavailable
            raise ProviderUnavailableError(
                f"{display_name} MOD 初始化失敗：{reason}"
            )
        raise ProviderUnavailableError("沒有已啟用的下載 MOD 支援此網址")

    def _unavailable_for_url(self, url: str) -> tuple[str, str, str] | None:
        try:
            parsed = urlsplit(url)
            parsed.port
        except (TypeError, ValueError):
            return None
        host = (parsed.hostname or "").casefold()
        if parsed.scheme.casefold() not in {"http", "https"} or not host:
            return None
        with self._lock:
            unavailable = tuple(self._unavailable.items())
        for provider_id, (display_name, reason, hosts) in unavailable:
            if host in hosts:
                return provider_id, display_name, reason
        return None

    def analyze(self, url: str) -> dict[str, Any]:
        return self.provider_for(url).analyze(url)

    def playlist(
        self, url: str, *, limit: int = 500
    ) -> tuple[PlaylistEntryV1, ...]:
        provider = self.provider_for(url)
        with self._lock:
            capability = self._capabilities.get(provider.provider_id)
        if capability is not None and not capability.supports_playlist:
            raise ValueError("download MOD does not support playlists")
        bounded_limit = (
            min(limit, capability.max_batch_size) if capability is not None else limit
        )
        return provider.playlist(url, limit=bounded_limit)

    def validate_batch(self, requests: Iterable[DownloadRequest]) -> None:
        values = tuple(requests)
        if not values:
            raise ValueError("download batch is empty")
        counts: dict[str, int] = {}
        capabilities: dict[str, DownloadCapabilityV2 | None] = {}
        for request in values:
            provider = self.provider_for(request.url)
            provider_id = provider.provider_id
            counts[provider_id] = counts.get(provider_id, 0) + 1
            if provider_id not in capabilities:
                capabilities[provider_id] = self.capability_for_provider(provider_id)
            capability = capabilities[provider_id]
            if capability is not None:
                negotiate_download(request, capability)
        for provider_id, count in counts.items():
            capability = capabilities[provider_id]
            if capability is not None and count > capability.max_batch_size:
                raise DownloadCapabilityError(
                    f"download batch exceeds {provider_id} limit "
                    f"({count}/{capability.max_batch_size})"
                )

    def download(
        self,
        request: DownloadRequest,
        progress: Callable[[dict[str, Any]], None],
        cancel_event: Event,
    ) -> str:
        provider = self.provider_for(request.url)
        with self._lock:
            capability = self._capabilities.get(provider.provider_id)
        if capability is not None:
            negotiate_download(request, capability)
        return provider.download(request, progress, cancel_event)

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


