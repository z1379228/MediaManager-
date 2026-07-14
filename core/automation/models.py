"""Models for disabled-by-default automation rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AutomationRule:
    rule_id: str
    name: str
    kind: str
    source: str
    preset: dict[str, Any]
    enabled: bool
    interval_seconds: int
    window_start: int
    window_end: int
    rate_limit: int
    next_run: float | None
    last_run: float | None
    last_error: str


@dataclass(frozen=True, slots=True)
class AutomationCandidate:
    candidate_key: str
    rule_id: str
    source: str
    discovered_at: float
    state: str
    attempts: int
    dispatch_token: str
    error: str

    @property
    def path(self) -> Path:
        return Path(self.source)
