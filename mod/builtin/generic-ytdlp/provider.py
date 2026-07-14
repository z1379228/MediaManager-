"""Bounded multi-site yt-dlp download MOD using an explicit host allowlist."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any


class StderrLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)


PROVIDER_ID = "generic-ytdlp"
DISPLAY_NAME = "其他網站 Beta"


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
        raise ValueError("site did not return media metadata")
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
    return {
        "id": str(info.get("id") or "")[:100],
        "title": str(info.get("title") or "未命名媒體")[:300],
        "duration": _finite_duration(info.get("duration")),
        "uploader": str(
            info.get("uploader") or info.get("channel") or info.get("creator") or ""
        )[:200],
        "webpage_url": str(info.get("webpage_url") or request["url"])[:4096],
        "chapters": chapters,
        "description": str(info.get("description") or "")[:20_000],
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
        raise ValueError("URL does not contain a supported media list")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    unavailable_values = {
        "private",
        "premium_only",
        "subscriber_only",
        "needs_auth",
    }
    for position, raw in enumerate(raw_entries, start=1):
        if position > limit:
            break
        if not isinstance(raw, dict):
            entries.append(
                {
                    "entry_id": f"unavailable-{position}",
                    "url": "",
                    "title": f"無法讀取的項目 #{position}",
                    "artist": "",
                    "duration": None,
                    "position": position,
                    "available": False,
                    "unavailable_reason": "項目失效、受限或無法解析",
                }
            )
            continue
        entry_id = str(raw.get("id") or f"unavailable-{position}")[:100]
        title = str(raw.get("title") or f"未命名項目 #{position}")[:300]
        artist = str(
            raw.get("uploader") or raw.get("channel") or raw.get("creator") or ""
        )[:200]
        availability = str(raw.get("availability") or "").casefold()
        url = str(raw.get("webpage_url") or raw.get("url") or "")[:4096]
        valid_url = url.startswith(("https://", "http://"))
        available = (
            valid_url
            and availability not in unavailable_values
            and entry_id not in seen
        )
        reason = ""
        if not valid_url:
            reason = "網站未提供可驗證的項目網址"
        elif availability in unavailable_values:
            reason = "項目需要登入、付費或額外權限"
        elif entry_id in seen:
            reason = "清單內重複項目"
        if available:
            seen.add(entry_id)
        entries.append(
            {
                "entry_id": entry_id,
                "url": url if valid_url else "",
                "title": title,
                "artist": artist,
                "duration": _finite_duration(raw.get("duration")),
                "position": position,
                "available": available,
                "unavailable_reason": reason[:200],
            }
        )
    if not entries:
        raise ValueError("media list contains no entries")
    return entries


def _media_options(request: dict[str, Any]) -> tuple[str, str, list[str]]:
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
    return str(preset), str(subtitle_mode), languages


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

    preset, subtitle_mode, languages = _media_options(request)
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
        "merge_output_format": "mp4",
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
    if audio_only:
        codec = "mp3" if preset == "audio-mp3" else "m4a"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "192" if codec == "mp3" else "128",
            }
        ]
    if subtitle_mode != "none":
        options.update(
            writesubtitles=True,
            writeautomaticsub=True,
            subtitleslangs=languages if subtitle_mode == "selected" else ["all"],
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
    emit({"type": "progress", "title": "Preparing download"})
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=True)
        prepared = Path(ydl.prepare_filename(info))
        if output_filename:
            requested = output / output_filename
            if requested.is_file():
                return str(requested)
        if audio_only:
            converted = prepared.with_suffix(
                ".mp3" if preset == "audio-mp3" else ".m4a"
            )
            if converted.is_file():
                return str(converted)
        return str(prepared)


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
