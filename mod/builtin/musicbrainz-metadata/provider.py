"""Manual, bounded MusicBrainz recording lookup MOD."""

from __future__ import annotations

import json
import math
import re
import sys
from typing import Any
from urllib import error as url_error
from urllib import request as url_request
from urllib.parse import urlencode, urljoin, urlsplit


_API_ROOT = "https://musicbrainz.org/ws/2/recording/"
_MAX_RESPONSE_BYTES = 512 * 1024
_MAX_QUERY_LENGTH = 200
_MAX_RESULTS = 10
_USER_AGENT = (
    "MediaManager/39.0 "
    "(https://github.com/z1379228/MediaManager-)"
)
_MBID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class _OfficialRedirectHandler(url_request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: object,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> object:
        absolute = urljoin(str(getattr(req, "full_url", "")), newurl)
        if not _official_api_url(absolute):
            raise ValueError("MusicBrainz redirect left the official API")
        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            absolute,
        )


def _official_api_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() == "musicbrainz.org"
        and parsed.username is None
        and parsed.password is None
        and port is None
        and parsed.path == "/ws/2/recording/"
        and not parsed.fragment
    )


def _bounded_text(value: object, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def _artist_credit(value: object) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for raw in value[:20]:
        if not isinstance(raw, dict):
            continue
        name = _bounded_text(raw.get("name"), 200)
        if not name:
            artist = raw.get("artist")
            if isinstance(artist, dict):
                name = _bounded_text(artist.get("name"), 200)
        if name:
            parts.append(name)
            join = _bounded_text(raw.get("joinphrase"), 20)
            if join:
                parts.append(f" {join} ")
    return "".join(parts).strip()[:200]


def _duration_seconds(value: object) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        return None
    seconds = round(float(value) / 1000)
    return seconds if seconds <= 86_400 else None


def _request_json(query: str, limit: int) -> dict[str, Any]:
    url = _API_ROOT + "?" + urlencode(
        {
            "query": query,
            "fmt": "json",
            "limit": str(limit),
        }
    )
    request = url_request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="GET",
    )
    opener = url_request.build_opener(_OfficialRedirectHandler())
    try:
        with opener.open(request, timeout=15) as response:
            if not _official_api_url(response.geturl()):
                raise ValueError("MusicBrainz response left the official API")
            raw_length = response.headers.get("Content-Length", "")
            if raw_length:
                try:
                    content_length = int(raw_length)
                except ValueError as caught:
                    raise ValueError(
                        "MusicBrainz response length is invalid"
                    ) from caught
                if content_length > _MAX_RESPONSE_BYTES:
                    raise ValueError("MusicBrainz response is too large")
            payload = response.read(_MAX_RESPONSE_BYTES + 1)
    except url_error.HTTPError as caught:
        if caught.code == 503:
            raise RuntimeError("MusicBrainz is busy; try again later") from caught
        raise RuntimeError(
            f"MusicBrainz request failed with HTTP {caught.code}"
        ) from caught
    except url_error.URLError as caught:
        raise RuntimeError("MusicBrainz request failed") from caught
    if len(payload) > _MAX_RESPONSE_BYTES:
        raise ValueError("MusicBrainz response is too large")
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as caught:
        raise ValueError("MusicBrainz returned invalid JSON") from caught
    if not isinstance(document, dict):
        raise ValueError("MusicBrainz returned an invalid document")
    return document


def search(payload: dict[str, Any]) -> dict[str, Any]:
    query = _bounded_text(payload.get("query"), _MAX_QUERY_LENGTH)
    raw_limit = payload.get("limit", 10)
    if not query:
        raise ValueError("MusicBrainz query is empty")
    if (
        isinstance(raw_limit, bool)
        or not isinstance(raw_limit, int)
        or not 1 <= raw_limit <= _MAX_RESULTS
    ):
        raise ValueError("MusicBrainz result limit is invalid")
    if payload.get("content_type") != "music" or payload.get("cursor", ""):
        raise ValueError("MusicBrainz search options are invalid")
    document = _request_json(query, raw_limit)
    recordings = document.get("recordings")
    if not isinstance(recordings, list):
        raise ValueError("MusicBrainz recordings are missing")
    results: list[dict[str, Any]] = []
    for recording in recordings[:raw_limit]:
        if not isinstance(recording, dict):
            continue
        recording_id = _bounded_text(recording.get("id"), 36).casefold()
        title = _bounded_text(recording.get("title"), 300)
        if not _MBID_RE.fullmatch(recording_id) or not title:
            continue
        results.append(
            {
                "video_id": recording_id,
                "url": f"https://musicbrainz.org/recording/{recording_id}",
                "title": title,
                "artist": _artist_credit(recording.get("artist-credit")),
                "duration": _duration_seconds(recording.get("length")),
                "language": "",
                "category": "music",
                "thumbnail_url": "",
            }
        )
    return {"items": results, "next_cursor": ""}


def emit(message: dict[str, Any]) -> None:
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("operation") != "search":
            raise ValueError("unsupported MusicBrainz operation")
        emit({"type": "result", "value": search(payload)})
        return 0
    except Exception as caught:
        emit({"type": "error", "error": f"{type(caught).__name__}: {caught}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
