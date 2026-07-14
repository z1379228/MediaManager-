"""Startup state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StartupPhase(StrEnum):
    CREATED = "created"
    PATHS_READY = "paths_ready"
    SETTINGS_READY = "settings_ready"
    LOGGING_READY = "logging_ready"
    SECURITY_CHECKED = "security_checked"
    READY = "ready"
    STOPPED = "stopped"


@dataclass(slots=True)
class StartupState:
    phase: StartupPhase = StartupPhase.CREATED
    messages: list[str] = field(default_factory=list)

    def advance(self, phase: StartupPhase, message: str) -> None:
        self.phase = phase
        self.messages.append(message)

