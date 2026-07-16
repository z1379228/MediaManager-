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
_CONTAINER_IDS = frozenset({"auto", "mp4", "mkv", "webm"})


@dataclass(frozen=True, slots=True)
class ContainerCompatibility:
    container_id: str
    compatible: bool
    recommended_container: str
    message: str


def _codec_matches(actual: str, requested: str) -> bool:
    normalized = actual.casefold()
    aliases = {
        "h264": ("h264", "avc1"),
        "aac": ("aac", "mp4a"),
    }
    return any(token in normalized for token in aliases.get(requested, (requested,)))


def _contains_codec(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(token in normalized for token in tokens)


def _preset_for(preset_id: str):
    preset = next(
        (item for item in FORMAT_PRESETS_V1 if item.preset_id == preset_id), None
    )
    if preset is None:
        raise ValueError("format preset is invalid")
    return preset


def _video_candidates(
    formats: tuple[MediaFormatV1, ...], preset_id: str
) -> tuple[MediaFormatV1, ...]:
    preset = _preset_for(preset_id)
    values = []
    for item in formats:
        if item.video_codec.casefold() == "none":
            continue
        if (
            preset.maximum_height is not None
            and item.height is not None
            and item.height > preset.maximum_height
        ):
            continue
        if preset.video_codec and not _codec_matches(
            item.video_codec, preset.video_codec
        ):
            continue
        values.append(item)
    return tuple(values)


def _audio_candidates(
    formats: tuple[MediaFormatV1, ...]
) -> tuple[MediaFormatV1, ...]:
    return tuple(
        item for item in formats if item.audio_codec.casefold() != "none"
    )


def _container_supported(
    formats: tuple[MediaFormatV1, ...], preset_id: str, container_id: str
) -> bool:
    videos = _video_candidates(formats, preset_id)
    audio = _audio_candidates(formats)
    if container_id == "mkv":
        return bool(videos)
    if container_id == "mp4":
        video_ok = any(
            item.extension.casefold() == "mp4"
            and _contains_codec(
                item.video_codec, ("h264", "avc1", "h265", "hevc", "av01")
            )
            for item in videos
        )
        audio_ok = any(
            item.extension.casefold() in {"m4a", "mp4"}
            and _contains_codec(item.audio_codec, ("aac", "mp4a", "mp3"))
            for item in audio
        )
        return video_ok and audio_ok
    if container_id == "webm":
        video_ok = any(
            item.extension.casefold() == "webm"
            and _contains_codec(item.video_codec, ("vp8", "vp9", "av01", "av1"))
            for item in videos
        )
        audio_ok = any(
            item.extension.casefold() in {"webm", "opus", "ogg"}
            and _contains_codec(item.audio_codec, ("opus", "vorbis"))
            for item in audio
        )
        return video_ok and audio_ok
    return False


def container_compatibility(
    formats: tuple[MediaFormatV1, ...], preset_id: str, container_id: str
) -> ContainerCompatibility:
    if container_id not in _CONTAINER_IDS:
        raise ValueError("container preset is invalid")
    preset = _preset_for(preset_id)
    if preset.media_kind == "audio":
        compatible = container_id == "auto"
        return ContainerCompatibility(
            container_id,
            compatible,
            "auto",
            (
                "音訊格式由所選編碼決定副檔名，不使用影片容器。"
                if compatible
                else "音訊輸出不能指定 MP4、MKV 或 WebM 影片容器。"
            ),
        )
    if not formats:
        compatible = container_id in {"auto", "mkv"}
        return ContainerCompatibility(
            container_id,
            compatible,
            "auto",
            (
                "自動封裝可直接使用；讀取影片資訊後可判定其他容器。"
                if container_id == "auto"
                else "MKV 可容納一般影音軌；讀取資訊後仍會顯示實際編碼。"
                if compatible
                else "請先讀取影片資訊，才能驗證此容器與來源編碼。"
            ),
        )
    mp4 = _container_supported(formats, preset_id, "mp4")
    webm = _container_supported(formats, preset_id, "webm")
    recommended = "mp4" if mp4 else "webm" if webm else "mkv"
    if container_id == "auto":
        return ContainerCompatibility(
            container_id,
            True,
            recommended,
            f"由下載 MOD 自動封裝；依目前格式建議 {recommended.upper()}。",
        )
    compatible = _container_supported(formats, preset_id, container_id)
    return ContainerCompatibility(
        container_id,
        compatible,
        recommended,
        (
            f"來源包含可直接封裝為 {container_id.upper()} 的影音軌。"
            if compatible
            else f"所選來源編碼不能安全封裝為 {container_id.upper()}；"
            f"建議改用 {recommended.upper()} 或自動。"
        ),
    )


def advanced_format_summary(
    formats: tuple[MediaFormatV1, ...], preset_id: str
) -> str:
    preset = _preset_for(preset_id)
    if not formats:
        return "尚未取得解析度、FPS、動態範圍與編碼資料"
    if preset.media_kind == "audio":
        source = max(
            _audio_candidates(formats),
            key=lambda item: int(item.estimated_bytes or 0),
            default=None,
        )
        if source is None:
            return "來源未回報可用音軌"
        return (
            f"音訊來源 {source.extension.upper()} · A:{source.audio_codec} · "
            f"輸出 {preset.extension.upper()}"
        )
    source = max(
        _video_candidates(formats, preset_id),
        key=lambda item: (
            int(item.height or 0),
            float(item.fps or 0),
            int(item.estimated_bytes or 0),
        ),
        default=None,
    )
    if source is None:
        return "來源未回報符合此預設的視訊軌"
    dimensions = (
        f"{source.width}×{source.height}"
        if source.width and source.height
        else f"{source.height}p"
        if source.height
        else "未知解析度"
    )
    fps = f"{source.fps:g} FPS" if source.fps else "FPS 未標示"
    dynamic_range = (
        source.dynamic_range.upper()
        if source.dynamic_range.casefold() != "unknown"
        else "HDR/SDR 未標示"
    )
    audio = next(
        (
            item.audio_codec
            for item in _audio_candidates(formats)
            if item.video_codec.casefold() == "none"
        ),
        source.audio_codec,
    )
    return (
        f"{dimensions} · {fps} · {dynamic_range} · "
        f"V:{source.video_codec} · A:{audio}"
    )


def format_preset_encoding_note(preset_id: str) -> str:
    preset = next(
        (item for item in FORMAT_PRESETS_V1 if item.preset_id == preset_id), None
    )
    if preset is None:
        raise ValueError("format preset is invalid")
    if preset.preset_id == "best":
        return "編碼依來源自動選擇；最高 1080p，通常不重新編碼。"
    if preset.preset_id == "video-h264-1080":
        return "優先選取 H.264 視訊與 AAC 音訊並封裝為 MP4，不做視訊轉碼。"
    if preset.preset_id == "video-2160":
        return "選取最高 2160p（4K）來源；檔案、頻寬與合併時間會明顯增加。"
    if preset.preset_id == "video-1440":
        return "選取最高 1440p 來源；來源未提供時由下載器選擇較低可用畫質。"
    if preset.preset_id == "audio-m4a-256":
        return "使用 FFmpeg 轉為約 256 kbps AAC/M4A；不會超越原始音訊品質。"
    if preset.preset_id == "audio-mp3-320":
        return "使用 FFmpeg 轉為約 320 kbps MP3；較高位元率不代表來源音質提升。"
    if preset.preset_id == "audio-opus":
        return "使用 FFmpeg 輸出約 160 kbps Opus，適合較小檔案。"
    if preset.preset_id == "audio-flac":
        return "使用 FFmpeg 輸出 FLAC；來源若有損，轉碼不會提升原始音質。"
    if preset.preset_id == "audio-wav":
        return "使用 FFmpeg 轉為未壓縮 WAV PCM；容量很大，且不會提升有損來源音質。"
    if preset.media_kind == "audio":
        return f"使用 FFmpeg 輸出 {preset.extension.upper()} 音訊。"
    return "依解析度選取來源串流；必要時只進行容器合併，不做視訊轉碼。"


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
    container = {
        "auto": "自動",
        "mp4": "MP4",
        "mkv": (
            "MKV（嵌入 ASS）"
            if request.timed_comment_mode == "ass"
            else "MKV"
        ),
        "webm": "WebM",
    }[request.container_preset]
    return (
        f"區段：{segment}",
        f"字幕：{subtitles}",
        f"彈幕：{timed_comments}",
        f"封裝：{container}",
    )


def suggest_output_filename(
    title: str,
    media_id: str,
    preset_id: str,
    container_id: str = "auto",
) -> str:
    preset = _preset_for(preset_id)
    if container_id not in _CONTAINER_IDS:
        raise ValueError("container preset is invalid")
    stem = " ".join(title.split()) or "media"
    stem = _UNSAFE.sub("_", stem).strip(" .") or "media"
    identifier = _UNSAFE.sub("_", " ".join(media_id.split())).strip(" .")
    extension = (
        preset.extension
        or (container_id if container_id != "auto" else "mp4")
    )
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
            preset.video_codec
            and has_video
            and not _codec_matches(item.video_codec, preset.video_codec)
        ):
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
            if preset.video_codec and not any(
                item.video_codec.casefold() != "none"
                and _codec_matches(item.video_codec, preset.video_codec)
                for item in formats
            ):
                continue
            if preset.audio_codec and not any(
                item.audio_codec.casefold() != "none"
                and _codec_matches(item.audio_codec, preset.audio_codec)
                for item in formats
            ):
                continue
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
        dynamic_range = (
            f" {item.dynamic_range.upper()}"
            if item.dynamic_range.casefold() != "unknown"
            else ""
        )
        lines.append(
            f"{item.format_id}: {media}{fps}{dynamic_range} "
            f"{item.extension.upper()} · "
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
