"""Versioned, transport-neutral media output options."""

from __future__ import annotations

import re
from dataclasses import dataclass


class MediaOptionsContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FormatPresetV1:
    preset_id: str
    label: str
    media_kind: str
    maximum_height: int | None = None
    extension: str = ""


FORMAT_PRESETS_V1 = (
    FormatPresetV1("best", "自動相容（最高 1080p）", "video", 1080),
    FormatPresetV1("video-1080", "影片 1080p", "video", 1080),
    FormatPresetV1("video-720", "影片 720p", "video", 720),
    FormatPresetV1("video-480", "影片 480p", "video", 480),
    FormatPresetV1("audio-m4a", "音訊 M4A", "audio", extension="m4a"),
    FormatPresetV1("audio-mp3", "音訊 MP3", "audio", extension="mp3"),
)
FORMAT_PRESET_IDS_V1 = frozenset(item.preset_id for item in FORMAT_PRESETS_V1)
SUBTITLE_MODES_V1 = frozenset({"none", "selected", "all"})
TIMED_COMMENT_MODES_V1 = frozenset({"none", "source", "ass"})
CONTAINER_PRESETS_V1 = frozenset({"auto", "mkv"})
_LANGUAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,15}$")


def validate_media_options_v1(
    format_preset: str,
    subtitle_mode: str,
    subtitle_languages: tuple[str, ...],
    timed_comment_mode: str = "none",
    container_preset: str = "auto",
) -> None:
    if format_preset not in FORMAT_PRESET_IDS_V1:
        raise MediaOptionsContractError("unsupported format preset")
    if subtitle_mode not in SUBTITLE_MODES_V1:
        raise MediaOptionsContractError("unsupported subtitle mode")
    if (
        not isinstance(subtitle_languages, tuple)
        or len(subtitle_languages) > 8
        or len(set(subtitle_languages)) != len(subtitle_languages)
        or any(not _LANGUAGE.fullmatch(item) for item in subtitle_languages)
    ):
        raise MediaOptionsContractError("subtitle languages are invalid")
    if subtitle_mode == "selected" and not subtitle_languages:
        raise MediaOptionsContractError("selected subtitles require languages")
    if subtitle_mode != "selected" and subtitle_languages:
        raise MediaOptionsContractError(
            "subtitle languages require selected subtitle mode"
        )
    if timed_comment_mode not in TIMED_COMMENT_MODES_V1:
        raise MediaOptionsContractError("unsupported timed-comment mode")
    if container_preset not in CONTAINER_PRESETS_V1:
        raise MediaOptionsContractError("unsupported container preset")
    if timed_comment_mode == "ass" and format_preset.startswith("audio-"):
        raise MediaOptionsContractError(
            "ASS timed comments require a video format"
        )
    if container_preset == "mkv" and timed_comment_mode != "ass":
        raise MediaOptionsContractError(
            "MKV timed comments require ASS conversion"
        )
