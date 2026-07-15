"""List public official AniGamer episodes without touching media streams."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import sys
from typing import Any
from urllib import parse, request


ANI_GAMER_ORIGIN = "https://ani.gamer.com.tw"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_EPISODES = 2_000
_SERIES_PATH = re.compile(r"/animeRef\.php\?sn=([0-9]{1,10})")
_EPISODE_PATH = re.compile(r"/animeVideo\.php\?sn=([0-9]{1,10})")
_TITLE_SUFFIX = re.compile(r"\s*\[[^\]]{1,20}\]\s*線上看\s*-\s*巴哈姆特動畫瘋\s*$")


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
        if not is_official_page_url(absolute):
            raise ValueError("AniGamer episode redirect left the official site")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _canonical_page(value: str) -> tuple[str, str] | None:
    try:
        parsed = parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != "ani.gamer.com.tw"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        return None
    path_with_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    match = _SERIES_PATH.fullmatch(path_with_query) or _EPISODE_PATH.fullmatch(
        path_with_query
    )
    if match is None:
        return None
    page = "animeRef.php" if parsed.path == "/animeRef.php" else "animeVideo.php"
    serial = match.group(1)
    return f"{ANI_GAMER_ORIGIN}/{page}?sn={serial}", serial


def is_official_page_url(value: str) -> bool:
    return _canonical_page(value) is not None


def safe_episode_url(value: str, base_url: str) -> tuple[str, str] | None:
    absolute = parse.urljoin(base_url, value)
    canonical = _canonical_page(absolute)
    if canonical is None or "/animeVideo.php?" not in canonical[0]:
        return None
    return canonical


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


class EpisodeParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.page_title_parts: list[str] = []
        self.in_title = False
        self.season_depth = 0
        self.current_episode: tuple[str, str] | None = None
        self.current_label_parts: list[str] = []
        self.episodes: list[tuple[str, str, str]] = []
        self.thumbnail = ""

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = self._attrs(attrs)
        classes = set(values.get("class", "").split())
        if tag == "title":
            self.in_title = True
        if tag == "section":
            if self.season_depth:
                self.season_depth += 1
            elif "season" in classes:
                self.season_depth = 1
        elif self.season_depth and tag == "a" and len(self.episodes) < MAX_EPISODES:
            episode = safe_episode_url(values.get("href", ""), self.base_url)
            data_serial = values.get("data-ani-video-sn", "")
            if episode is not None and (not data_serial or data_serial == episode[1]):
                self.current_episode = episode
                self.current_label_parts = []
        elif tag == "img" and not self.thumbnail:
            alt = " ".join(values.get("alt", "").split())
            candidate = safe_thumbnail(
                values.get("data-src", "") or values.get("src", "")
            )
            if alt and candidate and "/B/ACG/" in candidate:
                self.thumbnail = candidate

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.page_title_parts.append(data)
        if self.current_episode is not None:
            self.current_label_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "a" and self.current_episode is not None:
            label = " ".join("".join(self.current_label_parts).split())[:80]
            url, serial = self.current_episode
            if label and not any(existing[1] == serial for existing in self.episodes):
                self.episodes.append((url, serial, label))
            self.current_episode = None
            self.current_label_parts = []
        elif tag == "section" and self.season_depth:
            self.season_depth -= 1

    @property
    def series_title(self) -> str:
        raw = " ".join("".join(self.page_title_parts).split())[:500]
        title = _TITLE_SUFFIX.sub("", raw).strip()
        return title[:300] or "動畫瘋作品"


def fetch_html(page_url: str) -> tuple[str, str]:
    canonical = _canonical_page(page_url)
    if canonical is None:
        raise ValueError("AniGamer series URL is invalid")
    outgoing = request.Request(
        canonical[0],
        headers={
            "Accept": "text/html",
            "User-Agent": "MediaManager/11 AniGamerOfficialEpisodeGuide",
        },
    )
    opener = request.build_opener(_OfficialRedirectHandler())
    with opener.open(outgoing, timeout=20) as response:
        final_url = response.geturl()
        if not is_official_page_url(final_url):
            raise ValueError("AniGamer episode page redirected outside the official site")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("AniGamer episode response is too large")
    return final_url, payload.decode("utf-8", errors="replace")


def _cursor_offset(value: object) -> int:
    if value in {None, ""}:
        return 0
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError("AniGamer episode cursor is invalid")
    offset = int(value)
    if not 0 <= offset <= MAX_EPISODES:
        raise ValueError("AniGamer episode cursor is invalid")
    return offset


def search(raw_request: dict[str, Any]) -> dict[str, Any]:
    query = " ".join(str(raw_request.get("query", "")).split())
    if not 1 <= len(query) <= 200 or _canonical_page(query) is None:
        raise ValueError("AniGamer series URL is invalid")
    if raw_request.get("content_type", "video") != "video":
        raise ValueError("AniGamer episode content type is invalid")
    limit = max(1, min(int(raw_request.get("limit", 20)), 50))
    offset = _cursor_offset(raw_request.get("cursor", ""))
    emit({"type": "progress", "title": "Reading AniGamer official episode list"})
    final_url, html = fetch_html(query)
    parser = EpisodeParser(final_url)
    parser.feed(html)
    parser.close()
    page = parser.episodes[offset : offset + limit]
    items = [
        {
            "video_id": f"ani-episode-{serial}",
            "url": url,
            "title": f"{parser.series_title} [{label}]",
            "artist": "動畫瘋官方集數",
            "duration": None,
            "language": "",
            "category": "video",
            "thumbnail_url": parser.thumbnail,
        }
        for url, serial, label in page
    ]
    next_offset = offset + len(page)
    return {
        "items": items,
        "next_cursor": str(next_offset) if next_offset < len(parser.episodes) else "",
    }


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
