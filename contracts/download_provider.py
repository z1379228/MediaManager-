"""Core-facing contract implemented by isolated download provider clients."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Any, Protocol

from contracts.playlist_v1 import PlaylistEntryV1
from core.downloads.models import DownloadRequest


class DownloadProvider(Protocol):
    provider_id: str
    display_name: str

    def supports(self, url: str) -> bool: ...

    def analyze(self, url: str) -> dict[str, Any]: ...

    def playlist(
        self, url: str, *, limit: int = 500
    ) -> tuple[PlaylistEntryV1, ...]: ...

    def download(
        self,
        request: DownloadRequest,
        progress: Callable[[dict[str, Any]], None],
        cancel_event: Event,
    ) -> str: ...

    def close(self) -> None: ...
