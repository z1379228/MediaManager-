from collections.abc import Iterator, Mapping
from unittest.mock import Mock

from contracts.discovery_v1 import DiscoveryItemV1
import pytest

from contracts.search_v2 import (
    SearchCapabilityV2,
    SearchContractV2Error,
    SearchPageV2,
    SearchQueryV2,
)
from core.discovery.adapters import SearchAdapterRegistry


def _item(video_id: str, *, url: str | None = None) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url or f"https://example.test/watch?v={video_id}",
        f"Track {video_id}",
        "Artist",
        120,
        "zh-TW",
        "music",
        "",
    )


def _capability(provider_id: str) -> SearchCapabilityV2:
    return SearchCapabilityV2.from_dict(
        {
            "provider_id": provider_id,
            "sites": ["youtube"],
            "content_types": ["all", "music"],
            "max_page_size": 20,
            "pagination": "none",
            "audio_preview": True,
            "video_preview": False,
        }
    )


def _wide_capability(provider_id: str) -> SearchCapabilityV2:
    return SearchCapabilityV2(
        provider_id,
        ("youtube",),
        ("all", "music", "video"),
        50,
        "offset",
        True,
        False,
    )


def test_search_query_is_normalized_and_bounded() -> None:
    query = SearchQueryV2("  synth   wave  ", "music", 200)
    assert query.normalized(_capability("one")) == SearchQueryV2(
        "synth wave", "music", 20, ""
    )


def test_direct_contract_construction_cannot_bypass_validation() -> None:
    with pytest.raises(SearchContractV2Error):
        SearchCapabilityV2("bad", (), ("all",), 20, "none", True, False)
    with pytest.raises(SearchContractV2Error, match="page size"):
        SearchQueryV2("music", page_size=True).normalized(_capability("one"))
    with pytest.raises(SearchContractV2Error):
        SearchPageV2("one", ("not-an-item",))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "query",
    (
        SearchQueryV2(""),
        SearchQueryV2(42),  # type: ignore[arg-type]
        SearchQueryV2("music", content_type=42),  # type: ignore[arg-type]
        SearchQueryV2("music", page_size=True),
        SearchQueryV2("music", cursor=42),  # type: ignore[arg-type]
    ),
)
def test_registry_validates_query_without_registered_sources(
    query: SearchQueryV2,
) -> None:
    registry = SearchAdapterRegistry()

    with pytest.raises(SearchContractV2Error):
        registry.search(query)


@pytest.mark.parametrize(
    "query",
    (
        SearchQueryV2(""),
        SearchQueryV2(42),  # type: ignore[arg-type]
        SearchQueryV2("music", content_type=42),  # type: ignore[arg-type]
        SearchQueryV2("music", page_size=True),
        SearchQueryV2("music", cursor=42),  # type: ignore[arg-type]
    ),
)
def test_registry_rejects_invalid_query_before_provider_dispatch(
    query: SearchQueryV2,
) -> None:
    registry = SearchAdapterRegistry()
    search = Mock(return_value=SearchPageV2("one", ()))
    registry.register(_capability("one"), search)

    with pytest.raises(SearchContractV2Error):
        registry.search(query, provider_ids=("one",))

    search.assert_not_called()


def test_registry_normalizes_non_query_contract_error() -> None:
    registry = SearchAdapterRegistry()

    with pytest.raises(SearchContractV2Error, match="search query invalid"):
        registry.search(None)  # type: ignore[arg-type]


