from pathlib import Path

import pytest

from contracts.split_plan_v1 import SplitPlanV1
from core.downloads.split_batch import build_split_requests


class NamingProvider:
    def split_filename(
        self,
        *,
        source_title: str,
        index: int,
        track_title: str,
        start: float,
        duration: float,
        extension: str,
    ) -> str:
        return f"{source_title}-{index:02d}-{track_title}-{start:g}-{duration:g}.{extension}"


def confirmed_plan() -> SplitPlanV1:
    evidence = {
        "source": "manual",
        "confidence": 1.0,
        "detail": "user-confirmed boundary",
    }
    return SplitPlanV1.from_dict(
        {
            "source_url": "https://youtu.be/example",
            "source_title": "Work BGM",
            "duration": 300,
            "composite_likely": True,
            "segments": [
                {
                    "index": 1,
                    "start": 0,
                    "end": 120,
                    "title": "First",
                    "evidence": [evidence],
                },
                {
                    "index": 2,
                    "start": 120,
                    "end": 300,
                    "title": "Second",
                    "evidence": [evidence],
                },
            ],
            "warnings": [],
        }
    )


def test_confirmed_plan_becomes_audio_only_named_segment_batch() -> None:
    requests = build_split_requests(
        confirmed_plan(),
        output_dir=Path("output"),
        priority=5,
        filename_provider=NamingProvider(),
        source_video_id="example",
        source_artist="Artist",
    )
    assert len(requests) == 2
    assert requests[0].start_time == 0
    assert requests[0].end_time == 120
    assert requests[0].audio_only
    assert requests[0].output_filename == "Work BGM-01-First-0-120.m4a"
    assert requests[1].output_filename == "Work BGM-02-Second-120-180.m4a"
    assert requests[1].priority == 5
    assert requests[1].source_category == "music"


def test_unconfirmed_plan_cannot_expand() -> None:
    raw = confirmed_plan()
    unconfirmed = SplitPlanV1(
        raw.source_url,
        raw.source_title,
        raw.duration,
        False,
        raw.segments,
        raw.warnings,
    )
    with pytest.raises(ValueError, match="explicitly confirmed"):
        build_split_requests(
            unconfirmed,
            output_dir=Path("output"),
            priority=0,
            filename_provider=NamingProvider(),
        )
