"""Bounded media-format summaries returned by download MOD analysis."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any
import re


class MediaAnalysisContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MediaFormatV1:
    format_id: str
    extension: str
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str
    audio_codec: str
    estimated_bytes: int | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MediaFormatV1":
        required = {
            "format_id",
            "extension",
            "width",
            "height",
            "fps",
            "video_codec",
            "audio_codec",
            "estimated_bytes",
        }
        if not isinstance(raw, dict) or set(raw) != required:
            raise MediaAnalysisContractError("media format fields invalid")
        text_limits = {
            "format_id": 100,
            "extension": 16,
            "video_codec": 80,
            "audio_codec": 80,
        }
        if any(
            not isinstance(raw[field], str)
            or not raw[field]
            or len(raw[field]) > limit
            for field, limit in text_limits.items()
        ):
            raise MediaAnalysisContractError("media format text invalid")
        for field, maximum in (("width", 16384), ("height", 8640)):
            value = raw[field]
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 1 <= value <= maximum
            ):
                raise MediaAnalysisContractError("media dimensions invalid")
        fps = raw["fps"]
        if fps is not None and (
            not isinstance(fps, (int, float))
            or isinstance(fps, bool)
            or not math.isfinite(fps)
            or not 0 < fps <= 1000
        ):
            raise MediaAnalysisContractError("media frame rate invalid")
        estimated = raw["estimated_bytes"]
        if estimated is not None and (
            not isinstance(estimated, int)
            or isinstance(estimated, bool)
            or not 1 <= estimated <= 16 * 1024**4
        ):
            raise MediaAnalysisContractError("media size estimate invalid")
        return cls(
            raw["format_id"],
            raw["extension"],
            raw["width"],
            raw["height"],
            float(fps) if fps is not None else None,
            raw["video_codec"],
            raw["audio_codec"],
            estimated,
        )


def parse_media_formats(raw: object) -> tuple[MediaFormatV1, ...]:
    if not isinstance(raw, list) or len(raw) > 40:
        raise MediaAnalysisContractError("media format list invalid")
    values = tuple(MediaFormatV1.from_dict(item) for item in raw)
    if len({item.format_id for item in values}) != len(values):
        raise MediaAnalysisContractError("media format IDs are duplicated")
    return values


_LANGUAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,31}$")


def parse_media_languages(raw: object) -> tuple[str, ...]:
    if (
        not isinstance(raw, list)
        or len(raw) > 32
        or len(raw) != len(set(raw))
        or not all(isinstance(item, str) and _LANGUAGE.fullmatch(item) for item in raw)
    ):
        raise MediaAnalysisContractError("media language list invalid")
    return tuple(raw)
