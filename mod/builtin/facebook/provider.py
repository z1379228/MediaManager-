"""Public Facebook video download MOD with an exact URL allowlist."""

from __future__ import annotations

import json
import importlib.util
import math
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PROVIDER_ID = "facebook"
DISPLAY_NAME = "Facebook"
_HOSTS = frozenset(
    {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "web.facebook.com",
        "mbasic.facebook.com",
        "fb.watch",
    }
)
_MEDIA_SUFFIXES = (".mp4", ".mkv", ".webm", ".m4a", ".mp3")


def _browser_impersonation_target() -> object | None:
    """Return the typed yt-dlp target required by its programmatic API."""

    if importlib.util.find_spec("curl_cffi") is None:
        return None
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
    except ImportError:
        return None
    return ImpersonateTarget.from_str("chrome")


def _apply_public_page_options(options: dict[str, Any]) -> None:
    # Facebook can serve a parseable public page only to a browser-like TLS
    # client. This does not load cookies or bypass login/visibility controls.
    target = _browser_impersonation_target()
    if target is not None:
        options["impersonate"] = target


def _raise_public_parse_error(
    error: Exception, *, impersonation_active: bool
) -> None:
    message = str(error)
    if "Cannot parse data" in message or "Unsupported impersonate target" in message:
        if impersonation_active:
            raise RuntimeError(
                "Facebook 已啟用 curl-cffi 瀏覽器模擬，但公開頁未提供可下載媒體；"
                "該內容可能需要登入、貼文權限或地區存取。MediaManager 不會讀取 Cookie。"
            ) from error
        raise RuntimeError(
            "Facebook 公開頁無法解析；目前未偵測到 curl-cffi 瀏覽器模擬支援。"
        ) from error
    raise error


class StderrLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _single_video_query(query: str) -> str | None:
    try:
        fields = parse_qsl(
            query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=4,
        )
    except ValueError:
        return None
    if len(fields) != 1 or fields[0][0].casefold() != "v":
        return None
    value = fields[0][1]
    return value if value.isascii() and value.isdigit() and 1 <= len(value) <= 32 else None


def canonical_url(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme != "https"
        or host not in _HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        return None
    parts = tuple(part for part in parsed.path.split("/") if part)
    if host == "fb.watch":
        if (
            parsed.query
            or len(parts) != 1
            or not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", parts[0])
        ):
            return None
        return f"https://fb.watch/{parts[0]}/"
    if parsed.path in {"/watch", "/watch/", "/video.php"}:
        video_id = _single_video_query(parsed.query)
        if video_id is None:
            return None
        path = "/video.php" if parsed.path == "/video.php" else "/watch/"
        return urlunsplit(
            ("https", "www.facebook.com", path, urlencode({"v": video_id}), "")
        )
    if parsed.query:
        return None
    if (
        len(parts) == 2
        and parts[0] in {"reel", "videos"}
        and parts[1].isascii()
        and parts[1].isdigit()
        and 1 <= len(parts[1]) <= 32
    ):
        return f"https://www.facebook.com/{parts[0]}/{parts[1]}/"
    if (
        len(parts) == 3
        and re.fullmatch(r"[A-Za-z0-9._-]{1,100}", parts[0])
        and parts[1] == "videos"
        and parts[2].isascii()
        and parts[2].isdigit()
        and 1 <= len(parts[2]) <= 32
    ):
        return f"https://www.facebook.com/{parts[0]}/videos/{parts[2]}/"
    return None


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


def _bounded_number(value: object, maximum: float) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 < value <= maximum
    ):
        return float(value)
    return None


def _duration(value: object) -> float | None:
    return _bounded_number(value, 604_800)


def format_summaries(info: dict[str, Any]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    raw_formats = info.get("formats")
    for raw in raw_formats[:500] if isinstance(raw_formats, list) else []:
        if not isinstance(raw, dict):
            continue
        format_id = str(raw.get("format_id") or "")[:100]
        if not format_id or format_id in values:
            continue
        size = _bounded_number(raw.get("filesize"), 16 * 1024**4) or _bounded_number(
            raw.get("filesize_approx"), 16 * 1024**4
        )
        width = _bounded_number(raw.get("width"), 16384)
        height = _bounded_number(raw.get("height"), 8640)
        values[format_id] = {
            "format_id": format_id,
            "extension": str(raw.get("ext") or "unknown")[:16],
            "width": int(width) if width else None,
            "height": int(height) if height else None,
            "fps": _bounded_number(raw.get("fps"), 1000),
            "video_codec": str(raw.get("vcodec") or "none")[:80],
            "audio_codec": str(raw.get("acodec") or "none")[:80],
            "estimated_bytes": int(size) if size else None,
        }
    return sorted(
        values.values(),
        key=lambda item: (int(item["height"] or 0), int(item["estimated_bytes"] or 0)),
        reverse=True,
    )[:40]


def _languages(info: dict[str, Any]) -> tuple[list[str], list[str]]:
    subtitles: set[str] = set()
    for field in ("subtitles", "automatic_captions"):
        tracks = info.get(field)
        if isinstance(tracks, dict):
            subtitles.update(
                str(language)[:32]
                for language, items in tracks.items()
                if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,31}", str(language))
                and isinstance(items, list)
                and items
            )
    audio = {
        str(item.get("language"))[:32]
        for item in (info.get("formats") or [])[:500]
        if isinstance(item, dict)
        and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9-]{0,31}", str(item.get("language") or "")
        )
        and str(item.get("acodec") or "none").casefold() != "none"
    }
    return sorted(audio)[:32], sorted(subtitles)[:32]


