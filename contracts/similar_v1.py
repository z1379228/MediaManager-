"""Versioned contract for user-triggered similar media selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.discovery_v1 import DiscoveryItemV1


class SimilarContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SimilarPlanV1:
    queries: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SimilarPlanV1":
        if not isinstance(raw, dict) or set(raw) != {"queries"}:
            raise SimilarContractError("similar plan fields invalid")
        queries = raw["queries"]
        if (
            not isinstance(queries, list)
            or not 1 <= len(queries) <= 3
            or len(queries) != len(set(queries))
            or not all(
                isinstance(query, str) and 1 <= len(query) <= 200
                for query in queries
            )
        ):
            raise SimilarContractError("similar queries invalid")
        return cls(tuple(queries))


@dataclass(frozen=True, slots=True)
class SimilarSelectionV1:
    item: DiscoveryItemV1
    score: int
    reasons: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SimilarSelectionV1":
        if not isinstance(raw, dict) or set(raw) != {"item", "score", "reasons"}:
            raise SimilarContractError("similar selection fields invalid")
        score, reasons = raw["score"], raw["reasons"]
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise SimilarContractError("similar selection score invalid")
        if (
            not isinstance(reasons, list)
            or not 1 <= len(reasons) <= 6
            or not all(
                isinstance(reason, str) and 1 <= len(reason) <= 100
                for reason in reasons
            )
        ):
            raise SimilarContractError("similar selection reasons invalid")
        return cls(DiscoveryItemV1.from_dict(raw["item"]), score, tuple(reasons))
