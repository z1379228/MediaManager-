"""Explicit HTTPS direct-file downloader with no website extraction."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PROVIDER_ID = "direct-http"
DISPLAY_NAME = "Direct HTTP"
MAX_FILE_BYTES = 64 * 1024**3
_SUFFIXES = frozenset(
    {
        ".7z", ".bz2", ".csv", ".epub", ".flac", ".gz", ".iso",
        ".jpg", ".jpeg", ".m4a", ".mkv", ".mov", ".mp3", ".mp4",
        ".ogg", ".opus", ".pdf", ".png", ".rar", ".tar", ".tgz",
        ".txt", ".wav", ".webm", ".webp", ".xz", ".zip",
    }
)
_SITE_DOMAINS = frozenset(
    {
        "youtube.com", "youtu.be", "youtube-nocookie.com", "bilibili.com",
        "b23.tv", "gamer.com.tw", "facebook.com", "fb.watch",
        "instagram.com", "threads.com", "threads.net", "x.com", "twitter.com",
        "mega.nz", "mega.io",
        "vimeo.com", "dailymotion.com", "dai.ly", "soundcloud.com",
        "tiktok.com", "twitch.tv",
    }
)
_UNSAFE_FILENAME = frozenset('<>:"/\\|?*')


def emit(message: dict[str, Any]) -> None:
    sys.stdout.buffer.write(
        (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    )
    sys.stdout.buffer.flush()


def _site_owned(host: str) -> bool:
    return any(
        host == domain or host.endswith(f".{domain}") for domain in _SITE_DOMAINS
    )


def _global_host(host: str) -> None:
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        try:
            resolved = socket.getaddrinfo(
                host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
        except OSError as error:
            raise ValueError("direct-file host could not be resolved") from error
        addresses = {
            ipaddress.ip_address(item[4][0].split("%", 1)[0]) for item in resolved
        }
    else:
        addresses = {literal}
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("direct-file host resolves to a non-public address")


def _validated_url(value: object, *, resolve: bool = True) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        raise ValueError("direct-file URL is invalid")
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").casefold()
        port = parsed.port
    except ValueError as error:
        raise ValueError("direct-file URL is malformed") from error
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or len(parsed.query) > 2000
        or _site_owned(host)
        or not any(unquote(parsed.path).casefold().endswith(s) for s in _SUFFIXES)
    ):
        raise ValueError("URL is not an explicit supported HTTPS file")
    if resolve:
        _global_host(host)
    return value


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        absolute = _validated_url(urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def _content_length(headers: object) -> int | None:
    value = headers.get("Content-Length")
    if value is None:
        return None
    try:
        size = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("direct-file content length is invalid") from error
    if not 0 <= size <= MAX_FILE_BYTES:
        raise ValueError("direct-file content length exceeds the 64 GiB limit")
    return size


def _safe_filename(value: object) -> str:
    filename = " ".join(Path(unquote(str(value or ""))).name.split())
    filename = "".join(
        "_" if character in _UNSAFE_FILENAME or ord(character) < 32 else character
        for character in filename
    )
    if not filename or filename[-1] in " ." or len(filename) > 180:
        raise ValueError("direct-file output filename is invalid")
    if not any(filename.casefold().endswith(suffix) for suffix in _SUFFIXES):
        raise ValueError("direct-file output filename has an unsupported suffix")
    return filename


def _response_filename(response: object, url: str) -> str:
    disclosed = response.headers.get_filename()
    for candidate in (disclosed, Path(unquote(urlsplit(url).path)).name):
        try:
            return _safe_filename(candidate)
        except ValueError:
            continue
    raise ValueError("direct-file server did not disclose a safe filename")


def _open_for_analysis(url: str) -> object:
    opener = build_opener(_SafeRedirectHandler())
    request = Request(
        url,
        method="HEAD",
        headers={"Accept-Encoding": "identity", "User-Agent": "MediaManager/12"},
    )
    try:
        return opener.open(request, timeout=30)
    except HTTPError as error:
        if error.code not in {405, 501}:
            raise
    request = Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "Range": "bytes=0-0",
            "User-Agent": "MediaManager/12",
        },
    )
    return opener.open(request, timeout=30)


def analyze(request: dict[str, Any]) -> dict[str, Any]:
    url = _validated_url(request.get("url"))
    with _open_for_analysis(url) as response:
        final_url = _validated_url(response.geturl())
        size = _content_length(response.headers)
        filename = _response_filename(response, final_url)
        content_type = str(response.headers.get_content_type() or "")[:100]
    return {
        "id": hashlib.sha256(url.encode("utf-8")).hexdigest()[:24],
        "title": filename,
        "duration": None,
        "uploader": urlsplit(final_url).hostname or "",
        "webpage_url": final_url,
        "thumbnail": "",
        "content_kind": "direct-file",
        "expected_bytes": size,
        "content_type": content_type,
        "chapters": [],
        "formats": [],
        "audio_languages": [],
        "subtitle_languages": [],
    }


def _expected_sha256(request: dict[str, Any]) -> str:
    options = request.get("provider_options", {})
    if not isinstance(options, dict) or set(options) - {"expected_sha256"}:
        raise ValueError("direct-file provider options are invalid")
    value = str(options.get("expected_sha256") or "").casefold()
    if value and not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("expected SHA-256 is invalid")
    return value


def download(request: dict[str, Any]) -> str:
    url = _validated_url(request.get("url"))
    expected_sha256 = _expected_sha256(request)
    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("direct-file output directory is unsafe")
    requested_name = str(request.get("output_filename") or "")
    fallback_name = _safe_filename(Path(unquote(urlsplit(url).path)).name)
    filename = _safe_filename(requested_name) if requested_name else fallback_name
    target = (output / filename).resolve()
    if not target.is_relative_to(output) or target.exists():
        raise ValueError("direct-file output path is already in use")
    partial = output / f".{filename}.part"
    if partial.is_symlink() or (partial.exists() and not partial.is_file()):
        raise ValueError("direct-file partial output is unsafe")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > MAX_FILE_BYTES:
        raise ValueError("direct-file partial output exceeds the safety limit")
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "MediaManager/12",
    }
    if offset:
        headers["Range"] = f"bytes={offset}-"
    opener = build_opener(_SafeRedirectHandler())
    response = opener.open(Request(url, headers=headers), timeout=30)
    with response:
        _validated_url(response.geturl())
        status = int(getattr(response, "status", 200))
        append = bool(offset and status == 206)
        if not append:
            offset = 0
        remaining = _content_length(response.headers)
        expected_total = offset + remaining if remaining is not None else None
        if expected_total is not None and expected_total > MAX_FILE_BYTES:
            raise ValueError("direct-file output exceeds the 64 GiB limit")
        digest = hashlib.sha256()
        if append:
            with partial.open("rb") as existing:
                while chunk := existing.read(1024 * 1024):
                    digest.update(chunk)
        mode = "ab" if append else "wb"
        downloaded = offset
        with partial.open(mode) as destination:
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_FILE_BYTES:
                    raise ValueError("direct-file output exceeds the 64 GiB limit")
                destination.write(chunk)
                digest.update(chunk)
                emit(
                    {
                        "type": "progress",
                        "title": filename,
                        "downloaded_bytes": downloaded,
                        "total_bytes": expected_total,
                        "speed": "",
                        "eta": "",
                    }
                )
    if expected_sha256 and digest.hexdigest() != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ValueError("downloaded file SHA-256 does not match the expected value")
    if not partial.is_file() or partial.stat().st_size <= 0:
        raise ValueError("direct-file download produced an empty output")
    partial.replace(target)
    return str(target)


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "analyze":
            emit({"type": "result", "value": analyze(raw)})
        elif operation == "download":
            emit({"type": "result", "value": download(raw)})
        else:
            raise ValueError("unsupported provider operation")
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
