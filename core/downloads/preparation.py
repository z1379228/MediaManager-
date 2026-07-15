"""Side-effect-free download naming, size and confirmation summaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from contracts.media_analysis_v1 import MediaFormatV1
from contracts.media_options_v1 import FORMAT_PRESETS_V1
from core.downloads.models import DownloadRequest
from core.downloads.preflight import DownloadPreflight


_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True, slots=True)
class DownloadBatchPreview:
    item_count: int
    output_directory: Path
    format_preset: str
    filename: str
    estimated_bytes: int | None
    free_bytes: int


def human_bytes(value: int | None) -> str:
    if value is None:
        return "未知"
    amount = float(max(0, value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return "未知"


def download_option_lines(request: DownloadRequest) -> tuple[str, ...]:
    """Return explicit confirmation lines for segment, subtitle and danmaku options."""

    if request.start_time is None and request.end_time is None:
        segment = "完整內容"
    else:
        start = f"{(request.start_time or 0):g} 秒"
        end = f"{request.end_time:g} 秒" if request.end_time is not None else "結尾"
        segment = f"{start} → {end}"
    subtitles = {
        "none": "不下載",
        "all": "全部可用字幕",
        "selected": "指定語言：" + "、".join(request.subtitle_languages),
    }[request.subtitle_mode]
    timed_comments = {
        "none": "不保留",
        "source": "保留 XML",
        "ass": "保留 XML 並轉為 ASS",
    }[request.timed_comment_mode]
    container = "MKV（嵌入 ASS）" if request.container_preset == "mkv" else "自動"
    return (
        f"區段：{segment}",
        f"字幕：{subtitles}",
        f"彈幕：{timed_comments}",
        f"封裝：{container}",
    )


def suggest_output_filename(title: str, media_id: str, preset_id: str) -> str:
    preset = next(
        (item for item in FORMAT_PRESETS_V1 if item.preset_id == preset_id), None
    )
    if preset is None:
        raise ValueError("format preset is invalid")
    stem = " ".join(title.split()) or "media"
    stem = _UNSAFE.sub("_", stem).strip(" .") or "media"
    identifier = _UNSAFE.sub("_", " ".join(media_id.split())).strip(" .")
    extension = preset.extension or "mp4"
    suffix = f" [{identifier}]" if identifier else ""
    maximum_stem = max(1, 180 - len(suffix) - len(extension) - 1)
    return f"{stem[:maximum_stem].rstrip(' .')}{suffix}.{extension}"


def estimate_preset_bytes(
    formats: tuple[MediaFormatV1, ...], preset_id: str
) -> int | None:
    preset = next(
        (item for item in FORMAT_PRESETS_V1 if item.preset_id == preset_id), None
    )
    if preset is None:
        raise ValueError("format preset is invalid")
    candidates = []
    for item in formats:
        has_video = item.video_codec.casefold() != "none"
        has_audio = item.audio_codec.casefold() != "none"
        if preset.media_kind == "audio" and (not has_audio or has_video):
            continue
        if preset.media_kind == "video" and not has_video:
            continue
        if (
            preset.maximum_height is not None
            and item.height is not None
            and item.height > preset.maximum_height
        ):
            continue
        if item.estimated_bytes is not None:
            candidates.append(item.estimated_bytes)
    return max(candidates) if candidates else None


def available_preset_ids(formats: tuple[MediaFormatV1, ...]) -> tuple[str, ...]:
    if not formats:
        return tuple(item.preset_id for item in FORMAT_PRESETS_V1)
    video_heights = tuple(
        item.height
        for item in formats
        if item.video_codec.casefold() != "none" and item.height is not None
    )
    has_audio = any(item.audio_codec.casefold() != "none" for item in formats)
    available: list[str] = []
    for preset in FORMAT_PRESETS_V1:
        if preset.preset_id == "best" and video_heights:
            available.append(preset.preset_id)
        elif preset.media_kind == "video" and any(
            height >= int(preset.maximum_height or 0) for height in video_heights
        ):
            available.append(preset.preset_id)
        elif preset.media_kind == "audio" and has_audio:
            available.append(preset.preset_id)
    return tuple(available or ("best",))


def format_detail_lines(
    formats: tuple[MediaFormatV1, ...], *, limit: int = 12
) -> tuple[str, ...]:
    lines = []
    for item in formats[: max(1, min(limit, 20))]:
        media = f"{item.height}p" if item.height else "audio"
        fps = f" {item.fps:g}fps" if item.fps else ""
        lines.append(
            f"{item.format_id}: {media}{fps} {item.extension.upper()} · "
            f"V:{item.video_codec} A:{item.audio_codec} · "
            f"{human_bytes(item.estimated_bytes)}"
        )
    return tuple(lines)


def build_batch_preview(
    requests: tuple[DownloadRequest, ...],
    preflight: DownloadPreflight,
    *,
    estimated_bytes: int | None = None,
) -> DownloadBatchPreview:
    if not requests:
        raise ValueError("download batch is empty")
    first = requests[0]
    if any(
        request.output_dir.resolve(strict=False)
        != first.output_dir.resolve(strict=False)
        or request.format_preset != first.format_preset
        for request in requests
    ):
        raise ValueError("download batch preview requires shared output and format")
    total_estimate = (
        estimated_bytes * len(requests) if estimated_bytes is not None else None
    )
    return DownloadBatchPreview(
        len(requests),
        first.output_dir.resolve(strict=False),
        first.format_preset,
        first.output_filename if len(requests) == 1 else "",
        total_estimate,
        preflight.lowest_free_bytes,
    )
