from __future__ import annotations

import pytest

from core.downloads.performance_profiles import (
    DEFAULT_YOUTUBE_PERFORMANCE_PROFILE,
    YOUTUBE_PERFORMANCE_OPTION_KEYS,
    normalized_youtube_performance_profile,
    resolve_youtube_performance,
    youtube_performance_profiles,
)


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
                <= profile.fragment_budget
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


def test_auto_profile_uses_remaining_fragment_budget() -> None:
    one_worker = resolve_youtube_performance("auto", 1)
    four_workers = resolve_youtube_performance("auto", 4)

    assert one_worker.fragment_concurrency == 4
    assert four_workers.fragment_concurrency == 1
    assert one_worker.maximum_fragment_concurrency == 4
    assert four_workers.maximum_fragment_concurrency == 4