def test_federated_search_deduplicates_and_isolates_failure() -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("one"),
        lambda query: SearchPageV2("one", (_item("same"), _item("unique"))),
    )
    registry.register(
        _capability("two"),
        lambda query: SearchPageV2("two", (_item("same"),)),
    )
    registry.register(
        _capability("broken"),
        lambda query: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = registry.search(SearchQueryV2("music"))

    assert [item.video_id for item in result.items] == ["same", "unique"]
    assert result.sources == ("one", "one")
    assert result.failures[0].provider_id == "broken"
    assert result.failures[0].message == "offline"
    assert result.failures[0].category == "error"


def test_registry_rejects_duplicate_provider_selection_before_dispatch() -> None:
    registry = SearchAdapterRegistry()
    search = Mock(
        return_value=SearchPageV2("one", (_item("one"),)),
    )
    registry.register(_capability("one"), search)

    with pytest.raises(ValueError, match="duplicate search MOD selection"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids=("one", "one"),
        )

    search.assert_not_called()


@pytest.mark.parametrize("provider_id", ("", 42))
def test_registry_rejects_invalid_provider_selection(
    provider_id: object,
) -> None:
    registry = SearchAdapterRegistry()

    with pytest.raises(ValueError, match="search MOD selection is invalid"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids=(provider_id,),  # type: ignore[arg-type]
        )


def test_registry_rejects_string_provider_selection_before_dispatch() -> None:
    registry = SearchAdapterRegistry()
    search = Mock(
        return_value=SearchPageV2("one", (_item("one"),)),
    )
    registry.register(_capability("one"), search)

    with pytest.raises(ValueError, match="search MOD selection is invalid"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids="one",
        )

    search.assert_not_called()


def test_registry_normalizes_non_iterable_provider_selection_error() -> None:
    registry = SearchAdapterRegistry()

    with pytest.raises(ValueError, match="search MOD selection is invalid"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids=42,  # type: ignore[arg-type]
        )


def test_registry_bounds_provider_selection_before_materializing() -> None:
    consumed: list[int] = []

    def provider_ids():
        for index in range(1000):
            consumed.append(index)
            yield f"source-{index}"

    registry = SearchAdapterRegistry()

    with pytest.raises(ValueError, match="too many search MODs selected"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids=provider_ids(),
        )

    assert consumed == list(range(17))


@pytest.mark.parametrize("limit", (True, "12", 1.5))
def test_registry_rejects_non_integer_result_limit_before_dispatch(
    limit: object,
) -> None:
    registry = SearchAdapterRegistry()
    search = Mock(
        return_value=SearchPageV2("one", (_item("one"),)),
    )
    registry.register(_capability("one"), search)

    with pytest.raises(ValueError, match="search result limit is invalid"):
        registry.search(
            SearchQueryV2("music"),
            provider_ids=("one",),
            limit=limit,  # type: ignore[arg-type]
        )

    search.assert_not_called()


@pytest.mark.parametrize(("limit", "expected"), ((0, 1), (999, 50)))
def test_registry_preserves_integer_result_limit_clamping(
    limit: int,
    expected: int,
) -> None:
    received: list[int] = []
    registry = SearchAdapterRegistry()

    def search(query: SearchQueryV2) -> SearchPageV2:
        received.append(query.page_size)
        return SearchPageV2("one", ())

    registry.register(_wide_capability("one"), search)

    registry.search(
        SearchQueryV2("music", page_size=999),
        provider_ids=("one",),
        limit=limit,
    )

    assert received == [expected]


@pytest.mark.parametrize(
    "malformed_url",
    (
        "https://[invalid",
        "https://user@www.youtube.com/watch?v=unsafe",
    ),
)
def test_federated_search_isolates_malformed_discovery_url(
    malformed_url: str,
) -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("malformed"),
        lambda query: SearchPageV2(
            "malformed",
            (_item("unsafe", url=malformed_url),),
        ),
    )
    registry.register(
        _capability("healthy"),
        lambda query: SearchPageV2("healthy", (_item("healthy"),)),
    )

    result = registry.search(SearchQueryV2("music"))

    assert tuple(item.video_id for item in result.items) == ("healthy",)
    assert result.sources == ("healthy",)
    assert len(result.failures) == 1
    assert result.failures[0].provider_id == "malformed"
    assert result.failures[0].category == "invalid-response"


def test_federated_search_keeps_same_id_from_different_sites() -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("youtube"),
        lambda query: SearchPageV2(
            "youtube", (_item("same", url="https://www.youtube.com/watch?v=same"),)
        ),
    )
    registry.register(
        _capability("bilibili"),
        lambda query: SearchPageV2(
            "bilibili", (_item("same", url="https://www.bilibili.com/video/same"),)
        ),
    )

    result = registry.search(SearchQueryV2("music"))

    assert len(result.items) == 2
    assert result.sources == ("youtube", "bilibili")


def test_federated_search_preserves_case_sensitive_media_ids() -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("youtube"),
        lambda query: SearchPageV2(
            "youtube",
            (
                _item(
                    "AbC123",
                    url="https://www.youtube.com/watch?v=AbC123",
                ),
                _item(
                    "aBc123",
                    url="https://www.youtube.com/watch?v=aBc123",
                ),
            ),
        ),
    )

    result = registry.search(SearchQueryV2("music"))

    assert [item.video_id for item in result.items] == ["AbC123", "aBc123"]


def test_federated_search_does_not_let_explicit_port_claim_youtube_identity(
) -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("external"),
        lambda query: SearchPageV2(
            "external",
            (_item("same", url="https://www.youtube.com:443/watch?v=same"),),
        ),
    )
    registry.register(
        _capability("youtube"),
        lambda query: SearchPageV2(
            "youtube",
            (_item("same", url="https://www.youtube.com/watch?v=same"),),
        ),
    )

    result = registry.search(SearchQueryV2("music"))

    assert len(result.items) == 2
    assert result.sources == ("external", "youtube")


