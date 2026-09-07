"""Lightweight YouTube search MOD using yt-dlp flat extraction."""

from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from typing import Any
from urllib.parse import urlencode


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
    from pathlib import Path

    path = Path(str(raw["path"])).resolve()
    if not path.is_file():
        raise ValueError("JavaScript runtime executable is missing")
    return {"js_runtimes": {raw["name"]: {"path": str(path)}}}


_MUSIC_SIGNALS = (
    "music",
    "official audio",
    "lyrics",
    "lyric video",
    "song",
    "songs",
    "album",
    "albums",
    "playlist",
    "playlists",
    "mix",
    "mixes",
    "remix",
    "remixes",
    "soundtrack",
    "soundtracks",
    "ost",
    "karaoke",
    "bgm",
    "音樂",
    "歌曲",
    "歌詞",
    "歌單",
    "專輯",
    "原聲帶",
    "作業用",
)
_LATIN_MUSIC_SIGNAL_RE = re.compile(
    "|".join(
        rf"(?<![a-z0-9_]){re.escape(signal)}(?![a-z0-9_])"
        for signal in _MUSIC_SIGNALS
        if signal.isascii()
    )
)
_UNSPACED_MUSIC_SIGNALS = tuple(
    signal for signal in _MUSIC_SIGNALS if not signal.isascii()
)
_TOPIC_CHANNEL_RE = re.compile(r"(?:^|\s)[-\u2010-\u2015\u2212]\s*topic$")
_MAX_QUERY_LENGTH = 200
_MAX_DISCOVERY_DURATION = 86400


def contains_music_signal(value: str) -> bool:
    """Match Latin signals as terms while retaining CJK substring behavior."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return bool(_LATIN_MUSIC_SIGNAL_RE.search(normalized)) or any(
        signal in normalized for signal in _UNSPACED_MUSIC_SIGNALS
    )


def has_topic_channel_signal(entry: dict[str, Any]) -> bool:
    """Recognize YouTube's strict ``Artist - Topic`` channel suffix."""

    return any(
        _TOPIC_CHANNEL_RE.search(
            unicodedata.normalize("NFKC", str(entry.get(field) or "")).casefold()
        )
        for field in ("channel", "uploader")
    )


def search_scope(request: dict[str, Any]) -> str:
    value = request.get("content_type", "all")
    if value not in {"all", "music", "video"}:
        raise ValueError("search content type is invalid")
    return str(value)


def search_target(query: str, content_type: str, fetch_limit: int) -> str:
    """Route explicit music searches to yt-dlp's bounded songs extractor."""

    if content_type == "music":
        return (
            "https://music.youtube.com/search?"
            f"{urlencode({'q': query})}#songs"
        )
    return f"ytsearch{fetch_limit}:{query}"


def result_category(
    entry: dict[str, Any],
    content_type: str,
    query: str,
) -> str:
    if content_type in {"music", "video"}:
        return content_type
    metadata = " ".join(
        str(entry.get(field) or "")
        for field in ("title", "track", "album", "genre", "categories")
    )
    signals = f"{query} {metadata}".casefold()
    return (
        "music"
        if contains_music_signal(signals) or has_topic_channel_signal(entry)
        else "video"
    )


def search_offset(request: dict[str, Any]) -> int:
    value = request.get("cursor", "")
    if value == "":
        return 0
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError("search cursor is invalid")
    offset = int(value)
    if offset < 0 or offset > 199:
        raise ValueError("search cursor is outside the bounded result window")
    return offset


def bounded_duration(value: object) -> int | None:
    """Normalize flat metadata without violating the discovery contract."""

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or value > _MAX_DISCOVERY_DURATION
    ):
        return None
    return int(value)


def search(request: dict[str, Any]) -> dict[str, Any]:
    from yt_dlp import YoutubeDL

    query = " ".join(str(request.get("query", "")).split())
    limit = int(request.get("limit", 12))
    if not 1 <= len(query) <= _MAX_QUERY_LENGTH:
        raise ValueError("search query length is invalid")
    limit = max(1, min(int(limit), 50))
    offset = search_offset(request)
    fetch_limit = min(offset + limit + 1, 200)
    content_type = search_scope(request)
    target = search_target(query, content_type, fetch_limit)
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": StderrLogger(),
        "skip_download": True,
        "extract_flat": True,
        "playlistend": fetch_limit,
        "socket_timeout": 20,
        "retries": 2,
        "extractor_retries": 2,
    }
    options.update(runtime_options(request))
    emit({"type": "progress", "title": "Searching"})
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(target, download=False)
    results: list[dict[str, Any]] = []
    entries = ((info or {}).get("entries") or [])[offset : offset + limit + 1]
    has_more = len(entries) > limit and offset + limit < 200
    for entry in entries[:limit]:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        video_id = str(entry["id"])
        thumbnail_url = str(entry.get("thumbnail") or "")[:1000]
        if not thumbnail_url:
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
        results.append(
            {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": str(entry.get("title") or "Untitled")[:300],
                "artist": str(entry.get("channel") or entry.get("uploader") or "")[
                    :200
                ],
                "duration": bounded_duration(entry.get("duration")),
                "language": str(entry.get("language") or "")[:32],
                "category": result_category(entry, content_type, query),
                "thumbnail_url": thumbnail_url,
            }
        )
    return {
        "items": results,
        "next_cursor": str(offset + limit) if has_more else "",
    }


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        if raw.get("operation") != "search":
            raise ValueError("unsupported discovery operation")
        emit(
            {
                "type": "result",
                "value": search(raw),
            }
        )
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
