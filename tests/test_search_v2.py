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
