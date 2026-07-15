"""Pure, exact-host website-family routing used before MOD selection."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit


YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    }
)
BILIBILI_HOSTS = frozenset(
    {
        "bilibili.com",
        "www.bilibili.com",
        "m.bilibili.com",
        "space.bilibili.com",
        "b23.tv",
    }
)
FACEBOOK_HOSTS = frozenset(
    {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "fb.watch",
    }
)
ANI_GAMER_HOSTS = frozenset({"ani.gamer.com.tw"})


@dataclass(frozen=True, slots=True)
class SiteRoute:
    site_family: str
    resource_kind: str
    download_provider_id: str | None
    search_provider_id: str | None


def _valid_token(value: str, *, minimum: int = 1, maximum: int = 200) -> bool:
    return minimum <= len(value) <= maximum and all(
        character.isascii()
        and (character.isalnum() or character in {"-", "_"})
        for character in value
    )


def _query_values(
    query: str,
) -> dict[str, tuple[str, ...]] | None:
    try:
        fields = parse_qsl(query, keep_blank_values=True, max_num_fields=64)
    except ValueError:
        return None
    values: dict[str, list[str]] = {}
    for raw_key, value in fields:
        key = raw_key.casefold()
        values.setdefault(key, []).append(value)
    if any(len(values.get(key, ())) > 1 for key in ("v", "list", "sn")):
        return None
    return {key: tuple(items) for key, items in values.items()}


def _youtube_route(host: str, path: str, query: str) -> SiteRoute | None:
    values = _query_values(query)
    if values is None:
        return None
    video_id = (values.get("v") or ("",))[0]
    playlist_id = (values.get("list") or ("",))[0]
    if host == "youtu.be":
        parts = tuple(part for part in path.split("/") if part)
        if len(parts) != 1 or playlist_id or not _valid_token(parts[0], maximum=64):
            return None
        return SiteRoute("youtube", "video", "youtube", "youtube-search")
    if path == "/watch":
        if not _valid_token(video_id, maximum=64):
            return None
        kind = "playlist-context" if playlist_id else "video"
        if playlist_id and not _valid_token(playlist_id, minimum=2):
            return None
        return SiteRoute("youtube", kind, "youtube", "youtube-search")
    if path == "/playlist":
        if video_id or not _valid_token(playlist_id, minimum=2):
            return None
        return SiteRoute("youtube", "playlist", "youtube", "youtube-search")
    parts = tuple(part for part in path.split("/") if part)
    if (
        len(parts) == 2
        and parts[0] in {"embed", "live", "shorts"}
        and not video_id
        and not playlist_id
        and _valid_token(parts[1], maximum=64)
    ):
        return SiteRoute("youtube", "video", "youtube", "youtube-search")
    return None


def _bilibili_route(host: str, path: str) -> SiteRoute | None:
    parts = tuple(part for part in path.split("/") if part)
    if host == "b23.tv" and len(parts) == 1 and _valid_token(parts[0], maximum=64):
        kind = "short-link"
    elif host == "space.bilibili.com" and parts and parts[0].isdigit():
        kind = "creator"
    elif len(parts) >= 2 and parts[0] == "video":
        kind = "video"
    elif len(parts) >= 3 and parts[:2] == ("bangumi", "play"):
        kind = "episode"
    else:
        return None
    return SiteRoute("bilibili", kind, "bilibili", "bilibili-search")


def _facebook_route(host: str, path: str) -> SiteRoute | None:
    parts = tuple(part for part in path.split("/") if part)
    is_media = (
        (host == "fb.watch" and len(parts) == 1)
        or (parts and parts[0] == "watch")
        or (len(parts) == 2 and parts[0] in {"reel", "videos"})
        or (len(parts) >= 3 and parts[-2] == "videos")
    )
    if not is_media:
        return None
    return SiteRoute("facebook", "video-page", "facebook", None)


def _ani_gamer_route(path: str, query: str) -> SiteRoute | None:
    values = _query_values(query)
    if values is None:
        return None
    serial = (values.get("sn") or ("",))[0]
    if not serial.isascii() or not serial.isdigit() or not 1 <= len(serial) <= 16:
        return None
    if path == "/animeRef.php":
        kind = "series"
        download_provider = None
    elif path == "/animeVideo.php":
        kind = "episode"
        download_provider = "ani-gamer-offline"
    else:
        return None
    return SiteRoute(
        "ani-gamer",
        kind,
        download_provider,
        "ani-gamer-search",
    )


def classify_site_url(value: object) -> SiteRoute | None:
    """Classify a bounded canonical media URL without performing network I/O."""

    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 4096
        or any(character in value for character in ('"', "'", "\r", "\n"))
    ):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        return None
    if host in YOUTUBE_HOSTS:
        return _youtube_route(host, parsed.path, parsed.query)
    if host in BILIBILI_HOSTS:
        return _bilibili_route(host, parsed.path)
    if host in FACEBOOK_HOSTS:
        return _facebook_route(host, parsed.path)
    if host in ANI_GAMER_HOSTS:
        return _ani_gamer_route(parsed.path, parsed.query)
    return None
