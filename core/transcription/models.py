"""Models for local speech-to-text jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import Event


class TranscriptionState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    source: Path
    model_id: str
    output_dir: Path
    formats: tuple[str, ...] = ("txt", "srt", "vtt")
    language: str = "auto"


@dataclass(frozen=True, slots=True)
class TranscriptionPlan:
    request: TranscriptionRequest
    outputs: tuple[Path, ...]
    model_bytes: int
    estimated_ram_bytes: int


@dataclass(slots=True)
class TranscriptionTask:
    task_id: str
    request: TranscriptionRequest
    state: TranscriptionState = TranscriptionState.QUEUED
    error: str = ""
    outputs: tuple[str, ...] = ()
    cancel_event: Event = field(default_factory=Event, repr=False)
