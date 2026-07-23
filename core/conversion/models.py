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


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    sources: tuple[Path, ...]
    output: Path
    preset: str
    start_time: float | None = None
    end_time: float | None = None
    hardware_acceleration: bool = False
    remove_ranges: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True, slots=True)
class ConversionPlan:
    request: ConversionRequest
    strategy: str
    estimated_bytes: int
    command: tuple[str, ...]
    fallback_command: tuple[str, ...] | None = None


@dataclass(slots=True)
class ConversionTask:
    task_id: str
    request: ConversionRequest
    state: ConversionState = ConversionState.QUEUED
    error: str = ""
    output_path: str = ""
    cancel_event: Event = field(default_factory=Event, repr=False)
