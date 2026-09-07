from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryContractError, DiscoveryItemV1
from contracts.search_v2 import (
    SearchCapabilityV2,
    SearchContractV2Error,
    SearchPageV2,
)
from contracts.split_plan_v1 import SplitPlanV1
from core.discovery.service import DiscoveryService


def item(**changes):
    raw = {
        "video_id": "abc",
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "Example",
        "artist": "Artist",
        "duration": 120,
        "language": "zh-TW",
        "category": "music",
        "thumbnail_url": "https://example.com/thumb.jpg",
    }
    raw.update(changes)
    return raw


def test_discovery_contract_accepts_bounded_result() -> None:
    result = DiscoveryItemV1.from_dict(item())
    assert result.duration == 120 and result.category == "music"


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "javascript:alert(1)"},
        {"title": "x" * 301},
        {"duration": 999999},
    ],
)
def test_discovery_contract_rejects_invalid_result(changes) -> None:
    with pytest.raises(DiscoveryContractError):
        DiscoveryItemV1.from_dict(item(**changes))


@pytest.mark.parametrize(
    "url",
    (
        "https:///missing-host",
        "https://[invalid",
        "https://example.test:99999/watch",
        "https://user:secret@example.test/watch",
        "https://example.test/watch\nnext",
        "https://example.test/" + "x" * 4096,
    ),
)
def test_discovery_contract_rejects_malformed_https_url(url: str) -> None:
    with pytest.raises(DiscoveryContractError, match="identity"):
        DiscoveryItemV1.from_dict(item(url=url))


def test_direct_discovery_construction_cannot_bypass_url_validation() -> None:
    with pytest.raises(DiscoveryContractError, match="identity"):
        DiscoveryItemV1(
            "unsafe",
            "https://[invalid",
            "Unsafe result",
            "Artist",
            120,
            "zh-TW",
            "music",
            "",
        )


def test_discovery_service_routes_only_when_enabled(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "youtube-search"
    provider.display_name = "YouTube Search"
    provider.search.return_value = (DiscoveryItemV1.from_dict(item()),)
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider)
    with pytest.raises(RuntimeError, match="disabled"):
        service.search("example")
    service.set_enabled("youtube-search", True)
    assert service.search("example")[0].title == "Example"
    provider.search.assert_called_once_with(
        "example",
        limit=12,
        content_type="all",
    )
    service.search("example", content_type="music")
    provider.search.assert_called_with(
        "example",
        limit=12,
        content_type="music",
    )
    with pytest.raises(ValueError, match="content type"):
        service.search("example", content_type="unknown")
    service.close()


