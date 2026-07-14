from __future__ import annotations

from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryContractError, DiscoveryItemV1
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
        {"extra": "field"},
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
