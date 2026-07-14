"""Least-privilege permission approval policy."""

from __future__ import annotations

from contracts.capabilities import DENIED_CAPABILITIES, permits


class PermissionPolicy:
    def validate_requested(self, requested: tuple[str, ...]) -> tuple[str, ...]:
        denied = tuple(item for item in requested if item in DENIED_CAPABILITIES)
        return denied

    def allows(self, approved: tuple[str, ...], requested: str) -> bool:
        return any(permits(grant, requested) for grant in approved)

