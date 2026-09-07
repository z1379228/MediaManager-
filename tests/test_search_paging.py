from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.adapters import FederatedSearchResult, SearchAdapterFailure
from trusted_ui.search_paging import (
    MAX_WORKSPACE_SEARCH_RESULTS,
    merge_federated_search_pages,
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


def test_merge_search_results_preserves_case_sensitive_media_ids_across_pages() -> None:
    existing = (item("AbC123"),)
    incoming = (item("aBc123"),)

    assert tuple(
        entry.video_id for entry in merge_search_results(existing, incoming)
    ) == ("AbC123", "aBc123")


def test_merge_search_results_deduplicates_official_youtube_host_aliases() -> None:
    existing = (
        item("SameId", "https://www.youtube.com/watch?v=SameId"),
    )
    incoming = (
        item("SameId", "https://youtu.be/SameId"),
        item("SameId", "https://example.com/watch?v=SameId"),
    )

    merged = merge_search_results(existing, incoming)

    assert tuple(entry.url for entry in merged) == (
        "https://www.youtube.com/watch?v=SameId",
        "https://example.com/watch?v=SameId",
    )


def test_merge_federated_search_pages_preserves_sources_and_retry_cursor() -> None:
    first = FederatedSearchResult(
        (item("one"), item("two")),
        (),
        ("youtube-search", "youtube-search"),
        (("youtube-search", "first-cursor"),),
    )
    second = FederatedSearchResult(
        (
            item("two", "https://www.youtube.com/watch?v=two&utm_source=next"),
            item("three"),
        ),
        (),
        ("youtube-search", "bilibili-search"),
        (("youtube-search", "second-cursor"),),
    )

    merged = merge_federated_search_pages(first, second)

    assert tuple(entry.video_id for entry in merged.items) == (
        "one",
        "two",
        "three",
    )
    assert merged.sources == (
        "youtube-search",
        "youtube-search",
        "bilibili-search",
    )
    assert merged.next_cursors == (("youtube-search", "second-cursor"),)

    failure = SearchAdapterFailure(
        "youtube-search", "temporary failure", "unavailable"
    )
    retriable = merge_federated_search_pages(
        merged,
        FederatedSearchResult((), (failure,), ()),
    )
    assert retriable.items == merged.items
    assert retriable.failures == (failure,)
    assert retriable.next_cursors == merged.next_cursors


def test_merge_federated_search_pages_drops_cursor_at_workspace_limit() -> None:
    existing_items = tuple(item(f"existing-{index}") for index in range(199))
    existing = FederatedSearchResult(
        existing_items,
        (),
        tuple("youtube-search" for _ in existing_items),
        (("youtube-search", "first-cursor"),),
    )
    incoming = FederatedSearchResult(
        (item("new-200"), item("overflow-201")),
        (),
        ("youtube-search", "youtube-search"),
        (("youtube-search", "unused-cursor"),),
    )

    merged = merge_federated_search_pages(existing, incoming)

    assert len(merged.items) == MAX_WORKSPACE_SEARCH_RESULTS
    assert merged.items[-1].video_id == "new-200"
    assert merged.next_cursors == ()
