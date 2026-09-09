"""Core-owned YouTube download performance profiles."""
from __future__ import annotations

from dataclasses import dataclass


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
class ResolvedYouTubePerformance:
    profile: YouTubePerformanceProfile
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
            ("_core_performance_profile", self.profile.profile_id),
            ("_core_worker_count", str(self.worker_count)),
            ("_core_fragment_concurrency", str(self.fragment_concurrency)),
            ("_core_fragment_budget", str(self.profile.fragment_budget)),
        )


_YOUTUBE_PERFORMANCE_PROFILES = (
    YouTubePerformanceProfile(
        "resource",
        "省資源",
        "降低背景 CPU、記憶體與網路競爭，適合長時間開啟。",
        1,
        2,
        2,
        2,
    ),
    YouTubePerformanceProfile(
        "balanced",
        "平衡",
        "兼顧操作流暢度與下載速度，建議一般使用。",
        2,
        4,
        4,
        2,
    ),
    YouTubePerformanceProfile(
        "high",
        "高速",
        "提高片段並行量；網路、磁碟與 CPU 使用量可能增加。",
        2,
        4,
        8,
        4,
    ),
    YouTubePerformanceProfile(
        "auto",
        "自動",
        "依全域同時工作數分配固定片段配額。",
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


def resolve_youtube_performance(
    profile_id: object,
    worker_count: object,
) -> ResolvedYouTubePerformance:
    """Resolve a bounded profile without trusting persisted or UI values."""

    profile = _YOUTUBE_PERFORMANCE_BY_ID[
        normalized_youtube_performance_profile(profile_id)
    ]
    workers = (
        worker_count
        if isinstance(worker_count, int) and not isinstance(worker_count, bool)
        else profile.recommended_workers
    )
    workers = max(1, min(workers, profile.maximum_workers, 4))
    fragments = min(
        profile.maximum_fragments_per_task,
        max(1, profile.fragment_budget // workers),
    )
    return ResolvedYouTubePerformance(profile, workers, fragments)
