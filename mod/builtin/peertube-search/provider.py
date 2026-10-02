"""Bounded public-video search for a user-selected PeerTube instance."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import sys
from typing import Any
from urllib import parse
from uuid import UUID


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RESULT_WINDOW = 200
MAX_QUERY_LENGTH = 200
REQUEST_TIMEOUT = 20


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _plain_text(value: object, *, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _validated_origin(value: object) -> tuple[str, str]:
    if not isinstance(value, str) or not 1 <= len(value) <= 500:
        raise ValueError("PeerTube instance origin is invalid")
    raw = value.strip()
    if any(character.isspace() for character in raw) or any(
        character in raw for character in ('"', "'", "\\")
    ):
        raise ValueError("PeerTube instance origin is invalid")
    try:
        parsed = parse.urlsplit(raw)
        port = parsed.port
    except (TypeError, ValueError) as error:
        raise ValueError("PeerTube instance origin is invalid") from error
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or host.endswith(".")
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("PeerTube instance must be an HTTPS origin without a path")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("PeerTube instance hostname is invalid") from error
    if not 1 <= len(ascii_host) <= 253 or "%" in ascii_host:
        raise ValueError("PeerTube instance hostname is invalid")
    try:
        address_literal = ipaddress.ip_address(ascii_host)
    except ValueError:
        origin_host = ascii_host
    else:
        if not address_literal.is_global:
            raise ValueError("PeerTube instance hostname is non-public")
        origin_host = (
            f"[{address_literal.compressed}]"
            if address_literal.version == 6
            else address_literal.compressed
        )
        ascii_host = address_literal.compressed
    return f"https://{origin_host}", ascii_host


def _public_addresses(host: str) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(
            host,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except OSError as error:
        raise ConnectionError("PeerTube instance hostname could not be resolved") from error
    addresses: list[str] = []
    for record in records:
        address = str(record[4][0])
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as error:
            raise ValueError("PeerTube instance resolved to an invalid address") from error
        if not parsed.is_global:
            raise ValueError("PeerTube instance resolved to a non-public address")
        normalized = parsed.compressed
        if normalized not in addresses:
            addresses.append(normalized)
    if not addresses:
        raise ConnectionError("PeerTube instance hostname returned no addresses")
    return tuple(addresses)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a validated address while retaining hostname TLS checks."""

    def __init__(self, host: str, address: str) -> None:
        super().__init__(
            host,
            port=443,
            timeout=REQUEST_TIMEOUT,
            context=ssl.create_default_context(),
        )
        self._pinned_address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._pinned_address, 443),
            self.timeout,
            self.source_address,
        )
        try:
            raw_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except Exception:
            raw_socket.close()
            raise