def test_discovery_service_uses_provider_declared_search_capability(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search",
        ("catalog",),
        ("all",),
        7,
        "none",
        False,
        False,
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")

    service.register(provider, enabled=True)

    assert service.search_capabilities() == (provider.search_capability,)
    result = service.federated_search("example", limit=20)
    assert result.items == ()
    provider.search.assert_called_once_with(
        "example", limit=7, content_type="all"
    )
    service.close()


def test_search_capability_mismatch_does_not_leave_partial_registration(
    tmp_path,
) -> None:
    invalid = Mock()
    invalid.provider_id = "catalog-search"
    invalid.display_name = "Invalid Catalog Search"
    invalid.search_capability = SearchCapabilityV2(
        "different-search", ("catalog",), ("all",), 7, "none", False, False
    )
    service = DiscoveryService(tmp_path / "discovery-state.json")

    with pytest.raises(ValueError, match="search capability provider mismatch"):
        service.register(invalid, enabled=True)

    replacement = Mock()
    replacement.provider_id = "catalog-search"
    replacement.display_name = "Catalog Search"
    replacement.search_capability = SearchCapabilityV2(
        "catalog-search", ("catalog",), ("all",), 7, "none", False, False
    )
    replacement.search.return_value = ()
    service.register(replacement, enabled=True)

    assert service.federated_search("example").items == ()
    replacement.search.assert_called_once_with(
        "example", limit=7, content_type="all"
    )
    service.close()


def test_discovery_service_routes_extended_provider_content_types(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search",
        ("catalog",),
        ("all", "playlist", "live"),
        10,
        "none",
        False,
        False,
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    service.federated_search("concert", content_type="live")
    service.federated_search("soundtrack", content_type="playlist")

    assert provider.search.call_args_list == [
        (("concert",), {"limit": 10, "content_type": "live"}),
        (("soundtrack",), {"limit": 10, "content_type": "playlist"}),
    ]
    service.close()


def test_federated_search_rejects_explicitly_selected_disabled_source(
    tmp_path,
) -> None:
    provider = Mock()
    provider.provider_id = "bilibili-search"
    provider.display_name = "Bilibili Search"
    provider.search_capability = SearchCapabilityV2(
        "bilibili-search",
        ("bilibili",),
        ("all",),
        7,
        "none",
        False,
        False,
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=False)

    with pytest.raises(RuntimeError, match="bilibili-search"):
        service.federated_search(
            "example",
            provider_ids=("bilibili-search",),
        )

    provider.search.assert_not_called()
    assert service.federated_search("example").items == ()
    service.close()


def test_federated_search_rejects_missing_source_without_fallback(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "youtube-search"
    provider.display_name = "YouTube Search"
    provider.search_capability = SearchCapabilityV2(
        "youtube-search", ("youtube",), ("all",), 7, "none", False, False
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    with pytest.raises(RuntimeError, match="unavailable: missing-search"):
        service.federated_search(
            "example",
            provider_ids=("missing-search",),
        )

    provider.search.assert_not_called()
    service.close()


def test_federated_search_rejects_string_provider_selection(tmp_path) -> None:
    service = DiscoveryService(tmp_path / "discovery-state.json")

    with pytest.raises(ValueError, match="search MOD selection is invalid"):
        service.federated_search(
            "example",
            provider_ids="one",  # type: ignore[arg-type]
        )

    service.close()


def test_federated_search_normalizes_non_iterable_provider_error(tmp_path) -> None:
    service = DiscoveryService(tmp_path / "discovery-state.json")

    with pytest.raises(ValueError, match="search MOD selection is invalid"):
        service.federated_search(
            "example",
            provider_ids=42,  # type: ignore[arg-type]
        )

    service.close()


def test_federated_search_bounds_provider_iterable_before_lookup(tmp_path) -> None:
    consumed: list[int] = []

    def provider_ids() -> Iterator[str]:
        for index in range(1000):
            consumed.append(index)
            yield f"source-{index}"

    service = DiscoveryService(tmp_path / "discovery-state.json")

    with pytest.raises(ValueError, match="too many search MODs selected"):
        service.federated_search(
            "example",
            provider_ids=provider_ids(),  # type: ignore[arg-type]
        )

    assert consumed == list(range(17))
    service.close()


@pytest.mark.parametrize("limit", (True, "12", 1.5))
def test_federated_search_rejects_non_integer_result_limit(
    tmp_path,
    limit: object,
) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search", ("catalog",), ("all",), 7, "none", False, False
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    with pytest.raises(ValueError, match="search result limit is invalid"):
        service.federated_search(
            "example",
            provider_ids=(provider.provider_id,),
            limit=limit,  # type: ignore[arg-type]
        )

    provider.search.assert_not_called()
    service.close()


@pytest.mark.parametrize(
    ("query", "content_type"),
    (
        ("", "all"),
        (42, "all"),
        ("music", 42),
    ),
)
def test_federated_search_validates_query_without_enabled_source(
    tmp_path,
    query: object,
    content_type: object,
) -> None:
    service = DiscoveryService(tmp_path / "discovery-state.json")

    with pytest.raises(SearchContractV2Error):
        service.federated_search(
            query,  # type: ignore[arg-type]
            content_type=content_type,  # type: ignore[arg-type]
        )

    service.close()


@pytest.mark.parametrize("cursor", (None, False, 0, []))
def test_federated_search_rejects_falsey_non_string_cursor_before_dispatch(
    tmp_path,
    cursor: object,
) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search", ("catalog",), ("all",), 7, "cursor", False, False
    )
    provider.search.return_value = ()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    with pytest.raises(ValueError, match="search cursor invalid"):
        service.federated_search(
            "example",
            provider_ids=(provider.provider_id,),
            cursor=cursor,  # type: ignore[arg-type]
        )

    provider.search.assert_not_called()
    service.close()


def test_search_source_health_tracks_failure_and_recovery(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search", ("catalog",), ("all",), 7, "none", False, False
    )
    provider.search.side_effect = RuntimeError("offline")
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    failed = service.federated_search("example")

    assert failed.failures[0].message == "offline"
    status = service.search_source_statuses()[0]
    assert status.health == "error"
    assert status.message == "offline"
    assert status.consecutive_failures == 1
    assert status.successful_searches == 0

    provider.search.side_effect = None
    provider.search.return_value = ()
    service.federated_search("example")
    status = service.search_source_statuses()[0]
    assert status.health == "ready"
    assert status.consecutive_failures == 0
    assert status.successful_searches == 1

    service.set_enabled("catalog-search", False)
    assert service.search_source_statuses()[0].health == "disabled"
    service.close()


def test_search_failure_redacts_cookie_before_health_and_ui_boundary(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "catalog-search"
    provider.display_name = "Catalog Search"
    provider.search_capability = SearchCapabilityV2(
        "catalog-search", ("catalog",), ("all",), 7, "none", False, False
    )
    provider.search.side_effect = RuntimeError(
        "Cookie: session=discovery-cookie-canary"
    )
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    failed = service.federated_search("example")

    assert failed.failures[0].message == "Cookie: [REDACTED]"
    assert "discovery-cookie-canary" not in service.search_source_statuses()[0].message
    service.close()


def test_discovery_service_binds_opaque_cursor_to_search(tmp_path) -> None:
    class PagedProvider:
        provider_id = "catalog-search"
        display_name = "Catalog Search"
        search_capability = SearchCapabilityV2(
            "catalog-search", ("catalog",), ("all", "music"), 7, "cursor", False, False
        )

        def __init__(self) -> None:
            self.received: list[str] = []

        def search_page(self, query):
            self.received.append(query.cursor)
            if query.cursor:
                return SearchPageV2(
                    self.provider_id,
                    (DiscoveryItemV1.from_dict(item(video_id="page-two")),),
                )
            return SearchPageV2(
                self.provider_id,
                (DiscoveryItemV1.from_dict(item(video_id="page-one")),),
                "provider-secret-cursor",
            )

        def close(self) -> None:
            pass

    provider = PagedProvider()
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(provider, enabled=True)

    first = service.federated_search(
        "  synth   wave ", provider_ids=(provider.provider_id,), content_type="music"
    )
    token = first.next_cursors[0][1]

    assert token.startswith("sc1.")
    assert "provider-secret-cursor" not in token
    second = service.federated_search(
        "synth wave",
        provider_ids=(provider.provider_id,),
        content_type="music",
        cursor=token,
    )
    assert second.items[0].video_id == "page-two"
    assert provider.received == ["", "provider-secret-cursor"]

    with pytest.raises(ValueError, match="does not match"):
        service.federated_search(
            "different query",
            provider_ids=(provider.provider_id,),
            content_type="music",
            cursor=token,
        )
    with pytest.raises(ValueError, match="invalid"):
        service.federated_search(
            "synth wave",
            provider_ids=(provider.provider_id,),
            content_type="music",
            cursor=token[:-1] + ("A" if token[-1] != "A" else "B"),
        )
    service.close()


def test_discovery_service_paginates_multiple_sources_with_one_bound_cursor(
    tmp_path,
) -> None:
    class PagedProvider:
        display_name = "Paged Search"

        def __init__(self, provider_id: str) -> None:
            self.provider_id = provider_id
            self.search_capability = SearchCapabilityV2(
                provider_id,
                (provider_id,),
                ("all", "music"),
                7,
                "cursor",
                False,
                False,
            )
            self.received: list[str] = []

        def search_page(self, query):
            self.received.append(query.cursor)
            suffix = "two" if query.cursor else "one"
            return SearchPageV2(
                self.provider_id,
                (
                    DiscoveryItemV1.from_dict(
                        item(
                            video_id=f"{self.provider_id}-{suffix}",
                            url=(
                                f"https://{self.provider_id}.example/"
                                f"watch/{suffix}"
                            ),
                        )
                    ),
                ),
                "" if query.cursor else f"{self.provider_id}-secret-cursor",
            )

        def close(self) -> None:
            pass

    first_provider = PagedProvider("first-search")
    second_provider = PagedProvider("second-search")
    provider_ids = (first_provider.provider_id, second_provider.provider_id)
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(first_provider, enabled=True)
    service.register(second_provider, enabled=True)

    first = service.federated_search(
        "  synth   wave ",
        provider_ids=provider_ids,
        content_type="music",
    )

    assert tuple(item.video_id for item in first.items) == (
        "first-search-one",
        "second-search-one",
    )
    assert len(first.next_cursors) == 1
    cursor_provider_id, token = first.next_cursors[0]
    assert cursor_provider_id == "__federated__"
    assert token.startswith("fsc1.")
    assert "secret-cursor" not in token

    second = service.federated_search(
        "synth wave",
        provider_ids=provider_ids,
        content_type="music",
        cursor=token,
    )

    assert tuple(item.video_id for item in second.items) == (
        "first-search-two",
        "second-search-two",
    )
    assert second.next_cursors == ()
    assert first_provider.received == ["", "first-search-secret-cursor"]
    assert second_provider.received == ["", "second-search-secret-cursor"]

    with pytest.raises(ValueError, match="does not match"):
        service.federated_search(
            "different query",
            provider_ids=provider_ids,
            content_type="music",
            cursor=token,
        )
    with pytest.raises(ValueError, match="does not match"):
        service.federated_search(
            "synth wave",
            provider_ids=tuple(reversed(provider_ids)),
            content_type="music",
            cursor=token,
        )
    with pytest.raises(ValueError, match="invalid"):
        service.federated_search(
            "synth wave",
            provider_ids=provider_ids,
            content_type="music",
            cursor=token[:-1] + ("A" if token[-1] != "A" else "B"),
        )
    service.close()


def test_discovery_service_preserves_failed_federated_cursor_for_retry(
    tmp_path,
) -> None:
    class RetriableProvider:
        provider_id = "retriable-search"
        display_name = "Retriable Search"
        search_capability = SearchCapabilityV2(
            provider_id,
            ("retriable",),
            ("all",),
            7,
            "cursor",
            False,
            False,
        )

        def __init__(self) -> None:
            self.received: list[str] = []

        def search_page(self, query):
            self.received.append(query.cursor)
            if not query.cursor:
                return SearchPageV2(
                    self.provider_id,
                    (DiscoveryItemV1.from_dict(item(video_id="first")),),
                    "retry-me",
                )
            if self.received.count("retry-me") == 1:
                raise ConnectionError("temporary outage")
            return SearchPageV2(
                self.provider_id,
                (DiscoveryItemV1.from_dict(item(video_id="recovered")),),
            )

        def close(self) -> None:
            pass

    class ExhaustedProvider:
        provider_id = "exhausted-search"
        display_name = "Exhausted Search"
        search_capability = SearchCapabilityV2(
            provider_id,
            ("exhausted",),
            ("all",),
            7,
            "cursor",
            False,
            False,
        )

        def __init__(self) -> None:
            self.received: list[str] = []

        def search_page(self, query):
            self.received.append(query.cursor)
            return SearchPageV2(
                self.provider_id,
                (DiscoveryItemV1.from_dict(item(video_id="exhausted")),),
            )

        def close(self) -> None:
            pass

    retriable = RetriableProvider()
    exhausted = ExhaustedProvider()
    provider_ids = (retriable.provider_id, exhausted.provider_id)
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register(retriable, enabled=True)
    service.register(exhausted, enabled=True)

    first = service.federated_search("music", provider_ids=provider_ids)
    failed = service.federated_search(
        "music",
        provider_ids=provider_ids,
        cursor=first.next_cursors[0][1],
    )

    assert failed.items == ()
    assert tuple(failure.provider_id for failure in failed.failures) == (
        retriable.provider_id,
    )
    assert len(failed.next_cursors) == 1
    assert exhausted.received == [""]

    recovered = service.federated_search(
        "music",
        provider_ids=provider_ids,
        cursor=failed.next_cursors[0][1],
    )

    assert tuple(item.video_id for item in recovered.items) == ("recovered",)
    assert recovered.next_cursors == ()
    assert retriable.received == ["", "retry-me", "retry-me"]
    assert exhausted.received == [""]
    service.close()


def test_discovery_service_routes_split_plan_only_when_enabled(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "youtube-auto-split"
    provider.display_name = "YouTube Auto Split"
    provider.split_plan.return_value = SplitPlanV1.from_dict(
        {
            "source_url": "https://youtu.be/example",
            "source_title": "Mix",
            "duration": 120,
            "composite_likely": False,
            "segments": [],
            "warnings": ["No evidence"],
        }
    )
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register_split(provider)
    arguments = {
        "source_url": "https://youtu.be/example",
        "source_title": "Mix",
        "duration": 120,
        "chapters": [],
        "description": "",
    }
    with pytest.raises(RuntimeError, match="disabled"):
        service.split_plan(**arguments)
    service.set_enabled("youtube-auto-split", True)
    assert not service.split_plan(**arguments).composite_likely
    provider.split_plan.assert_called_once_with(**arguments)
    service.close()


def test_discovery_service_routes_video_preview_only_when_enabled(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "youtube-player"
    provider.display_name = "YouTube Player"
    service = DiscoveryService(tmp_path / "discovery-state.json")
    service.register_video_preview(provider)
    with pytest.raises(RuntimeError, match="disabled"):
        service.video_preview_provider()
    service.set_enabled("youtube-player", True)
    assert service.video_preview_provider() is provider
    service.close()
