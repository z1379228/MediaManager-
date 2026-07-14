"""Versioned contract for user-confirmed composite-media split drafts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class SplitPlanContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SplitEvidenceV1:
    source: str
    confidence: float
    detail: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SplitEvidenceV1":
        if not isinstance(raw, dict) or set(raw) != {
            "source",
            "confidence",
            "detail",
        }:
            raise SplitPlanContractError("split evidence fields invalid")
        if raw["source"] not in {
            "chapters",
            "description",
            "silence",
            "change_point",
            "manual",
        }:
            raise SplitPlanContractError("split evidence source invalid")
        confidence = raw["confidence"]
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise SplitPlanContractError("split evidence confidence invalid")
        detail = raw["detail"]
        if not isinstance(detail, str) or len(detail) > 300:
            raise SplitPlanContractError("split evidence detail invalid")
        return cls(raw["source"], float(confidence), detail)


@dataclass(frozen=True, slots=True)
class SplitSegmentV1:
    index: int
    start: float
    end: float
    title: str
    evidence: tuple[SplitEvidenceV1, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SplitSegmentV1":
        if not isinstance(raw, dict) or set(raw) != {
            "index",
            "start",
            "end",
            "title",
            "evidence",
        }:
            raise SplitPlanContractError("split segment fields invalid")
        index, start, end = raw["index"], raw["start"], raw["end"]
        if not isinstance(index, int) or isinstance(index, bool) or not 1 <= index <= 999:
            raise SplitPlanContractError("split segment index invalid")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in (start, end)
        ) or not 0 <= start < end:
            raise SplitPlanContractError("split segment range invalid")
        title = raw["title"]
        if not isinstance(title, str) or len(title) > 200:
            raise SplitPlanContractError("split segment title invalid")
        evidence_raw = raw["evidence"]
        if not isinstance(evidence_raw, list) or len(evidence_raw) > 8:
            raise SplitPlanContractError("split segment evidence invalid")
        evidence = tuple(SplitEvidenceV1.from_dict(item) for item in evidence_raw)
        return cls(index, float(start), float(end), title, evidence)


@dataclass(frozen=True, slots=True)
class SplitPlanV1:
    source_url: str
    source_title: str
    duration: float
    composite_likely: bool
    segments: tuple[SplitSegmentV1, ...]
    warnings: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SplitPlanV1":
        required = {
            "source_url",
            "source_title",
            "duration",
            "composite_likely",
            "segments",
            "warnings",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise SplitPlanContractError("split plan fields invalid")
        if not isinstance(raw["source_url"], str) or not raw["source_url"].startswith(
            "https://"
        ):
            raise SplitPlanContractError("split plan source URL invalid")
        title = raw["source_title"]
        if not isinstance(title, str) or not 1 <= len(title) <= 300:
            raise SplitPlanContractError("split plan source title invalid")
        duration = raw["duration"]
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or not 0 < duration <= 86400
        ):
            raise SplitPlanContractError("split plan duration invalid")
        likely = raw["composite_likely"]
        if not isinstance(likely, bool):
            raise SplitPlanContractError("split plan likelihood invalid")
        segment_values = raw["segments"]
        if not isinstance(segment_values, list) or len(segment_values) > 200:
            raise SplitPlanContractError("split plan segments invalid")
        segments = tuple(SplitSegmentV1.from_dict(item) for item in segment_values)
        previous_end = 0.0
        for expected_index, segment in enumerate(segments, 1):
            if segment.index != expected_index or segment.start < previous_end:
                raise SplitPlanContractError("split plan segment order invalid")
            if segment.end > float(duration) + 0.001:
                raise SplitPlanContractError("split segment exceeds source duration")
            previous_end = segment.end
        if likely and len(segments) < 2:
            raise SplitPlanContractError("composite plan needs at least two segments")
        warning_values = raw["warnings"]
        if (
            not isinstance(warning_values, list)
            or len(warning_values) > 20
            or not all(isinstance(item, str) and len(item) <= 300 for item in warning_values)
        ):
            raise SplitPlanContractError("split plan warnings invalid")
        return cls(
            raw["source_url"],
            title,
            float(duration),
            likely,
            segments,
            tuple(warning_values),
        )
