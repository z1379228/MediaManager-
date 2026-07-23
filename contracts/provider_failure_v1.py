"""Stable provider failure taxonomy across download MOD process boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from contracts._additive_result import (
    AdditiveResultError,
    validate_additive_result,
)


_PROVIDER_FAILURE_FIELDS = frozenset({"code", "message", "retryable"})


class ProviderFailureCode(StrEnum):
    UNSUPPORTED = "UNSUPPORTED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    REGION_RESTRICTED = "REGION_RESTRICTED"
    CONTENT_REMOVED = "CONTENT_REMOVED"
    RATE_LIMITED = "RATE_LIMITED"
    TEMPORARY = "TEMPORARY"
    PROVIDER_ERROR = "PROVIDER_ERROR"


@dataclass(frozen=True, slots=True)
class ProviderFailureV1:
    code: ProviderFailureCode
    message: str
    retryable: bool

    def __post_init__(self) -> None:
        if not 1 <= len(self.message) <= 1000:
            raise ValueError("provider failure message is invalid")
        if not isinstance(self.retryable, bool):
            raise ValueError("provider retryable state is invalid")

    @classmethod
    def from_dict(cls, raw: Any) -> ProviderFailureV1:
        try:
            validate_additive_result(
                raw,
                required_fields=_PROVIDER_FAILURE_FIELDS,
            )
        except AdditiveResultError as exc:
            raise ValueError("provider failure payload is invalid") from exc
        if (
            not isinstance(raw["message"], str)
            or not isinstance(raw["retryable"], bool)
        ):
            raise ValueError("provider failure payload is invalid")
        return cls(
            ProviderFailureCode(raw["code"]),
            raw["message"],
            raw["retryable"],
        )
