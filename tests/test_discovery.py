from __future__ import annotations

from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryContractError, DiscoveryItemV1
from contracts.search_v2 import SearchCapabilityV2, SearchPageV2
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
