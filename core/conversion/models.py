"""Models for bounded local FFmpeg work."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import Event


class ConversionState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ConversionCapabilities:
    """Observed capabilities of the selected local FFmpeg executable."""

    ffmpeg_version: str = ""
    build_configuration: str = ""
    formats: frozenset[str] = frozenset()
    encoders: frozenset[str] = frozenset()
    filters: frozenset[str] = frozenset()
    hwaccels: frozenset[str] = frozenset()
    errors: tuple[str, ...] = ()

    @property
    def supports_h264_nvenc(self) -> bool:
        return "h264_nvenc" in self.encoders

    @property
    def supports_hevc_nvenc(self) -> bool:
        return "hevc_nvenc" in self.encoders


@dataclass(frozen=True, slots=True)
class MediaStreamInfo:
    index: int
    codec_type: str
    codec_name: str
    title: str = ""
    language: str = ""
    channels: int | None = None
    width: int | None = None
    height: int | None = None
    default: bool = False
    forced: bool = False


@dataclass(frozen=True, slots=True)
class MediaInspection:
    source: Path
    format_name: str
    duration_seconds: float | None
    streams: tuple[MediaStreamInfo, ...]


@dataclass(frozen=True, slots=True)
class MediaHealthReport:
    """Bounded structural and prefix-decode result for one local media file."""

    inspection: MediaInspection
    checked_seconds: float
    healthy: bool
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    sources: tuple[Path, ...]
    output: Path
    preset: str
    start_time: float | None = None
    end_time: float | None = None
    hardware_acceleration: bool = False
    remove_ranges: tuple[tuple[float, float], ...] = ()
    watermark: Path | None = None
    stream_index: int | None = None
    target_size_bytes: int | None = None
    source_duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ConversionPlan:
    request: ConversionRequest
    strategy: str
    estimated_bytes: int
    command: tuple[str, ...]
    fallback_command: tuple[str, ...] | None = None
    preparatory_commands: tuple[tuple[str, ...], ...] = ()


@dataclass(slots=True)
class ConversionTask:
    task_id: str
    request: ConversionRequest
    state: ConversionState = ConversionState.QUEUED
    error: str = ""
    output_path: str = ""
    cancel_event: Event = field(default_factory=Event, repr=False)
