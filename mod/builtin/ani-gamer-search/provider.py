"""User-triggered search of the public official AniGamer catalogue."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import sys
from typing import Any
from urllib import parse, request


SEARCH_URL = "https://ani.gamer.com.tw/search.php"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_RESULT_PATH = re.compile(r"/animeRef\.php\?sn=([0-9]{1,10})")


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
            raise ValueError("AniGamer search redirect is invalid") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "ani.gamer.com.tw"
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
        ):
            raise ValueError("AniGamer search redirect left the official site")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def safe_result_url(value: str) -> tuple[str, str] | None:
    absolute = parse.urljoin(SEARCH_URL, value)
    try:
        parsed = parse.urlsplit(absolute)
        port = parsed.port
    except ValueError:
        return None
    match = _RESULT_PATH.fullmatch(
        f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != "ani.gamer.com.tw"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or match is None
    ):
        return None
    serial = match.group(1)
    return f"https://ani.gamer.com.tw/animeRef.php?sn={serial}", serial


def safe_thumbnail(value: str) -> str:
    try:
        parsed = parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return ""
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme != "https"
        or not host.endswith(".bahamut.com.tw")
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or len(value) > 1000
    ):
        return ""
    return value


class AniSearchParser(HTMLParser):
    def __init__(self, limit: int) -> None:
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.items: list[dict[str, Any]] = []
        self.current: dict[str, str] | None = None
        self.in_title = False
        self.title_parts: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = self._attrs(attrs)
        classes = set(values.get("class", "").split())
        if tag == "a" and "theme-list-main" in classes and len(self.items) < self.limit:
            result = safe_result_url(values.get("href", ""))
            self.current = (
                {"url": result[0], "serial": result[1], "title": "", "thumbnail": ""}
                if result is not None
                else None
            )
        elif self.current is not None and tag == "img" and "theme-img" in classes:
            self.current["title"] = " ".join(values.get("alt", "").split())[:300]
            self.current["thumbnail"] = safe_thumbnail(values.get("data-src", ""))
        elif self.current is not None and tag == "p" and "theme-name" in classes:
            self.in_title = True
            self.title_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self.in_title:
            self.in_title = False
            title = " ".join("".join(self.title_parts).split())[:300]
            if self.current is not None and title:
                self.current["title"] = title
        elif tag == "a" and self.current is not None:
            if self.current["title"] and len(self.items) < self.limit:
                self.items.append(
                    {
                        "video_id": f"ani-{self.current['serial']}",
                        "url": self.current["url"],
                        "title": self.current["title"],
                        "artist": "巴哈姆特動畫瘋",
                        "duration": None,
                        "language": "",
                        "category": "video",
                        "thumbnail_url": self.current["thumbnail"],
                    }
                )
            self.current = None
            self.in_title = False


def fetch_html(query: str) -> str:
    url = f"{SEARCH_URL}?{parse.urlencode({'keyword': query})}"
    search_request = request.Request(
        url,
        headers={
            "Accept": "text/html",
            "User-Agent": "MediaManager/9 AniGamerOfficialSearch",
        },
    )
    opener = request.build_opener(_OfficialRedirectHandler())
    with opener.open(search_request, timeout=20) as response:
        final = parse.urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != "ani.gamer.com.tw":
            raise ValueError("AniGamer search redirected outside the official site")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("AniGamer search response is too large")
    return payload.decode("utf-8", errors="replace")


def search(raw_request: dict[str, Any]) -> dict[str, Any]:
    query = " ".join(str(raw_request.get("query", "")).split())
    if not 1 <= len(query) <= 200:
        raise ValueError("AniGamer search query length is invalid")
    if raw_request.get("cursor", ""):
        raise ValueError("AniGamer search does not support pagination")
    if raw_request.get("content_type", "all") not in {"all", "video"}:
        raise ValueError("AniGamer search content type is invalid")
    limit = max(1, min(int(raw_request.get("limit", 12)), 50))
    emit({"type": "progress", "title": "Searching AniGamer official catalogue"})
    parser = AniSearchParser(limit)
    parser.feed(fetch_html(query))
    parser.close()
    return {"items": parser.items, "next_cursor": ""}


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