def _thumbnail(value: object) -> str:
    text = str(value or "")[:1000]
    try:
        parsed = urlsplit(text)
        host = (parsed.hostname or "").casefold()
    except ValueError:
        return ""
    if (
        parsed.scheme == "https"
        and (host == "fbcdn.net" or host.endswith(".fbcdn.net"))
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and not parsed.fragment
    ):
        return text
    return ""


def analyze(request: dict[str, Any]) -> dict[str, Any]:
    from yt_dlp import YoutubeDL

    url = canonical_url(request.get("url"))
    if url is None:
        raise ValueError("unsupported Facebook public video URL")
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "extractor_retries": 3,
    }
    options.update(runtime_options(request))
    _apply_public_page_options(options)
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:
        _raise_public_parse_error(
            error, impersonation_active="impersonate" in options
        )
    if not isinstance(info, dict):
        raise ValueError("Facebook did not return public video metadata")
    audio_languages, subtitle_languages = _languages(info)
    return {
        "id": str(info.get("id") or "")[:100],
        "title": str(info.get("title") or "Facebook 公開影片")[:300],
        "duration": _duration(info.get("duration")),
        "uploader": str(info.get("uploader") or info.get("channel") or "Facebook")[:200],
        "webpage_url": url,
        "thumbnail": _thumbnail(info.get("thumbnail")),
        "chapters": [],
        "description": str(info.get("description") or "")[:20_000],
        "formats": format_summaries(info),
        "audio_languages": audio_languages,
        "subtitle_languages": subtitle_languages,
    }


def _media_options(request: dict[str, Any]) -> tuple[str, str, list[str]]:
    preset = request.get("format_preset", "best")
    if preset not in {"best", "video-1080", "video-720", "video-480"}:
        raise ValueError("format preset is invalid")
    mode = request.get("subtitle_mode", "none")
    languages = request.get("subtitle_languages", [])
    if (
        mode != "none"
        or not isinstance(languages, list)
        or languages
        or request.get("audio_only") is True
        or request.get("start_time") is not None
        or request.get("end_time") is not None
    ):
        raise ValueError("Facebook MOD supports public full-video downloads only")
    return str(preset), str(mode), languages


def _completed_path(
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
    candidates.extend((prepared, *(prepared.with_suffix(suffix) for suffix in _MEDIA_SUFFIXES)))
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.is_relative_to(output) and resolved.is_file():
                return resolved
        except OSError:
            continue
    return prepared


def download(request: dict[str, Any]) -> str:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    url = canonical_url(request.get("url"))
    if url is None:
        raise ValueError("unsupported Facebook public video URL")
    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    output_filename = str(request.get("output_filename") or "")
    if output_filename and (
        Path(output_filename).name != output_filename
        or len(output_filename) > 180
        or output_filename[-1] in " ."
    ):
        raise ValueError("output filename is invalid")
    template = (
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
                "title": str(info.get("title") or "Facebook download")[:300],
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
        "outtmpl": str(template),
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
    _apply_public_page_options(options)
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
    if subtitle_mode != "none":
        options.update(
            writesubtitles=True,
            writeautomaticsub=True,
            subtitleslangs=languages if subtitle_mode == "selected" else ["all"],
            subtitlesformat="best",
        )
    start, end = request.get("start_time"), request.get("end_time")
    if start is not None or end is not None:
        options["download_ranges"] = download_range_func(
            None, [(start or 0.0, end or float("inf"))]
        )
        options["force_keyframes_at_cuts"] = True
    emit({"type": "progress", "title": "Preparing Facebook download"})
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, dict):
                raise ValueError("Facebook download returned no media metadata")
            return str(
                _completed_path(ydl, info, output, output_filename, audio_suffix)
            )
    except Exception as error:
        _raise_public_parse_error(
            error, impersonation_active="impersonate" in options
        )
        raise AssertionError("unreachable")


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "analyze":
            emit({"type": "result", "value": analyze(raw)})
        elif operation == "download":
            emit({"type": "result", "value": download(raw)})
        elif operation == "playlist":
            raise ValueError("Facebook MOD does not support playlists")
        else:
            raise ValueError("unsupported provider operation")
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