def test_federated_search_classifies_timeout_and_invalid_response() -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _capability("timeout"),
        lambda query: (_ for _ in ()).throw(TimeoutError("slow")),
    )
    registry.register(
        _capability("invalid"),
        lambda query: (_ for _ in ()).throw(ValueError("bad page")),
    )

    result = registry.search(SearchQueryV2("music"))

    assert [item.category for item in result.failures] == [
        "timeout",
        "invalid-response",
    ]


def test_federated_search_preserves_provider_next_cursor() -> None:
    registry = SearchAdapterRegistry()
    capability = SearchCapabilityV2(
        "paged", ("example",), ("all",), 20, "cursor", False, False
    )
    registry.register(
        capability,
        lambda query: SearchPageV2("paged", (_item("one"),), "next-token"),
    )

    result = registry.search(SearchQueryV2("music"), provider_ids=("paged",))

    assert result.next_cursors == (("paged", "next-token"),)


def test_single_source_search_honors_its_bounded_page_capability() -> None:
    registry = SearchAdapterRegistry()
    received: list[int] = []

    def search(query: SearchQueryV2) -> SearchPageV2:
        received.append(query.page_size)
        return SearchPageV2(
            "youtube-search",
            tuple(_item(f"video-{index}") for index in range(query.page_size)),
            "50",
        )

    registry.register(_wide_capability("youtube-search"), search)

    result = registry.search(
        SearchQueryV2("music", page_size=50),
        provider_ids=("youtube-search",),
        limit=50,
    )

    assert received == [50]
    assert len(result.items) == 50
    assert result.next_cursors == (("youtube-search", "50"),)


def test_multi_source_search_keeps_per_provider_fanout_bounded() -> None:
    registry = SearchAdapterRegistry()
    received: dict[str, int] = {}

    def adapter(provider_id: str):
        def search(query: SearchQueryV2) -> SearchPageV2:
            received[provider_id] = query.page_size
            return SearchPageV2(
                provider_id,
                tuple(
                    _item(f"{provider_id}-{index}")
                    for index in range(query.page_size)
                ),
            )

        return search

    registry.register(_wide_capability("one"), adapter("one"))
    registry.register(_wide_capability("two"), adapter("two"))

    registry.search(
        SearchQueryV2("music", page_size=50),
        provider_ids=("one", "two"),
        limit=50,
    )

    assert received == {"one": 20, "two": 20}


def test_multi_source_paging_does_not_skip_unmerged_provider_results() -> None:
    registry = SearchAdapterRegistry()

    def adapter(provider_id: str):
        def search(query: SearchQueryV2) -> SearchPageV2:
            offset = int(query.cursor or "0")
            items = tuple(
                _item(f"{provider_id}-{index}")
                for index in range(offset, offset + query.page_size)
            )
            return SearchPageV2(
                provider_id,
                items,
                str(offset + query.page_size),
            )

        return search

    registry.register(_wide_capability("one"), adapter("one"))
    registry.register(_wide_capability("two"), adapter("two"))

    first = registry.search(
        SearchQueryV2("music", page_size=20),
        provider_ids=("one", "two"),
        limit=20,
    )
    second = registry.search(
        SearchQueryV2("music", page_size=20),
        provider_ids=("one", "two"),
        limit=20,
        provider_cursors=dict(first.next_cursors),
    )

    assert {
        item.video_id for item in (*first.items, *second.items)
    } == {
        *(f"one-{index}" for index in range(20)),
        *(f"two-{index}" for index in range(20)),
    }


def test_multi_source_search_rejects_page_larger_than_allocated_quota() -> None:
    registry = SearchAdapterRegistry()
    registry.register(
        _wide_capability("oversized"),
        lambda query: SearchPageV2(
            "oversized",
            tuple(_item(f"oversized-{index}") for index in range(20)),
            "20",
        ),
    )
    registry.register(
        _wide_capability("bounded"),
        lambda query: SearchPageV2(
            "bounded",
            tuple(_item(f"bounded-{index}") for index in range(query.page_size)),
            str(query.page_size),
        ),
    )

    result = registry.search(
        SearchQueryV2("music", page_size=6),
        provider_ids=("oversized", "bounded"),
        limit=6,
    )

    assert tuple(item.video_id for item in result.items) == (
        "bounded-0",
        "bounded-1",
        "bounded-2",
    )
    assert result.next_cursors == (("bounded", "3"),)
    assert len(result.failures) == 1
    assert result.failures[0].provider_id == "oversized"
    assert result.failures[0].category == "invalid-response"
    assert "exceeded requested page size" in result.failures[0].message


