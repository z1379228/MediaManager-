from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryPreferencesV1
from contracts.similar_v1 import (
    SimilarContractError,
    SimilarPlanV1,
    SimilarSelectionV1,
)
from core.discovery.service import DiscoveryService
from core.downloads.subprocess_provider import SubprocessDownloadProvider


def item(
    video_id: str = "old",
    title: str = "Example Song",
    artist: str = "Artist",
) -> DiscoveryItemV1:
    return DiscoveryItemV1.from_dict(
        {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "artist": artist,
            "duration": 180,
            "language": "zh-TW",
            "category": "music",
            "thumbnail_url": "",
        }
    )


def preferences() -> HistoryPreferencesV1:
    return HistoryPreferencesV1(
        5,
        3,
        {"music": 3},
        {"zh-TW": 3},
        {"Preferred Artist": 2},
        {"music": 3},
    )


def test_similar_contract_validates_plan_and_selection() -> None:
    assert SimilarPlanV1.from_dict({"queries": ["Artist music"]}).queries == (
        "Artist music",
    )
    selection = SimilarSelectionV1.from_dict(
        {
            "item": {
                "video_id": "new",
                "url": "https://www.youtube.com/watch?v=new",
                "title": "Another Song",
                "artist": "Artist",
                "duration": 180,
                "language": "zh-TW",
                "category": "music",
                "thumbnail_url": "",
            },
            "score": 70,
            "reasons": ["artist", "category"],
        }
    )
    assert selection.item.video_id == "new"


def test_similar_contract_rejects_too_many_queries() -> None:
    with pytest.raises(SimilarContractError):
        SimilarPlanV1.from_dict({"queries": ["a", "b", "c", "d"]})


def test_similar_mod_excludes_original_and_selects_relevant_pool() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-similar"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
    )
    original = item()
    plan = provider.similar_plan(original, preferences())
    assert plan.queries[0] == "Artist Example Song"
    assert "Artist music" in plan.queries
    assert "Preferred Artist music" in plan.queries
    selection = provider.select_similar(
        original,
        (
            original,
            item("new", "Another Song", "Artist"),
            item("other", "Unrelated Clip", "Other"),
        ),
        preferences(),
    )
    assert selection is not None
    assert selection.item.video_id == "new"
    assert "artist" in selection.reasons
    provider.close()


def test_similar_mod_prioritizes_the_selected_artist_and_title_together() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-similar"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
    )
    original = item(title="Stay", artist="Aimer")
    try:
        plan = provider.similar_plan(
            original,
            HistoryPreferencesV1(0, 0, {}, {}, {}, {}),
        )

        assert plan.queries[0] == "Aimer Stay"
        assert "Aimer music" in plan.queries
        assert len(plan.queries) <= 3

        titled_plan = provider.similar_plan(
            item(title="Aimer - Stay", artist="Aimer"),
            HistoryPreferencesV1(0, 0, {}, {}, {}, {}),
        )
        assert titled_plan.queries[0] == "Aimer - Stay"

        short_artist_plan = provider.similar_plan(
            item(title="Stay", artist="A"),
            HistoryPreferencesV1(0, 0, {}, {}, {}, {}),
        )
        assert short_artist_plan.queries[0] == "A Stay"
    finally:
        provider.close()


def test_similar_mod_returns_multiple_ranked_results_with_fallbacks() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-similar"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
    )
    original = item()
    fallback = DiscoveryItemV1.from_dict(
        {
            "video_id": "fallback",
            "url": "https://www.youtube.com/watch?v=fallback",
            "title": "Unrelated Clip",
            "artist": "Unknown",
            "duration": 180,
            "language": "",
            "category": "",
            "thumbnail_url": "",
        }
    )
    results = provider.rank_similar(
        original,
        (
            original,
            item("best", "Example Song live", "Artist"),
            item("language", "Different Song", "Other"),
            fallback,
        ),
        preferences(),
        limit=12,
    )
    assert [result.item.video_id for result in results] == [
        "best",
        "language",
        "fallback",
    ]
    assert results[-1].score == 5
    assert results[-1].reasons == ("search-query",)
    provider.close()


def test_similar_mod_plans_and_scores_a_transformed_music_seed() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-similar"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
    )
    video_seed = replace(item(), category="video")
    music_seed = replace(video_seed, category="music")
    zero_preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
    try:
        plan = provider.similar_plan(music_seed, zero_preferences)
        assert plan.queries[0] == "Artist Example Song"
        assert "Artist music" in plan.queries
        assert all("video" not in query.casefold() for query in plan.queries)

        ranked = provider.rank_similar(
            music_seed,
            (item("candidate", "Different Song", "Other"),),
            zero_preferences,
            limit=12,
        )
        assert len(ranked) == 1
        assert "category" in ranked[0].reasons
    finally:
        provider.close()