def _request_json(host: str, address: str, target: str) -> dict[str, Any]:
    connection = _PinnedHTTPSConnection(host, address)
    try:
        connection.request(
            "GET",
            target,
            headers={
                "Accept": "application/json",
                "User-Agent": "MediaManager/39 PeerTubeSearch",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise ValueError("PeerTube API redirects are not followed")
        if response.status == 429:
            raise RuntimeError("PeerTube instance temporarily rate-limited the search")
        if response.status != 200:
            raise RuntimeError(f"PeerTube search failed with HTTP {response.status}")
        content_type = str(response.getheader("Content-Type") or "").casefold()
        if content_type and not content_type.startswith("application/json"):
            raise ValueError("PeerTube search returned a non-JSON response")
        length_header = response.getheader("Content-Length")
        if length_header:
            try:
                declared_length = int(length_header)
            except ValueError as error:
                raise ValueError("PeerTube response length is invalid") from error
            if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
                raise ValueError("PeerTube search response is too large")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    finally:
        connection.close()
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("PeerTube search response is too large")
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise ValueError("PeerTube search returned invalid JSON") from error
    if not isinstance(result, dict):
        raise ValueError("PeerTube search response is invalid")
    return result


def _cursor_offset(value: object, page_size: int) -> int:
    if value in {None, ""}:
        return 0
    if not isinstance(value, str):
        raise ValueError("PeerTube search cursor is invalid")
    offset_text, separator, size_text = value.partition(":")
    if (
        separator != ":"
        or not offset_text.isascii()
        or not offset_text.isdigit()
        or not size_text.isascii()
        or not size_text.isdigit()
        or int(size_text) != page_size
    ):
        raise ValueError("PeerTube search cursor is invalid")
    offset = int(offset_text)
    if offset < 0 or offset >= MAX_RESULT_WINDOW:
        raise ValueError("PeerTube search cursor is outside the bounded result window")
    return offset


def _uuid_text(value: object) -> str:
    try:
        parsed = UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return ""
    return str(parsed) if parsed.version == 4 else ""


def _constant_id(value: object) -> object:
    return value.get("id") if isinstance(value, dict) else None


def _duration(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= 86400 else None


def _language(value: object) -> str:
    identifier = _constant_id(value)
    return _plain_text(identifier, limit=32) if isinstance(identifier, str) else ""


def _artist(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return _plain_text(value.get("displayName") or value.get("name"), limit=200)


def _video_item(entry: object, origin: str, content_type: str) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    video_id = _uuid_text(entry.get("uuid"))
    title = _plain_text(entry.get("name"), limit=300)
    if (
        not video_id
        or not title
        or entry.get("isLocal") is not True
        or entry.get("nsfw") is True
        or (entry.get("privacy") is not None and _constant_id(entry["privacy"]) != 1)
        or (entry.get("state") is not None and _constant_id(entry["state"]) != 1)
    ):
        return None
    is_live = entry.get("isLive") is True
    if content_type == "live" and not is_live:
        return None
    return {
        "video_id": video_id,
        "url": f"{origin}/videos/watch/{video_id}",
        "title": title,
        "artist": _artist(entry.get("channel")),
        "duration": _duration(entry.get("duration")),
        "language": _language(entry.get("language")),
        "category": "live" if is_live else "video",
        # Avoid an implicit second request to a user-selected host. Opening the
        # result remains an explicit browser action by the user.
        "thumbnail_url": "",
    }


def search(raw_request: dict[str, Any]) -> dict[str, Any]:
    query = " ".join(str(raw_request.get("query", "")).split())
    if not 1 <= len(query) <= MAX_QUERY_LENGTH:
        raise ValueError("PeerTube search query length is invalid")
    parsed_query = parse.urlsplit(query)
    if parsed_query.scheme or parsed_query.netloc:
        raise ValueError("PeerTube search accepts text keywords, not a URL")
    content_type = raw_request.get("content_type", "all")
    if content_type not in {"all", "video", "live"}:
        raise ValueError("PeerTube search content type is invalid")
    page_size = max(1, min(int(raw_request.get("limit", 12)), 50))
    offset = _cursor_offset(raw_request.get("cursor", ""), page_size)
    origin, host = _validated_origin(raw_request.get("source_scope", ""))
    addresses = _public_addresses(host)
    parameters: dict[str, object] = {
        "search": query,
        "searchTarget": "local",
        "isLocal": "true",
        "start": offset,
        "count": page_size,
    }
    if content_type == "live":
        parameters["isLive"] = "true"
    emit({"type": "progress", "title": "Searching PeerTube"})
    target = f"/api/v1/search/videos?{parse.urlencode(parameters)}"
    response = _request_json(host, addresses[0], target)
    entries = response.get("data")
    total = response.get("total")
    if (
        not isinstance(entries, list)
        or len(entries) > page_size
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
    ):
        raise ValueError("PeerTube search response shape is invalid")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        item = _video_item(entry, origin, str(content_type))
        if item is None or item["video_id"] in seen:
            continue
        seen.add(item["video_id"])
        items.append(item)
    consumed = offset + len(entries)
    next_cursor = (
        f"{offset + page_size}:{page_size}"
        if entries
        and len(entries) == page_size
        and consumed < min(total, MAX_RESULT_WINDOW)
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