def test_multi_source_search_requires_room_for_every_selected_source() -> None:
    registry = SearchAdapterRegistry()
    for provider_id in ("one", "two", "three"):
        registry.register(
            _wide_capability(provider_id),
            lambda query, provider_id=provider_id: SearchPageV2(
                provider_id,
                (_item(provider_id),),
            ),
        )

    with pytest.raises(ValueError, match="cover every selected MOD"):
        registry.search(
            SearchQueryV2("music", page_size=2),
            provider_ids=("one", "two", "three"),
            limit=2,
        )


def test_multi_source_paging_only_calls_sources_with_bound_cursors() -> None:
    registry = SearchAdapterRegistry()
    received: dict[str, list[tuple[int, str]]] = {"one": [], "two": []}

    def adapter(provider_id: str):
        def search(query: SearchQueryV2) -> SearchPageV2:
            received[provider_id].append((query.page_size, query.cursor))
            return SearchPageV2(provider_id, (_item(f"{provider_id}-next"),))

        return search

    registry.register(_wide_capability("one"), adapter("one"))
    registry.register(_wide_capability("two"), adapter("two"))

    result = registry.search(
        SearchQueryV2("music", page_size=50),
        provider_ids=("one", "two"),
        limit=50,
        provider_cursors={"two": "two-next"},
    )

    assert tuple(item.video_id for item in result.items) == ("two-next",)
    assert received == {"one": [], "two": [(20, "two-next")]}


def test_registry_bounds_provider_cursor_mapping_before_materializing() -> None:
    consumed: list[int] = []

    class CursorMapping(Mapping[str, str]):
        def __getitem__(self, key: str) -> str:
            return f"cursor-{key}"

        def __iter__(self) -> Iterator[str]:
            for index in range(1000):
                consumed.append(index)
                yield f"source-{index}"

        def __len__(self) -> int:
            return 1000

    registry = SearchAdapterRegistry()

    with pytest.raises(ValueError, match="too many federated search cursors"):
        registry.search(
            SearchQueryV2("music", page_size=50),
            provider_ids=("one",),
            limit=50,
            provider_cursors=CursorMapping(),
        )

    assert consumed == list(range(17))


def test_registry_rejects_non_mapping_provider_cursors_before_dispatch() -> None:
    registry = SearchAdapterRegistry()
    search = Mock(return_value=SearchPageV2("one", ()))
    registry.register(_wide_capability("one"), search)

    with pytest.raises(ValueError, match="cursor mapping is invalid"):
        registry.search(
            SearchQueryV2("music", page_size=50),
            provider_ids=("one",),
            limit=50,
            provider_cursors=[("one", "next")],  # type: ignore[arg-type]
        )

    search.assert_not_called()


@pytest.mark.parametrize("cursor", (42, "", "x" * 501))
def test_registry_rejects_invalid_provider_cursor_before_dispatch(
    cursor: object,
) -> None:
    registry = SearchAdapterRegistry()
    search = Mock(return_value=SearchPageV2("one", ()))
    registry.register(_wide_capability("one"), search)

    with pytest.raises(ValueError, match="federated search cursor is invalid"):
        registry.search(
            SearchQueryV2("music", page_size=50),
            provider_ids=("one",),
            limit=50,
            provider_cursors={"one": cursor},  # type: ignore[dict-item]
        )

    search.assert_not_called()


def test_federated_search_round_robins_bounded_results_from_every_source() -> None:
    registry = SearchAdapterRegistry()
    received: dict[str, int] = {}

    def adapter(provider_id: str, ids: tuple[str, ...]):
        def search(query: SearchQueryV2) -> SearchPageV2:
            received[provider_id] = query.page_size
            return SearchPageV2(
                provider_id,
                tuple(_item(video_id) for video_id in ids[: query.page_size]),
            )

        return search

    registry.register(
        _capability("one"),
        adapter("one", tuple(f"one-{index}" for index in range(20))),
    )
    registry.register(
        _capability("two"),
        adapter("two", ("two-1", "two-2")),
    )
    registry.register(
        _capability("three"),
        adapter("three", ("three-1", "three-2")),
    )

    result = registry.search(SearchQueryV2("music", page_size=50), limit=6)

    assert [item.video_id for item in result.items] == [
        "one-0",
        "two-1",
        "three-1",
        "one-1",
        "two-2",
        "three-2",
    ]
    assert result.sources == ("one", "two", "three", "one", "two", "three")
    assert received == {"one": 2, "two": 2, "three": 2}
