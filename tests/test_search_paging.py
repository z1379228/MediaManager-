from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult
from trusted_ui.search_paging import (
    MAX_WORKSPACE_SEARCH_RESULTS,
    merge_search_results,
    provider_next_cursor,
)


def item(video_id: str, url: str | None = None) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url or f"https://www.youtube.com/watch?v={video_id}",
        f"Title {video_id}",
        "Artist",
        120,
        "",
        "video",
        "",
    )


def test_provider_next_cursor_is_bound_to_the_requested_provider() -> None:
    response = FederatedSearchResult(
        (),
        (),
        (),
        (("youtube-search", "youtube-token"), ("bilibili-search", "bili-token")),
    )

    assert provider_next_cursor(response, "youtube-search") == "youtube-token"
    assert provider_next_cursor(response, "bilibili-search") == "bili-token"
    assert provider_next_cursor(response, "missing-search") == ""


def test_provider_next_cursor_rejects_oversized_tokens() -> None:
    response = FederatedSearchResult(
        (),
        (),
        (),
        (("youtube-search", "x" * 2049),),
    )

    assert provider_next_cursor(response, "youtube-search") == ""


def test_merge_search_results_deduplicates_tracking_aliases_and_bounds_size() -> None:
    existing = (item("one"), item("two"))
    incoming = (
        item("one", "https://www.youtube.com/watch?v=one&utm_source=page2"),
        item("three"),
    )

    assert tuple(entry.video_id for entry in merge_search_results(existing, incoming)) == (
        "one",
        "two",
        "three",
    )
    oversized = tuple(item(str(index)) for index in range(250))
    assert len(merge_search_results((), oversized)) == MAX_WORKSPACE_SEARCH_RESULTS
