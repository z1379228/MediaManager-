"""Core-owned YouTube download performance profiles."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from functools import lru_cache
import os
import sys


YOUTUBE_PERFORMANCE_PROFILE_SCHEMA = 1
DEFAULT_YOUTUBE_PERFORMANCE_PROFILE = "balanced"
YOUTUBE_PERFORMANCE_OPTION_KEYS = frozenset(
    {
        "_core_performance_schema",
        "_core_performance_profile",
        "_core_worker_count",
        "_core_fragment_concurrency",
        "_core_fragment_budget",
    }
)


@dataclass(frozen=True, slots=True)
class YouTubePerformanceProfile:
    profile_id: str
    display_name: str
    description: str
    recommended_workers: int
    maximum_workers: int
    fragment_budget: int
    maximum_fragments_per_task: int


@dataclass(frozen=True, slots=True)
class SystemResourceSnapshot:
    """Stable machine capacity used by the non-polling automatic profile."""

    logical_processors: int | None
    total_memory_bytes: int | None


@dataclass(frozen=True, slots=True)
class ResolvedYouTubePerformance:
    profile: YouTubePerformanceProfile
    effective_profile: YouTubePerformanceProfile
    worker_count: int
    fragment_concurrency: int

    @property
    def maximum_fragment_concurrency(self) -> int:
        return self.worker_count * self.fragment_concurrency

    def provider_options(self) -> tuple[tuple[str, str], ...]:
        """Return the complete, versioned core-to-provider performance contract."""

        return (
            (
                "_core_performance_schema",
                str(YOUTUBE_PERFORMANCE_PROFILE_SCHEMA),
            ),
            (
                "_core_performance_profile",
                self.effective_profile.profile_id,
            ),
            ("_core_worker_count", str(self.worker_count)),
            ("_core_fragment_concurrency", str(self.fragment_concurrency)),
            (
                "_core_fragment_budget",
                str(self.effective_profile.fragment_budget),
            ),
        )


_YOUTUBE_PERFORMANCE_PROFILES = (
    YouTubePerformanceProfile(
        "resource",
        "省資源",
        "全域只執行 1 個下載，降低 CPU、記憶體、磁碟與網路競爭。",
        1,
        2,
        2,
        2,
    ),
    YouTubePerformanceProfile(
        "balanced",
        "平衡",
        "全域同時執行 2 個下載，兼顧操作流暢度與下載速度。",
        2,
        4,
        4,
        2,
    ),
    YouTubePerformanceProfile(
        "high",
        "高速",
        "全域同時執行 4 個下載；網路、磁碟與 CPU 使用量可能增加。",
        4,
        4,
        8,
        4,
    ),
    YouTubePerformanceProfile(
        "auto",
        "自動",
        "啟動時依邏輯處理器與總記憶體保守分級，不持續輪詢系統負載。",
        2,
        4,
        4,
        4,
    ),
)
_YOUTUBE_PERFORMANCE_BY_ID = {
    profile.profile_id: profile for profile in _YOUTUBE_PERFORMANCE_PROFILES
}


def youtube_performance_profiles() -> tuple[YouTubePerformanceProfile, ...]:
    return _YOUTUBE_PERFORMANCE_PROFILES


def normalized_youtube_performance_profile(value: object) -> str:
    if isinstance(value, str) and value in _YOUTUBE_PERFORMANCE_BY_ID:
        return value
    return DEFAULT_YOUTUBE_PERFORMANCE_PROFILE


def _positive_integer(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _total_memory_bytes() -> int | None:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = (
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            )

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        try:
            succeeded = ctypes.windll.kernel32.GlobalMemoryStatusEx(
                ctypes.byref(status)
            )
        except (AttributeError, OSError):
            return None
        return _positive_integer(status.total_physical) if succeeded else None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    if not isinstance(page_size, int) or not isinstance(page_count, int):
        return None
    return _positive_integer(page_size * page_count)


@lru_cache(maxsize=1)
def detect_system_resources() -> SystemResourceSnapshot:
    """Read stable hardware capacity once without starting a monitor thread."""

    return SystemResourceSnapshot(
        _positive_integer(os.cpu_count()),
        _total_memory_bytes(),
    )


def automatic_youtube_performance_profile(
    resources: SystemResourceSnapshot | None = None,
) -> str:
    """Choose a conservative effective profile from stable machine capacity."""

    snapshot = resources or detect_system_resources()
    processors = _positive_integer(snapshot.logical_processors)
    memory = _positive_integer(snapshot.total_memory_bytes)
    if processors is None or memory is None:
        return DEFAULT_YOUTUBE_PERFORMANCE_PROFILE
    if processors <= 4 or memory < 8 * 1024**3:
        return "resource"
    if processors >= 12 and memory >= 16 * 1024**3:
        return "high"
    return "balanced"


def resolve_youtube_performance(
    profile_id: object,
    worker_count: object,
    *,
    system_resources: SystemResourceSnapshot | None = None,
) -> ResolvedYouTubePerformance:
    """Resolve a bounded profile without trusting persisted or UI values."""

    profile = _YOUTUBE_PERFORMANCE_BY_ID[
        normalized_youtube_performance_profile(profile_id)
    ]
    effective_profile = profile
    if profile.profile_id == "auto":
        effective_profile = _YOUTUBE_PERFORMANCE_BY_ID[
            automatic_youtube_performance_profile(system_resources)
        ]
        workers = effective_profile.recommended_workers
    else:
        workers = (
            worker_count
            if isinstance(worker_count, int) and not isinstance(worker_count, bool)
            else effective_profile.recommended_workers
        )
    workers = max(1, min(workers, effective_profile.maximum_workers, 4))
    fragments = min(
        effective_profile.maximum_fragments_per_task,
        max(1, effective_profile.fragment_budget // workers),
    )
    return ResolvedYouTubePerformance(
        profile,
        effective_profile,
        workers,
        fragments,
    )
