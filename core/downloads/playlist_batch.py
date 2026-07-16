"""Convert selected playlist entries into an atomic download batch."""

from __future__ import annotations

from pathlib import Path

from contracts.playlist_v1 import PlaylistEntryV1
from core.downloads.models import DownloadRequest


def build_playlist_requests(
    entries: tuple[PlaylistEntryV1, ...],
    *,
    output_dir: Path,
    priority: int,
    format_preset: str,
    subtitle_mode: str,
    subtitle_languages: tuple[str, ...],
    timed_comment_mode: str = "none",
    container_preset: str = "auto",
    provider_options: tuple[tuple[str, str], ...] = (),
) -> tuple[DownloadRequest, ...]:
    if not entries:
        raise ValueError("at least one playlist entry must be selected")
    if len(entries) > 500:
        raise ValueError("playlist selection is too large")
    if any(not entry.available for entry in entries):
        raise ValueError("unavailable playlist entries cannot be downloaded")
    if len({entry.entry_id for entry in entries}) != len(entries):
        raise ValueError("playlist selection contains duplicate entries")
    return tuple(
        DownloadRequest(
            entry.url,
            output_dir,
            priority=priority,
            source_video_id=entry.entry_id,
            source_title=entry.title,
            source_artist=entry.artist,
            source_category="playlist",
            format_preset=format_preset,
            subtitle_mode=subtitle_mode,
            subtitle_languages=subtitle_languages,
            timed_comment_mode=timed_comment_mode,
            container_preset=container_preset,
            provider_options=provider_options,
        )
        for entry in entries
    )
