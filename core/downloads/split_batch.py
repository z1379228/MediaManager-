"""Convert a user-confirmed split plan into one atomic download batch."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from contracts.split_plan_v1 import SplitPlanV1
from core.downloads.models import DownloadRequest


class SplitFilenameProvider(Protocol):
    def split_filename(
        self,
        *,
        source_title: str,
        index: int,
        track_title: str,
        start: float,
        duration: float,
        extension: str,
    ) -> str: ...


def build_split_requests(
    plan: SplitPlanV1,
    *,
    output_dir: Path,
    priority: int,
    filename_provider: SplitFilenameProvider,
    source_video_id: str = "",
    source_artist: str = "",
    source_language: str = "",
) -> tuple[DownloadRequest, ...]:
    if not plan.composite_likely or len(plan.segments) < 2:
        raise ValueError("split plan must be explicitly confirmed")
    requests: list[DownloadRequest] = []
    for segment in plan.segments:
        duration = segment.end - segment.start
        filename = filename_provider.split_filename(
            source_title=plan.source_title,
            index=segment.index,
            track_title=segment.title,
            start=segment.start,
            duration=duration,
            extension="m4a",
        )
        requests.append(
            DownloadRequest(
                plan.source_url,
                output_dir,
                priority=priority,
                start_time=segment.start,
                end_time=segment.end,
                source_video_id=source_video_id,
                source_title=plan.source_title,
                source_artist=source_artist,
                source_language=source_language,
                source_category="music",
                output_filename=filename,
                audio_only=True,
            )
        )
    return tuple(requests)
