"""Download services used by the MediaManager 1.0 interface."""

from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.downloads.provider_registry import DownloadProviderRegistry
from core.downloads.queue import DownloadQueue
from core.downloads.subprocess_provider import SubprocessDownloadProvider

__all__ = [
    "DownloadProviderRegistry",
    "DownloadQueue",
    "DownloadRequest",
    "DownloadState",
    "DownloadTask",
    "SubprocessDownloadProvider",
]
