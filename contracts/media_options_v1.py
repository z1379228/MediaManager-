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
    video_codec: str = ""
    audio_codec: str = ""
    transcodes: bool = False


FORMAT_PRESETS_V1 = (
    FormatPresetV1("best", "自動相容（最高 1080p）", "video", 1080),
    FormatPresetV1("video-2160", "影片 2160p（4K）", "video", 2160),
    FormatPresetV1("video-1440", "影片 1440p", "video", 1440),
    FormatPresetV1("video-1080", "影片 1080p", "video", 1080),
    FormatPresetV1(
        "video-h264-1080",
        "影片 H.264/AAC 1080p（相容優先）",
        "video",
        1080,
        "mp4",
        "h264",
        "aac",
    ),
    FormatPresetV1("video-720", "影片 720p", "video", 720),
    FormatPresetV1("video-480", "影片 480p", "video", 480),
    FormatPresetV1("audio-m4a", "音訊 M4A", "audio", extension="m4a"),
    FormatPresetV1(
        "audio-m4a-256",
        "音訊 AAC/M4A 256k",
        "audio",
        extension="m4a",
        audio_codec="aac",
        transcodes=True,
    ),
    FormatPresetV1("audio-mp3", "音訊 MP3", "audio", extension="mp3"),
    FormatPresetV1(
        "audio-mp3-320",
        "音訊 MP3 320k",
        "audio",
        extension="mp3",
        audio_codec="mp3",
        transcodes=True,
    ),
    FormatPresetV1(
        "audio-opus",
        "音訊 Opus 160k",
        "audio",
        extension="opus",
        audio_codec="opus",
        transcodes=True,
    ),
    FormatPresetV1(
        "audio-flac",
        "音訊 FLAC（轉碼）",
        "audio",
        extension="flac",
        audio_codec="flac",
        transcodes=True,
    ),
    FormatPresetV1(
        "audio-wav",
        "音訊 WAV PCM（大容量）",
        "audio",
        extension="wav",
        audio_codec="pcm",
        transcodes=True,
    ),
)
FORMAT_PRESET_IDS_V1 = frozenset(item.preset_id for item in FORMAT_PRESETS_V1)
SUBTITLE_MODES_V1 = frozenset({"none", "selected", "all"})
TIMED_COMMENT_MODES_V1 = frozenset({"none", "source", "ass"})
CONTAINER_PRESETS_V1 = frozenset({"auto", "mp4", "mkv", "webm"})
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
    if format_preset.startswith("audio-") and container_preset != "auto":
        raise MediaOptionsContractError(
            "audio formats do not accept a video container preset"
        )
