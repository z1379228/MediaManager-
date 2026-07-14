"""Bilibili download MOD with optional XML danmaku sidecars."""

from __future__ import annotations

import json
import importlib.util
import math
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


class StderrLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)


PROVIDER_ID = "bilibili"
DISPLAY_NAME = "Bilibili"
_MEDIA_SUFFIXES = (".mp4", ".mkv", ".webm", ".m4a", ".mp3")
_BILIBILI_VIDEO_ID = re.compile(r"^(?:BV[0-9A-Za-z]+|av\d+)$", re.IGNORECASE)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def runtime_options(request: dict[str, Any]) -> dict[str, Any]:
    raw = request.get("js_runtime")
    if raw is None:
        return {}
    if (
        not isinstance(raw, dict)
        or set(raw) != {"name", "path"}
        or raw["name"] not in {"deno", "node", "quickjs"}
    ):
        raise ValueError("JavaScript runtime configuration is invalid")
    path = Path(str(raw["path"])).resolve()
    if not path.is_file():
        raise ValueError("JavaScript runtime executable is missing")
    return {"js_runtimes": {raw["name"]: {"path": str(path)}}}


def _finite_duration(value: object, *, allow_zero: bool = False) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (0 <= value <= 604_800 if allow_zero else 0 < value <= 604_800)
    ):
        return float(value)
    return None


def _content_kind(info: dict[str, Any], url: str) -> str:
    extractor = str(info.get("extractor_key") or info.get("extractor") or "")
    if "bangumi" in extractor.casefold() or "/bangumi/play/" in url:
        return "bangumi"
    entries = info.get("entries")
    return "multipart" if isinstance(entries, list) and len(entries) > 1 else "video"


def _subtitle_languages(info: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for field in ("subtitles", "automatic_captions"):
        raw = info.get(field)
        if isinstance(raw, dict):
            values.update(
                str(language)[:32]
                for language, tracks in raw.items()
                if language and isinstance(tracks, list) and tracks
            )
    return sorted(values)[:32]


def _playlist_entry_url(raw: dict[str, Any], entry_id: str, position: int) -> str:
    value = str(raw.get("webpage_url") or raw.get("url") or "")[:4096]
    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("https://", "http://")) and _BILIBILI_VIDEO_ID.fullmatch(
        value or entry_id
    ):
        value = f"https://www.bilibili.com/video/{value or entry_id}"
    if (
        value.startswith(("https://", "http://"))
        and position > 1
        and "/video/" in value
        and "?p=" not in value
        and "&p=" not in value
    ):
        value += ("&" if "?" in value else "?") + f"p={position}"
    return value[:4096]


def analyze(request: dict[str, Any]) -> dict[str, Any]:
    from yt_dlp import YoutubeDL

    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "extractor_retries": 3,
    }
    options.update(runtime_options(request))
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=False)
    if not isinstance(info, dict):
        raise ValueError("Bilibili did not return media metadata")
    chapters: list[dict[str, Any]] = []
    for chapter in (info.get("chapters") or [])[:200]:
        if not isinstance(chapter, dict):
            continue
        start = _finite_duration(chapter.get("start_time"), allow_zero=True)
        end = _finite_duration(chapter.get("end_time"), allow_zero=True)
        if start is None:
            continue
        chapters.append(
            {
                "start_time": start,
                "end_time": end,
                "title": str(chapter.get("title") or "")[:200],
            }
        )
    entries = info.get("entries")
    return {
        "id": str(info.get("id") or "")[:100],
        "title": str(info.get("title") or "未命名媒體")[:300],
        "duration": _finite_duration(info.get("duration")),
        "uploader": str(
            info.get("uploader") or info.get("channel") or info.get("creator") or ""
        )[:200],
        "webpage_url": str(info.get("webpage_url") or request["url"])[:4096],
        "thumbnail": str(info.get("thumbnail") or "")[:4096],
        "part_count": len(entries) if isinstance(entries, list) else 1,
        "chapters": chapters,
        "description": str(info.get("description") or "")[:20_000],
        "content_kind": _content_kind(info, str(request["url"])),
        "subtitle_languages": _subtitle_languages(info),
        "extractor": str(
            info.get("extractor_key") or info.get("extractor") or ""
        )[:100],
    }