def test_discovery_service_passes_local_preferences_to_similar(
    tmp_path: Path,
) -> None:
    original = item()
    replacement = item("new", "Another Song", "Artist")
    prefs = preferences()
    expected = SimilarSelectionV1(replacement, 60, ("artist", "category"))

    search = Mock()
    search.provider_id = "youtube-search"
    search.display_name = "YouTube Search"
    search.search.return_value = (replacement,)

    history = Mock()
    history.provider_id = "youtube-history"
    history.display_name = "YouTube History"
    history.history_preferences.return_value = prefs

    similar = Mock()
    similar.provider_id = "youtube-similar"
    similar.display_name = "YouTube Similar"
    similar.similar_plan.return_value = SimilarPlanV1(("Artist music",))
    similar.select_similar.return_value = expected

    service = DiscoveryService(tmp_path / "state.json")
    service.register(search, enabled=True)
    service.register_history(history, enabled=True)
    service.register_similar(similar, enabled=True)
    assert service.similar_candidate(original) == expected
    similar.similar_plan.assert_called_once_with(original, prefs)
    args = similar.select_similar.call_args.args
    assert args == (original, (replacement,), prefs)
    service.close()


def test_discovery_service_returns_bounded_similar_result_list(
    tmp_path: Path,
) -> None:
    original = item()
    first = item("first", "First Song", "Artist")
    second = item("second", "Second Song", "Artist")
    prefs = preferences()
    expected = (
        SimilarSelectionV1(first, 65, ("artist", "category")),
        SimilarSelectionV1(second, 55, ("artist",)),
    )

    search = Mock()
    search.provider_id = "youtube-search"
    search.display_name = "YouTube Search"
    search.search.return_value = (original, first, second, first)

    history = Mock()
    history.provider_id = "youtube-history"
    history.display_name = "YouTube History"
    history.history_preferences.return_value = prefs

    similar = Mock()
    similar.provider_id = "youtube-similar"
    similar.display_name = "YouTube Similar"
    similar.similar_plan.return_value = SimilarPlanV1(("Artist music",))
    similar.rank_similar.return_value = expected

    service = DiscoveryService(tmp_path / "state.json")
    service.register(search, enabled=True)
    service.register_history(history, enabled=True)
    service.register_similar(similar, enabled=True)
    assert service.similar_candidates(original, limit=50) == expected
    similar.rank_similar.assert_called_once_with(
        original,
        (first, second),
        prefs,
        limit=50,
    )
    search.search.assert_called_once_with(
        "Artist music",
        limit=50,
        content_type="all",
    )
    service.close()


def test_discovery_service_rejects_similar_before_planning_when_search_is_disabled(
    tmp_path: Path,
) -> None:
    original = item()
    search = Mock()
    search.provider_id = "youtube-search"
    search.display_name = "YouTube Search"
    similar = Mock()
    similar.provider_id = "youtube-similar"
    similar.display_name = "YouTube Similar"

    service = DiscoveryService(tmp_path / "state.json")
    service.register(search, enabled=False)
    service.register_similar(similar, enabled=True)
    try:
        with pytest.raises(RuntimeError, match="bound search MOD is disabled"):
            service.similar_candidate(original)
        with pytest.raises(RuntimeError, match="bound search MOD is disabled"):
            service.similar_candidates(original)
        similar.similar_plan.assert_not_called()
        search.search.assert_not_called()
    finally:
        service.close()


def test_discovery_service_scopes_similar_candidates_to_music(
    tmp_path: Path,
) -> None:
    original = replace(item(), category="video")
    music_seed = replace(original, category="music")
    candidate = item("music", "Music Candidate", "Artist")
    expected = (SimilarSelectionV1(candidate, 70, ("artist", "category")),)

    search = Mock()
    search.provider_id = "youtube-search"
    search.display_name = "YouTube Search"
    search.search.return_value = (original, candidate)

    history = Mock()
    history.provider_id = "youtube-history"
    history.display_name = "YouTube History"
    history.history_preferences.return_value = preferences()

    similar = Mock()
    similar.provider_id = "youtube-similar"
    similar.display_name = "YouTube Similar"
    similar.similar_plan.return_value = SimilarPlanV1(
        ("Artist Track music", "Artist music")
    )
    similar.rank_similar.return_value = expected

    service = DiscoveryService(tmp_path / "state.json")
    service.register(search, enabled=True)
    service.register_history(history, enabled=True)
    service.register_similar(similar, enabled=True)
    try:
        assert service.similar_candidates(
            original,
            limit=20,
            content_type="music",
            use_preferences=False,
        ) == expected
        assert search.search.call_args_list == [
            call("Artist Track music", limit=20, content_type="music"),
            call("Artist music", limit=20, content_type="music"),
        ]
        zero_preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})
        similar.similar_plan.assert_called_once_with(
            music_seed,
            zero_preferences,
        )
        similar.rank_similar.assert_called_once_with(
            music_seed,
            (candidate,),
            zero_preferences,
            limit=20,
        )
        history.history_preferences.assert_not_called()
        with pytest.raises(ValueError, match="similar content type"):
            service.similar_candidates(original, content_type="playlist")
        with pytest.raises(ValueError, match="preference mode"):
            service.similar_candidates(original, use_preferences="no")  # type: ignore[arg-type]
    finally:
        service.close()
