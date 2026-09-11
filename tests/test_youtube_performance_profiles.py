from __future__ import annotations

import pytest

from core.downloads.performance_profiles import (
    DEFAULT_YOUTUBE_PERFORMANCE_PROFILE,
    SystemResourceSnapshot,
    YOUTUBE_PERFORMANCE_OPTION_KEYS,
    automatic_youtube_performance_profile,
    normalized_youtube_performance_profile,
    resolve_youtube_performance,
    youtube_performance_profiles,
)


@pytest.mark.parametrize(
    ("processors", "memory_gib", "expected"),
    (
        (4, 4, "resource"),
        (8, 8, "balanced"),
        (12, 16, "high"),
        (24, 32, "high"),
    ),
)
def test_automatic_profile_uses_conservative_hardware_tiers(
    processors: int,
    memory_gib: int,
    expected: str,
) -> None:
    resources = SystemResourceSnapshot(processors, memory_gib * 1024**3)

    assert automatic_youtube_performance_profile(resources) == expected


@pytest.mark.parametrize(
    "resources",
    (
        SystemResourceSnapshot(None, 16 * 1024**3),
        SystemResourceSnapshot(12, None),
        SystemResourceSnapshot(None, None),
    ),
)
def test_automatic_profile_stays_balanced_when_capacity_is_incomplete(
    resources: SystemResourceSnapshot,
) -> None:
    assert automatic_youtube_performance_profile(resources) == "balanced"


def test_profiles_have_stable_unique_ids_and_bounded_allocations() -> None:
    profiles = youtube_performance_profiles()

    assert tuple(profile.profile_id for profile in profiles) == (
        "resource",
        "balanced",
        "high",
        "auto",
    )
    assert len({profile.profile_id for profile in profiles}) == len(profiles)
    for profile in profiles:
        for requested_workers in range(1, 5):
            resolved = resolve_youtube_performance(
                profile.profile_id,
                requested_workers,
            )
            assert 1 <= resolved.worker_count <= profile.maximum_workers
            assert 1 <= resolved.fragment_concurrency <= 4
            assert (
                resolved.maximum_fragment_concurrency
                <= resolved.effective_profile.fragment_budget
            )


@pytest.mark.parametrize("value", (None, "", "turbo", 4, True))
def test_unknown_profile_defaults_to_balanced(value: object) -> None:
    assert (
        normalized_youtube_performance_profile(value)
        == DEFAULT_YOUTUBE_PERFORMANCE_PROFILE
    )


def test_resource_profile_clamps_global_workers() -> None:
    resolved = resolve_youtube_performance("resource", 4)

    assert resolved.worker_count == 2
    assert resolved.fragment_concurrency == 1
    assert dict(resolved.provider_options()).keys() == (
        YOUTUBE_PERFORMANCE_OPTION_KEYS
    )


def test_high_profile_uses_all_bounded_global_workers_by_default() -> None:
    resolved = resolve_youtube_performance("high", None)

    assert resolved.worker_count == 4
    assert resolved.fragment_concurrency == 2
    assert resolved.maximum_fragment_concurrency == 8


def test_auto_profile_uses_remaining_fragment_budget() -> None:
    resources = SystemResourceSnapshot(8, 8 * 1024**3)
    one_worker = resolve_youtube_performance(
        "auto", 1, system_resources=resources
    )
    four_workers = resolve_youtube_performance(
        "auto", 4, system_resources=resources
    )

    assert one_worker.worker_count == 2
    assert four_workers.worker_count == 2
    assert one_worker.fragment_concurrency == 2
    assert four_workers.fragment_concurrency == 2
    assert one_worker.effective_profile.profile_id == "balanced"
    assert four_workers.effective_profile.profile_id == "balanced"


def test_auto_profile_exposes_effective_provider_contract() -> None:
    resolved = resolve_youtube_performance(
        "auto",
        1,
        system_resources=SystemResourceSnapshot(16, 32 * 1024**3),
    )

    options = dict(resolved.provider_options())
    assert resolved.profile.profile_id == "auto"
    assert resolved.effective_profile.profile_id == "high"
    assert resolved.worker_count == 4
    assert options["_core_performance_profile"] == "high"
    assert options["_core_fragment_budget"] == "8"