def playlist(request: dict[str, Any]) -> list[dict[str, Any]]:
    from yt_dlp import YoutubeDL

    limit = int(request.get("limit", 500))
    if not 1 <= limit <= 500:
        raise ValueError("playlist limit is invalid")
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "playlistend": limit,
        "socket_timeout": 20,
        "extractor_retries": 3,
    }
    options.update(runtime_options(request))
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=False)
    raw_entries = info.get("entries") if isinstance(info, dict) else None
    if raw_entries is None:
        raise ValueError("URL does not contain a supported Bilibili list")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for position, raw in enumerate(raw_entries, start=1):
        if position > limit:
            break
        if not isinstance(raw, dict):
            entries.append(
                {
                    "entry_id": f"unavailable-{position}",
                    "url": "",
                    "title": f"無法讀取的分段 #{position}",
                    "artist": "",
                    "duration": None,
                    "position": position,
                    "available": False,
                    "unavailable_reason": "分段失效、受限或無法解析",
                }
            )
            continue
        base_id = str(raw.get("id") or f"unavailable-{position}")[:90]
        entry_id = (
            base_id if base_id not in seen else f"{base_id}-p{position}"
        )[:100]
        url = _playlist_entry_url(raw, base_id, position)
        valid_url = url.startswith(("https://", "http://"))
        available = valid_url and entry_id not in seen
        reason = ""
        if not valid_url:
            reason = "Bilibili 未提供可驗證的分段網址"
        elif entry_id in seen:
            reason = "清單內重複分段"
        if available:
            seen.add(entry_id)
        entries.append(
            {
                "entry_id": entry_id,
                "url": url if valid_url else "",
                "title": str(raw.get("title") or f"未命名分段 #{position}")[:300],
                "artist": str(
                    raw.get("uploader")
                    or raw.get("channel")
                    or raw.get("creator")
                    or ""
                )[:200],
                "duration": _finite_duration(raw.get("duration")),
                "position": position,
                "available": available,
                "unavailable_reason": reason[:200],
            }
        )
    if not entries:
        raise ValueError("Bilibili list contains no entries")
    return entries


def _media_options(
    request: dict[str, Any],
) -> tuple[str, str, list[str], str, str]:
    formats = {
        "best": "b[height<=1080]/bv*[height<=1080]+ba/b",
        "video-1080": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "video-720": "bv*[height<=720]+ba/b[height<=720]/b",
        "video-480": "bv*[height<=480]+ba/b[height<=480]/b",
        "audio-m4a": "ba[ext=m4a]/ba",
        "audio-mp3": "ba[abr<=192]/ba",
    }
    preset = request.get("format_preset", "best")
    if preset not in formats:
        raise ValueError("format preset is invalid")
    subtitle_mode = request.get("subtitle_mode", "none")
    languages = request.get("subtitle_languages", [])
    timed_comment_mode = request.get("timed_comment_mode", "none")
    container_preset = request.get("container_preset", "auto")
    if (
        subtitle_mode not in {"none", "selected", "all"}
        or not isinstance(languages, list)
        or len(languages) > 8
        or len(set(languages)) != len(languages)
        or not all(
            isinstance(item, str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,15}", item)
            for item in languages
        )
        or (subtitle_mode == "selected" and not languages)
        or (subtitle_mode != "selected" and languages)
    ):
        raise ValueError("subtitle options are invalid")
    if (
        timed_comment_mode not in {"none", "source", "ass"}
        or container_preset not in {"auto", "mkv"}
        or (timed_comment_mode == "ass" and str(preset).startswith("audio-"))
        or (container_preset == "mkv" and timed_comment_mode != "ass")
    ):
        raise ValueError("timed-comment or container options are invalid")
    return (
        str(preset),
        str(subtitle_mode),
        languages,
        str(timed_comment_mode),
        str(container_preset),
    )


