"""Application security operating mode."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SecurityMode(StrEnum):
    NORMAL = "NORMAL"
    SAFE_MODE = "SAFE_MODE"
    BLOCKED = "BLOCKED"


@dataclass(slots=True)
class SafeMode:
    mode: SecurityMode = SecurityMode.NORMAL
    reason: str | None = None

    def enter_safe_mode(self, reason: str) -> None:
        if self.mode is not SecurityMode.BLOCKED:
            self.mode, self.reason = SecurityMode.SAFE_MODE, reason

    def block(self, reason: str) -> None:
        self.mode, self.reason = SecurityMode.BLOCKED, reason

