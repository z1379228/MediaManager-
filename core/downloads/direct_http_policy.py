"""Explicit direct-file URL policy shared by routing and trusted UI."""

from __future__ import annotations

import ipaddress
from urllib.parse import unquote, urlsplit


DIRECT_HTTP_SUFFIXES = frozenset(
    {
        ".7z",
        ".bz2",
        ".csv",
        ".epub",
        ".flac",
        ".gz",
        ".iso",
        ".jpg",
        ".jpeg",
        ".m4a",
        ".mkv",
        ".mov",
        ".mp3",
        ".mp4",
        ".ogg",
        ".opus",
        ".pdf",
        ".png",
        ".rar",
        ".tar",
        ".tgz",
        ".txt",
        ".wav",
        ".webm",
        ".webp",
        ".xz",
        ".zip",
    }
)

# A direct-file MOD must not become a fallback extractor for existing website
# MODs. Subdomains of these official domains remain owned by their site MOD.
SITE_OWNED_DOMAINS = frozenset(
    {
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "bilibili.com",
        "b23.tv",
        "gamer.com.tw",
        "facebook.com",
        "fb.watch",
        "instagram.com",
        "threads.com",
        "threads.net",
        "x.com",
        "twitter.com",
        "mega.nz",
        "mega.io",
        "vimeo.com",
        "dailymotion.com",
        "dai.ly",
        "soundcloud.com",
        "tiktok.com",
        "twitch.tv",
    }
)


def _site_owned(host: str) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in SITE_OWNED_DOMAINS)


def direct_http_url_candidate(value: object) -> bool:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        return False
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").casefold()
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or len(parsed.query) > 2000
        or _site_owned(host)
    ):
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        if not address.is_global:
            return False
    path = unquote(parsed.path).casefold()
    return any(path.endswith(suffix) for suffix in DIRECT_HTTP_SUFFIXES)
