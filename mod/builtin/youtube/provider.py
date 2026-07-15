"""YouTube download MOD process. Communicates only through JSON lines."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class StderrLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)


PROVIDER_ID = "youtube"
DISPLAY_NAME = "YouTube"


def _thumbnail_url(info: dict[str, Any]) -> str:
    candidates: list[object] = [info.get("thumbnail")]
    thumbnails = info.get("thumbnails")
    if isinstance(thumbnails, list):
        candidates.extend(
            item.get("url")
            for item in reversed(thumbnails[:30])
            if isinstance(item, dict)
        )
    for candidate in candidates:
        value = str(candidate or "")[:1000]
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme == "https"
                and (parsed.hostname or "").casefold()
                in {"i.ytimg.com", "img.youtube.com"}
                and parsed.username is None
                and parsed.password is None
                and parsed.port is None
                and not parsed.fragment
            ):
                return value
        except ValueError:
            continue
    return ""


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


def format_summaries(info: dict[str, Any]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    raw_formats = info.get("formats")
    for raw in raw_formats[:500] if isinstance(raw_formats, list) else []:
        if not isinstance(raw, dict):
            continue
        format_id = str(raw.get("format_id") or "")[:100]
        if not format_id or format_id in values:
            continue

        def bounded_number(name: str, maximum: float) -> float | None:
            value = raw.get(name)
            return (
                float(value)
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
                and 0 < value <= maximum
                else None
            )

        size = bounded_number("filesize", 16 * 1024**4) or bounded_number(
            "filesize_approx", 16 * 1024**4
        )
        values[format_id] = {
            "format_id": format_id,
            "extension": str(raw.get("ext") or "unknown")[:16],
            "width": (
                int(width) if (width := bounded_number("width", 16384)) else None
            ),
            "height": (
                int(height) if (height := bounded_number("height", 8640)) else None
            ),
            "fps": bounded_number("fps", 1000),
            "video_codec": str(raw.get("vcodec") or "none")[:80],
            "audio_codec": str(raw.get("acodec") or "none")[:80],
            "estimated_bytes": int(size) if size else None,
        }
    return sorted(
        values.values(),
        key=lambda item: (int(item["height"] or 0), int(item["estimated_bytes"] or 0)),
        reverse=True,
    )[:40]


def media_languages(info: dict[str, Any]) -> tuple[list[str], list[str]]:
    subtitles: set[str] = set()
    for field in ("subtitles", "automatic_captions"):
        tracks = info.get(field)
        if isinstance(tracks, dict):
            subtitles.update(
                str(language)[:32]
                for language, values in tracks.items()
                if language
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,31}", str(language))
                and isinstance(values, list)
                and values
            )
    audio = {
        str(item.get("language"))[:32]
        for item in (info.get("formats") or [])[:500]
        if isinstance(item, dict)
        and item.get("language")
        and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9-]{0,31}", str(item.get("language"))
        )
        and str(item.get("acodec") or "none").casefold() != "none"
    }
    return sorted(audio)[:32], sorted(subtitles)[:32]


def analyze(request: dict[str, Any]) -> dict[str, Any]:
    from yt_dlp import YoutubeDL

    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    options.update(runtime_options(request))
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=False)
    chapters: list[dict[str, Any]] = []
    for chapter in (info.get("chapters") or [])[:200]:
        if not isinstance(chapter, dict):
            continue
        start, end = chapter.get("start_time"), chapter.get("end_time")
        if not isinstance(start, (int, float)) or isinstance(start, bool):
            continue
        chapters.append(
            {
                "start_time": float(start),
                "end_time": (
                    float(end)
                    if isinstance(end, (int, float)) and not isinstance(end, bool)
                    else None
                ),
                "title": str(chapter.get("title") or "")[:200],
            }
        )
    audio_languages, subtitle_languages = media_languages(info)
    return {
        "id": info.get("id", ""),
        "title": info.get("title", ""),
        "duration": info.get("duration"),
        "uploader": info.get("uploader", ""),
        "webpage_url": info.get("webpage_url", request["url"]),
        "chapters": chapters,
        "description": str(info.get("description") or "")[:20_000],
        "formats": format_summaries(info),
        "audio_languages": audio_languages,
        "subtitle_languages": subtitle_languages,
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
    }
    options.update(runtime_options(request))
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(request["url"], download=False)
    raw_entries = info.get("entries") if isinstance(info, dict) else None
    if raw_entries is None:
        raise ValueError("URL does not contain a playlist")

    unavailable_values = {
        "private",
        "premium_only",
        "subscriber_only",
        "needs_auth",
    }
    entries: list[dict[str, Any]] = []
    seen_entry_ids: dict[str, int] = {}
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
                    "thumbnail_url": "",
                    "available": False,
                    "unavailable_reason": "影片已失效、移除或無權存取",
                }
            )
            continue
        entry_id = str(raw.get("id") or f"unavailable-{position}")[:100]
        title = str(raw.get("title") or f"未命名項目 #{position}")[:300]
        artist = str(
            raw.get("uploader") or raw.get("channel") or raw.get("creator") or ""
        )[:200]
        duration = raw.get("duration")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            duration = None
        availability = str(raw.get("availability") or "").casefold()
        url = str(raw.get("webpage_url") or raw.get("url") or "")
        if url and not url.startswith(("http://", "https://")) and entry_id:
            url = f"https://www.youtube.com/watch?v={entry_id}"
        available = bool(url) and availability not in unavailable_values
        duplicate_position = seen_entry_ids.get(entry_id)
        if available and duplicate_position is not None:
            available = False
            availability = f"播放清單內重複項目（首次出現於 #{duplicate_position}）"
        elif available:
            seen_entry_ids[entry_id] = position
        entries.append(
            {
                "entry_id": entry_id,
                "url": url if url.startswith(("http://", "https://")) else "",
                "title": title,
                "artist": artist,
                "duration": duration,
                "position": position,
                "thumbnail_url": _thumbnail_url(raw),
                "available": available,
                "unavailable_reason": (
                    "" if available else availability or "影片已失效、移除或無權存取"
                )[:200],
            }
        )
    if not entries:
        raise ValueError("playlist contains no entries")
    return entries


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

    format_preset = request.get("format_preset", "best")
    formats = {
        "best": (
            "b[height<=1080][ext=mp4]/b[height<=1080]/"
            "bv*[height<=1080]+ba/b"
        ),
        "video-1080": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "video-720": "bv*[height<=720]+ba/b[height<=720]/b",
        "video-480": "bv*[height<=480]+ba/b[height<=480]/b",
        "audio-m4a": "ba[ext=m4a]/ba",
        "audio-mp3": "ba[abr<=192]/ba",
    }
    if format_preset not in formats:
        raise ValueError("format preset is invalid")
    subtitle_mode = request.get("subtitle_mode", "none")
    subtitle_languages = request.get("subtitle_languages", [])
    if (
        subtitle_mode not in {"none", "selected", "all"}
        or not isinstance(subtitle_languages, list)
        or len(subtitle_languages) > 8
        or len(set(subtitle_languages)) != len(subtitle_languages)
        or not all(
            isinstance(item, str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,15}", item)
            for item in subtitle_languages
        )
        or (subtitle_mode == "selected" and not subtitle_languages)
        or (subtitle_mode != "selected" and subtitle_languages)
    ):
        raise ValueError("subtitle options are invalid")

    options: dict[str, Any] = {
        "format": formats[format_preset],
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
        "continuedl": True,
        "nopart": False,
        "overwrites": False,
    }
    options.update(runtime_options(request))
    if request.get("ffmpeg_location"):
        options["ffmpeg_location"] = request["ffmpeg_location"]
    audio_only = request.get("audio_only") is True or format_preset.startswith(
        "audio-"
    )
    if audio_only:
        codec = "mp3" if format_preset == "audio-mp3" else "m4a"
        options["format"] = formats.get(format_preset, "ba[ext=m4a]/ba")
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
            subtitleslangs=(
                subtitle_languages if subtitle_mode == "selected" else ["all"]
            ),
            subtitlesformat="best",
        )
    start, end = request.get("start_time"), request.get("end_time")
    if start is not None or end is not None:
        # Segment mode uses a progressive stream to avoid a second merge download.
        if not audio_only:
            maximum_height = {
                "video-480": 480,
                "video-720": 720,
                "video-1080": 1080,
                "best": 1080,
            }[format_preset]
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
                ".mp3" if format_preset == "audio-mp3" else ".m4a"
            )
            if converted.is_file():
                return str(converted)
        return str(prepared)


def prepare_preview(request: dict[str, Any]) -> str:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    duration = float(request["duration"])
    preview_length = request.get("preview_length")
    preview_length = float(preview_length) if preview_length is not None else None
    if not 0 < duration <= 86400:
        raise ValueError("preview duration is invalid")

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
                "title": info.get("title", "Preparing audio preview"),
            }
        )

    options: dict[str, Any] = {
        "format": "ba[abr<=64]/ba[abr<=96]/ba",
        "outtmpl": str(output / "preview.%(ext)s"),
        "noplaylist": True,
        "max_filesize": 100 * 1024 * 1024,
        "progress_hooks": [hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }
        ],
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
    if preview_length is not None:
        if not 0 < preview_length <= 120:
            raise ValueError("preview length is invalid")
        options["download_ranges"] = download_range_func(
            None, [(0, min(duration, preview_length))]
        )
        options["force_keyframes_at_cuts"] = True
    elif duration > 7200:
        options["download_ranges"] = download_range_func(None, [(0, 7200)])
        options["force_keyframes_at_cuts"] = True
    emit({"type": "progress", "title": "Preparing audio preview"})
    with YoutubeDL(options) as ydl:
        ydl.extract_info(request["url"], download=True)
    preview = output / "preview.mp3"
    if not preview.is_file() or preview.stat().st_size == 0:
        raise RuntimeError("audio preview was not created")
    return str(preview)


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
        elif operation == "prepare_preview":
            emit({"type": "result", "value": prepare_preview(raw)})
        else:
            raise ValueError("unsupported provider operation")
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
