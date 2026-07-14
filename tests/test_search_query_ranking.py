from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.query_ranking import (
    matching_search_indices,
    prepare_search_query,
    rank_search_results,
)


def _item(video_id: str, title: str, artist: str) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        f"https://example.test/{video_id}",
        title,
        artist,
        120,
        "",
        "music",
        "",
    )


def test_query_alias_and_typo_correction_is_bounded() -> None:
    prepared = prepare_search_query("  LO-FI   offical lyrcis  ")

    assert prepared.query == "lofi official lyrics"
    assert prepared.corrections == (
        "lo-fi → lofi",
        "offical → official",
        "lyrcis → lyrics",
    )


def test_local_ranking_is_stable_and_explainable() -> None:
    items = (
        _item("weak", "Live recording", "Other"),
        _item("artist", "Live recording", "Example Artist"),
        _item("title", "Example Song official", "Artist"),
    )

    ranked = rank_search_results("example song", items)

    assert [item.index for item in ranked] == [2, 1, 0]
    assert ranked[0].score == 60
    assert ranked[0].reasons == ("標題完整符合",)
    assert ranked[-1].score == 0


def test_local_duration_and_language_filters_preserve_order() -> None:
    items = (
        DiscoveryItemV1(
            "short-ja",
            "https://example.test/short-ja",
            "Short",
            "Artist",
            180,
            "ja",
            "music",
            "",
        ),
        DiscoveryItemV1(
            "long-ja",
            "https://example.test/long-ja",
            "Long",
            "Artist",
            1800,
            "ja",
            "music",
            "",
        ),
        DiscoveryItemV1(
            "unknown",
            "https://example.test/unknown",
            "Unknown",
            "Artist",
            None,
            "",
            "music",
            "",
        ),
    )

    assert matching_search_indices(
        items, minimum_duration=1200, language="ja"
    ) == (1,)
    assert matching_search_indices(items) == (0, 1, 2)