def _completed_media_path(
    ydl: object,
    info: dict[str, Any],
    output: Path,
    output_filename: str,
    audio_suffix: str | None,
) -> Path:
    prepared = Path(ydl.prepare_filename(info))
    candidates: list[Path] = []
    if output_filename:
        candidates.append(output / output_filename)
    if audio_suffix:
        candidates.append(prepared.with_suffix(audio_suffix))
    candidates.append(prepared)
    candidates.extend(prepared.with_suffix(suffix) for suffix in _MEDIA_SUFFIXES)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.is_relative_to(output) and resolved.is_file():
                return resolved
        except OSError:
            continue
    return prepared


def _find_danmaku_xml(output: Path, media: Path) -> Path | None:
    matches = sorted(output.glob(f"{media.stem}*danmaku*.xml"))
    if not matches:
        all_xml = sorted(output.glob(f"{media.stem}*.xml"))
        if len(all_xml) == 1:
            matches = all_xml
    for candidate in matches:
        try:
            if (
                candidate.is_symlink()
                or not candidate.is_file()
                or candidate.stat().st_size <= 0
            ):
                continue
            resolved = candidate.resolve()
            if resolved.is_relative_to(output):
                return resolved
        except OSError:
            continue
    return None


def _convert_danmaku(xml_path: Path, ass_path: Path) -> int:
    converter_path = Path(__file__).resolve().with_name("danmaku_ass.py")
    spec = importlib.util.spec_from_file_location(
        "mediamanager_bilibili_danmaku_ass",
        converter_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("danmaku converter cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.convert_xml_to_ass(xml_path, ass_path))


def _mux_ass_into_mkv(
    media: Path,
    ass_path: Path,
    ffmpeg_location: object,
) -> Path:
    ffmpeg = Path(str(ffmpeg_location or "")).resolve()
    if not ffmpeg.is_file() or ffmpeg.name.casefold() not in {
        "ffmpeg",
        "ffmpeg.exe",
    }:
        raise ValueError("FFmpeg executable is unavailable for MKV muxing")
    target = media.with_suffix(".mkv")
    if target != media and target.exists():
        target = media.with_name(f"{media.stem} [danmaku].mkv")
    if target != media and target.exists():
        raise ValueError("safe MKV output filename is already in use")
    temporary = target.with_name(
        f".{target.stem}.{uuid.uuid4().hex}.tmp.mkv"
    )
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(media),
        "-i",
        str(ass_path),
        "-map",
        "0",
        "-map",
        "1:0",
        "-c",
        "copy",
        "-max_muxing_queue_size",
        "4096",
        str(temporary),
    ]
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        if (
            result.returncode != 0
            or not temporary.is_file()
            or temporary.stat().st_size <= 0
        ):
            detail = (result.stderr or "FFmpeg did not create MKV output")[-500:]
            raise RuntimeError(detail)
        if target == media:
            temporary.replace(media)
            return media
        temporary.replace(target)
        media.unlink()
        return target
    finally:
        if temporary.exists() and temporary.parent == target.parent:
            temporary.unlink()


def download(request: dict[str, Any]) -> str:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    output_filename = str(request.get("output_filename") or "")
    if output_filename and (
        Path(output_filename).name != output_filename
        or len(output_filename) > 180
        or output_filename[-1] in " ."
    ):
        raise ValueError("output filename is invalid")
    output_template = (
        output / f"{Path(output_filename).stem}.%(ext)s"
        if output_filename
        else output / "%(title).180B [%(id)s].%(ext)s"
    )

    def hook(status: dict[str, Any]) -> None:
        info = status.get("info_dict") or {}
        emit(
            {
                "type": "progress",
                "downloaded_bytes": status.get("downloaded_bytes"),
                "total_bytes": status.get("total_bytes"),
                "total_bytes_estimate": status.get("total_bytes_estimate"),
                "speed": status.get("_speed_str", ""),
                "eta": status.get("_eta_str", ""),
                "title": info.get("title", ""),
            }
        )

    (
        preset,
        subtitle_mode,
        languages,
        timed_comment_mode,
        container_preset,
    ) = _media_options(request)
    formats = {
        "best": "b[height<=1080]/bv*[height<=1080]+ba/b",
        "video-1080": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "video-720": "bv*[height<=720]+ba/b[height<=720]/b",
        "video-480": "bv*[height<=480]+ba/b[height<=480]/b",
        "audio-m4a": "ba[ext=m4a]/ba",
        "audio-mp3": "ba[abr<=192]/ba",
    }
    options: dict[str, Any] = {
        "format": formats[preset],
        "merge_output_format": "mkv" if container_preset == "mkv" else "mp4",
        "outtmpl": str(output_template),
        "windowsfilenames": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "quiet": True,
        "noprogress": True,
        "logger": StderrLogger(),
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
    }
    options.update(runtime_options(request))
    if request.get("ffmpeg_location"):
        options["ffmpeg_location"] = request["ffmpeg_location"]
    audio_only = request.get("audio_only") is True or preset.startswith("audio-")
    audio_suffix = None
    if audio_only:
        codec = "mp3" if preset == "audio-mp3" else "m4a"
        audio_suffix = f".{codec}"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "192" if codec == "mp3" else "128",
            }
        ]
    effective_languages = list(languages)
    if timed_comment_mode != "none" and subtitle_mode != "all":
        effective_languages = list(dict.fromkeys((*effective_languages, "danmaku")))
    if subtitle_mode != "none" or timed_comment_mode != "none":
        options.update(
            writesubtitles=True,
            subtitleslangs=(
                ["all"] if subtitle_mode == "all" else effective_languages
            ),
            subtitlesformat="best",
        )
    start, end = request.get("start_time"), request.get("end_time")
    if start is not None or end is not None:
        if not audio_only:
            maximum_height = {
                "video-480": 480,
                "video-720": 720,
                "video-1080": 1080,
                "best": 1080,
            }[preset]
            options["format"] = f"b[height<={maximum_height}]/b"
        options["download_ranges"] = download_range_func(
            None, [(start or 0.0, end or float("inf"))]
        )
        options["force_keyframes_at_cuts"] = True
    emit({"type": "progress", "title": "Preparing Bilibili download"})
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=True)
        if not isinstance(info, dict):
            raise ValueError("Bilibili download did not return media metadata")
        media = _completed_media_path(
            ydl,
            info,
            output,
            output_filename,
            audio_suffix,
        )
    if timed_comment_mode == "none":
        return str(media)
    xml_path = _find_danmaku_xml(output, media)
    if xml_path is None:
        emit(
            {
                "type": "progress",
                "title": "影片已完成；未取得可保留的彈幕 XML",
            }
        )
        return str(media)
    if timed_comment_mode == "source":
        return str(media)
    ass_path = xml_path.with_name(f"{media.stem}.danmaku.ass")
    try:
        count = _convert_danmaku(xml_path, ass_path)
    except (OSError, RuntimeError, ValueError) as error:
        emit(
            {
                "type": "progress",
                "title": f"ASS 轉換失敗，已保留 XML：{error}",
            }
        )
        return str(media)
    emit({"type": "progress", "title": f"已轉換 {count} 則彈幕為 ASS"})
    if container_preset == "mkv":
        try:
            media = _mux_ass_into_mkv(
                media,
                ass_path,
                request.get("ffmpeg_location"),
            )
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            emit(
                {
                    "type": "progress",
                    "title": f"MKV 封裝失敗，已保留原影片、XML 與 ASS：{error}",
                }
            )
            return str(media)
    return str(media)


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "analyze":
            emit({"type": "result", "value": analyze(raw)})
        elif operation == "playlist":
            emit({"type": "result", "value": playlist(raw)})
        elif operation == "download":
            emit({"type": "result", "value": download(raw)})
        else:
            raise ValueError("unsupported provider operation")
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
