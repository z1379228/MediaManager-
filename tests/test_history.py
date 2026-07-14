from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import (
    HistoryContractError,
    HistoryEventV1,
    HistoryPreferencesV1,
)
from core.discovery.service import DiscoveryService
from core.downloads.subprocess_provider import SubprocessDownloadProvider
from trusted_ui.search_panel import (
    history_preference_summary,
    recent_history_queries,
)


def discovery_item() -> DiscoveryItemV1:
    return DiscoveryItemV1.from_dict(
        {
            "video_id": "abc",
            "url": "https://www.youtube.com/watch?v=abc",
            "title": "Example",
            "artist": "Artist",
            "duration": 120,
            "language": "zh-TW",
            "category": "music",
            "thumbnail_url": "",
        }
    )


def test_history_contracts_validate_events_and_preferences() -> None:
    event = HistoryEventV1.from_dict(
        {
            "event_type": "search",
            "query": "example",
            "timestamp": "2026-07-13T00:00:00+00:00",
            "item": None,
        }
    )
    assert event.query == "example"
    preferences = HistoryPreferencesV1.from_dict(
        {
            "total_searches": 1,
            "total_selections": 1,
            "content_types": {"music": 1},
            "languages": {"zh-TW": 1},
            "artists": {"Artist": 1},
            "categories": {"music": 1},
        }
    )
    assert preferences.content_types == {"music": 1}


def test_history_contract_rejects_search_with_item() -> None:
    with pytest.raises(HistoryContractError):
        HistoryEventV1.from_dict(
            {
                "event_type": "search",
                "query": "example",
                "timestamp": "2026-07-13T00:00:00+00:00",
                "item": {
                    "video_id": "abc",
                    "url": "https://www.youtube.com/watch?v=abc",
                    "title": "Example",
                    "artist": "Artist",
                    "duration": 120,
                    "language": "zh-TW",
                    "category": "music",
                    "thumbnail_url": "",
                },
            }
        )


def test_search_history_ui_helpers_deduplicate_and_summarize() -> None:
    events = (
        HistoryEventV1(
            "search",
            "中文 音樂",
            "2026-07-14T00:00:03+00:00",
            None,
        ),
        HistoryEventV1(
            "selection",
            "中文   音樂",
            "2026-07-14T00:00:02+00:00",
            discovery_item(),
        ),
        HistoryEventV1(
            "search",
            "作業用 BGM",
            "2026-07-14T00:00:01+00:00",
            None,
        ),
    )
    assert recent_history_queries(events) == ("中文 音樂", "作業用 BGM")

    preferences = HistoryPreferencesV1(
        total_searches=3,
        total_selections=2,
        content_types={"music": 2, "video": 1},
        languages={"zh-TW": 2},
        artists={},
        categories={"music": 2},
    )
    assert history_preference_summary(preferences) == (
        "3 次搜尋 · 2 次選取 · 常選 音樂 · 語言 zh-TW"
    )


def test_history_mod_records_recent_events_and_preferences(tmp_path: Path) -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-history"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
        history_state_path=tmp_path / "history.json",
    )
    provider.record_history("search", "example")
    provider.record_history("selection", "example", discovery_item())
    recent = provider.recent_history()
    assert [event.event_type for event in recent] == ["selection", "search"]
    preferences = provider.history_preferences()
    assert preferences.total_searches == 1
    assert preferences.total_selections == 1
    assert preferences.languages == {"zh-TW": 1}
    provider.close()


def test_discovery_service_routes_history_only_when_enabled(tmp_path: Path) -> None:
    provider = Mock()
    provider.provider_id = "youtube-history"
    provider.display_name = "YouTube History"
    provider.recent_history.return_value = ()
    service = DiscoveryService(tmp_path / "state.json")
    service.register_history(provider)
    with pytest.raises(RuntimeError, match="disabled"):
        service.record_history("search", "example")
    service.set_enabled("youtube-history", True)
    service.record_history("search", "example")
    provider.record_history.assert_called_once_with("search", "example", None)
    assert service.recent_history() == ()
    service.close()
