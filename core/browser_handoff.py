"""Bounded, user-initiated browser-to-application URL handoff contract."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit

from core.site_routing import classify_site_url


HANDOFF_SCHEME = "mediamanager"
HANDOFF_ACTION = "add"
MAX_HANDOFF_CHARS = 8192
MAX_HANDOFF_TITLE_CHARS = 120


@dataclass(frozen=True, slots=True)
class BrowserHandoff:
    url: str
    title: str
    site_family: str

    def to_payload(self) -> dict[str, str]:
        """Return the trusted UI event payload without starting a download."""

        return {
            "url": self.url,
            "title": self.title,
            "provider_id": "browser-handoff",
        }


def _normalize_title(value: object) -> str:
    if not isinstance(value, str):
        return "瀏覽器交付"
    title = " ".join(value.split())[:MAX_HANDOFF_TITLE_CHARS]
    return title or "瀏覽器交付"


def _validate_download_url(value: str) -> tuple[str, str]:
    url = value.strip()
    route = classify_site_url(url)
    if route is None or route.download_provider_id is None:
        raise ValueError("browser handoff URL is not a supported download page")
    return url, route.site_family


def parse_browser_handoff(value: object) -> BrowserHandoff:
    """Validate a direct HTTPS URL or ``mediamanager://add`` handoff URI."""

    if not isinstance(value, str) or not value or len(value) > MAX_HANDOFF_CHARS:
        raise ValueError("browser handoff is empty or too long")
    if "\r" in value or "\n" in value or "\0" in value:
        raise ValueError("browser handoff contains invalid control characters")

    parsed = urlsplit(value)
    if parsed.scheme.casefold() == "https":
        url, site_family = _validate_download_url(value)
        return BrowserHandoff(url, "瀏覽器交付", site_family)

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("browser handoff authority is invalid") from error
    if (
        parsed.scheme.casefold() != HANDOFF_SCHEME
        or parsed.hostname is None
        or parsed.hostname.casefold() != HANDOFF_ACTION
        or parsed.path not in {"", "/"}
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise ValueError("browser handoff action is invalid")
    try:
        fields = parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=3,
        )
    except ValueError as error:
        raise ValueError("browser handoff query is invalid") from error
    values: dict[str, list[str]] = {}
    for key, item in fields:
        values.setdefault(key, []).append(item)
    if (
        set(values) - {"url", "title"}
        or len(values.get("url", ())) != 1
        or len(values.get("title", ())) > 1
    ):
        raise ValueError("browser handoff query fields are invalid")

    url, site_family = _validate_download_url(values["url"][0])
    title = _normalize_title((values.get("title") or [""])[0])
    return BrowserHandoff(url, title, site_family)


def build_browser_handoff_uri(url: str, *, title: str = "") -> str:
    """Build a protocol URI after applying the same trust boundary as parsing."""

    normalized_url, _site_family = _validate_download_url(url)
    fields = {"url": normalized_url}
    normalized_title = _normalize_title(title)
    if title.strip():
        fields["title"] = normalized_title
    value = f"{HANDOFF_SCHEME}://{HANDOFF_ACTION}?{urlencode(fields)}"
    if len(value) > MAX_HANDOFF_CHARS:
        raise ValueError("browser handoff is too long")
    return value
