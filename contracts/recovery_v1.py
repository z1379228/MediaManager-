"""Versioned contract for explicit unavailable-video recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.discovery_v1 import DiscoveryItemV1


class RecoveryContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryPlanV1:
    primary_query: str
    fallback_queries: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RecoveryPlanV1":
        if not isinstance(raw, dict) or set(raw) != {
            "primary_query",
            "fallback_queries",
        }:
            raise RecoveryContractError("recovery plan fields invalid")
        primary = raw["primary_query"]
        fallback = raw["fallback_queries"]
        if not isinstance(primary, str) or not 1 <= len(primary) <= 200:
            raise RecoveryContractError("recovery primary query invalid")
        if (
            not isinstance(fallback, list)
            or len(fallback) > 4
            or len(fallback) != len(set(fallback))
            or not all(
                isinstance(query, str) and 1 <= len(query) <= 200
                for query in fallback
            )
        ):
            raise RecoveryContractError("recovery fallback queries invalid")
        return cls(primary, tuple(fallback))


@dataclass(frozen=True, slots=True)
class RecoveryCandidateV1:
    item: DiscoveryItemV1
    score: int
    reasons: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RecoveryCandidateV1":
        if not isinstance(raw, dict) or set(raw) != {"item", "score", "reasons"}:
            raise RecoveryContractError("recovery candidate fields invalid")
        score, reasons = raw["score"], raw["reasons"]
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise RecoveryContractError("recovery candidate score invalid")
        if (
            not isinstance(reasons, list)
            or not 1 <= len(reasons) <= 5
            or not all(
                isinstance(reason, str) and 1 <= len(reason) <= 100
                for reason in reasons
            )
        ):
            raise RecoveryContractError("recovery candidate reasons invalid")
        return cls(DiscoveryItemV1.from_dict(raw["item"]), score, tuple(reasons))
