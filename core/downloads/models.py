"""Transport-neutral download task models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from pathlib import Path
from threading import Event
from typing import Any

from contracts.media_options_v1 import validate_media_options_v1


_UNSAFE_FILENAME = frozenset('<>:"/\\|?*')


class DownloadState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    url: str
    output_dir: Path
    priority: int = 0
    start_time: float | None = None
    end_time: float | None = None
    source_video_id: str = ""
    source_title: str = ""
    source_artist: str = ""
    source_language: str = ""
    source_category: str = ""
    output_filename: str = ""
    audio_only: bool = False
    format_preset: str = "best"
    subtitle_mode: str = "none"
    subtitle_languages: tuple[str, ...] = ()
    timed_comment_mode: str = "none"
    container_preset: str = "auto"
    provider_options: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.url.startswith(("https://", "http://")):
            raise ValueError("download URL must use HTTP or HTTPS")
        if not -10 <= self.priority <= 10:
            raise ValueError("priority must be between -10 and 10")
        for field_name, value in (
            ("segment start", self.start_time),
            ("segment end", self.end_time),
        ):
            if value is not None and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(f"{field_name} must be finite")
        if self.start_time is not None and self.start_time < 0:
            raise ValueError("segment start must be non-negative")
        if self.end_time is not None and self.end_time <= (self.start_time or 0):
            raise ValueError("segment end must be greater than start")
        source_limits = {
            "source_video_id": 100,
            "source_title": 300,
            "source_artist": 200,
            "source_language": 32,
            "source_category": 100,
        }
        for field_name, limit in source_limits.items():
            value = getattr(self, field_name)
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f"{field_name} metadata is invalid")
        if not isinstance(self.audio_only, bool):
            raise ValueError("audio_only must be a boolean")
        validate_media_options_v1(
            self.format_preset,
            self.subtitle_mode,
            self.subtitle_languages,
            self.timed_comment_mode,
            self.container_preset,
        )
        if (
            not isinstance(self.provider_options, tuple)
            or len(self.provider_options) > 16
        ):
            raise ValueError("provider options are invalid")
        seen_provider_options: set[str] = set()
        for item in self.provider_options:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not all(isinstance(value, str) for value in item)
            ):
                raise ValueError("provider options are invalid")
            key, value = item
            if (
                not key
                or len(key) > 64
                or len(value) > 256
                or key in seen_provider_options
                or any(ord(character) < 32 for character in key + value)
            ):
                raise ValueError("provider options are invalid")
            seen_provider_options.add(key)
        filename = self.output_filename
        if (
            not isinstance(filename, str)
            or len(filename) > 180
            or (filename and Path(filename).name != filename)
            or (filename and filename[-1] in " .")
            or any(character in _UNSAFE_FILENAME or ord(character) < 32 for character in filename)
        ):
            raise ValueError("output filename is invalid")


@dataclass(slots=True)
class DownloadTask:
    task_id: str
    request: DownloadRequest
    state: DownloadState = DownloadState.QUEUED
    title: str = ""
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    output_path: str = ""
    error: str = ""
    automatic_retries: int = 0
    next_retry_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    cancel_event: Event = field(default_factory=Event, repr=False)
    pause_requested: Event = field(default_factory=Event, repr=False)
