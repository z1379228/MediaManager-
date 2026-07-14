from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.recovery_v1 import (
    RecoveryCandidateV1,
    RecoveryContractError,
    RecoveryPlanV1,
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


def test_recovery_contract_validates_plan_and_candidate() -> None:
    plan = RecoveryPlanV1.from_dict(
        {
            "primary_query": "Example Song",
            "fallback_queries": ["Artist Example Song"],
        }
    )
    assert plan.fallback_queries == ("Artist Example Song",)
    candidate = RecoveryCandidateV1.from_dict(
        {
            "item": {
                "video_id": "new",
                "url": "https://www.youtube.com/watch?v=new",
                "title": "Example Song Official",
                "artist": "Artist",
                "duration": 180,
                "language": "zh-TW",
                "category": "music",
                "thumbnail_url": "",
            },
            "score": 85,
            "reasons": ["title", "artist"],
        }
    )
    assert candidate.score == 85


def test_recovery_contract_rejects_duplicate_fallbacks() -> None:
    with pytest.raises(RecoveryContractError):
        RecoveryPlanV1.from_dict(
            {
                "primary_query": "Example",
                "fallback_queries": ["Artist", "Artist"],
            }
        )


def test_recovery_mod_plans_and_ranks_without_original_video() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "youtube-recovery"
    provider = SubprocessDownloadProvider(
        root,
        application_root=Path(__file__).parents[1],
    )
    original = item()
    plan = provider.recovery_plan(original)
    assert plan.primary_query == "Example Song"
    ranked = provider.rank_recovery(
        original,
        (
            original,
            item("new", "Example Song Official", "Artist"),
            item("other", "Unrelated Clip", "Other"),
        ),
    )
    assert [candidate.item.video_id for candidate in ranked] == ["new"]
    assert "title" in ranked[0].reasons
    provider.close()


def test_discovery_service_uses_fallback_only_after_empty_primary(
    tmp_path: Path,
) -> None:
    original = item()
    replacement = item("new", "Example Song Official", "Artist")
    candidate = RecoveryCandidateV1(replacement, 80, ("title", "artist"))

    search = Mock()
    search.provider_id = "youtube-search"
    search.display_name = "YouTube Search"
    search.search.side_effect = [(), (replacement,)]

    recovery = Mock()
    recovery.provider_id = "youtube-recovery"
    recovery.display_name = "YouTube Recovery"
    recovery.recovery_plan.return_value = RecoveryPlanV1(
        "Example Song", ("Artist Example Song",)
    )
    recovery.rank_recovery.side_effect = [(), (candidate,)]

    service = DiscoveryService(tmp_path / "state.json")
    service.register(search, enabled=True)
    service.register_recovery(recovery, enabled=True)
    assert service.replacement_candidates(original) == (candidate,)
    assert [call.args[0] for call in search.search.call_args_list] == [
        "Example Song",
        "Artist Example Song",
    ]
    service.close()
