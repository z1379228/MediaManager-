"""Bounded Bilibili catalogue search using its public official search endpoint."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import sys
from typing import Any
from urllib import error, parse, request


API_URL = "https://api.bilibili.com/x/web-interface/search/type"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RESULT_WINDOW = 200
_BVID = re.compile(r"BV[A-Za-z0-9]{10}")


class _OfficialRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> request.Request | None:
        absolute = parse.urljoin(req.full_url, newurl)
        try:
            parsed = parse.urlsplit(absolute)
            port = parsed.port
        except ValueError as error:
            raise ValueError("Bilibili search redirect is invalid") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.bilibili.com"
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
        ):
            raise ValueError("Bilibili search redirect left the official API")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def plain_text(value: object, *, limit: int) -> str:
    parser = _PlainText()
    parser.feed(str(value or ""))
    parser.close()
    return " ".join("".join(parser.parts).split())[:limit]


def duration_seconds(value: object) -> int | None:
    parts = str(value or "").split(":")
    if not 1 < len(parts) <= 3 or any(not part.isascii() or not part.isdigit() for part in parts):
        return None
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total if 0 <= total <= 86400 else None


def thumbnail_url(value: object) -> str:
    raw = str(value or "").strip()
    if raw.startswith("//"):
        raw = f"https:{raw}"
    try:
        parsed = parse.urlsplit(raw)
        port = parsed.port
    except ValueError:
        return ""
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme.casefold() != "https"
        or not host.endswith(".hdslb.com")
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or len(raw) > 1000
    ):
        return ""
    return raw


def page_number(cursor: object, page_size: int) -> int:
    if cursor in {None, ""}:
        return 1
    match = re.fullmatch(r"([1-9][0-9]{0,2}):([1-9][0-9]?)", str(cursor))
    if match is None or int(match.group(2)) != page_size:
        raise ValueError("Bilibili search cursor is invalid")
    page = int(match.group(1))
    if (page - 1) * page_size >= MAX_RESULT_WINDOW:
        raise ValueError("Bilibili search cursor is outside the bounded result window")
    return page


def fetch_search(query: str, page: int, page_size: int) -> dict[str, Any]:
    params = parse.urlencode(
        {
            "search_type": "video",
            "keyword": query,
            "page": page,
            "page_size": page_size,
        }
    )
    search_request = request.Request(
        f"{API_URL}?{params}",
        headers={
            "Accept": "application/json",
            "Referer": "https://search.bilibili.com/",
            "User-Agent": "MediaManager/9 BilibiliSearch",
        },
    )
    opener = request.build_opener(_OfficialRedirectHandler())
    try:
        with opener.open(search_request, timeout=20) as response:
            final = parse.urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != "api.bilibili.com":
                raise ValueError("Bilibili search redirected outside the official API")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except error.HTTPError as failure:
        if failure.code in {412, 429}:
            raise RuntimeError(
                "Bilibili official search requires browser verification or is "
                "temporarily rate-limited; no YouTube fallback was used"
            ) from failure
        raise
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("Bilibili search response is too large")
    raw = json.loads(payload.decode("utf-8"))
    if not isinstance(raw, dict) or raw.get("code") != 0 or not isinstance(raw.get("data"), dict):
        raise ValueError("Bilibili search returned an invalid response")
    return raw["data"]


def search(raw_request: dict[str, Any]) -> dict[str, Any]:
    query = " ".join(str(raw_request.get("query", "")).split())
    if not 1 <= len(query) <= 200:
        raise ValueError("Bilibili search query length is invalid")
    content_type = raw_request.get("content_type", "all")
    if content_type not in {"all", "music", "video"}:
        raise ValueError("Bilibili search content type is invalid")
    page_size = max(1, min(int(raw_request.get("limit", 12)), 50))
    page = page_number(raw_request.get("cursor", ""), page_size)
    provider_query = query
    if content_type == "music" and not any(
        signal in query.casefold() for signal in ("music", "song", "音樂", "歌曲", "bgm")
    ):
        provider_query = f"{query} 音樂"
    emit({"type": "progress", "title": "Searching Bilibili"})
    data = fetch_search(provider_query, page, page_size)
    entries = data.get("result")
    if entries is None:
        entries = []
    if not isinstance(entries, list) or len(entries) > page_size:
        raise ValueError("Bilibili search result list is invalid")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        bvid = str(entry.get("bvid") or "")
        title = plain_text(entry.get("title"), limit=300)
        if not _BVID.fullmatch(bvid) or not title or bvid in seen:
            continue
        seen.add(bvid)
        items.append(
            {
                "video_id": bvid,
                "url": f"https://www.bilibili.com/video/{bvid}",
                "title": title,
                "artist": plain_text(entry.get("author"), limit=200),
                "duration": duration_seconds(entry.get("duration")),
                "language": "",
                "category": "music" if content_type == "music" else "video",
                "thumbnail_url": thumbnail_url(entry.get("pic")),
            }
        )
    total = data.get("numResults", 0)
    total = total if isinstance(total, int) and not isinstance(total, bool) else 0
    consumed = page * page_size
    next_cursor = (
        f"{page + 1}:{page_size}"
        if items and consumed < min(max(total, 0), MAX_RESULT_WINDOW)
        else ""
    )
    return {"items": items, "next_cursor": next_cursor}


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        if not isinstance(raw, dict) or raw.get("operation") != "search":
            raise ValueError("unsupported discovery operation")
        emit({"type": "result", "value": search(raw)})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
