"""Secret redaction for structured and plain-text logs."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "access_token",
        "refresh_token",
        "api_key",
        "proxy_password",
        "signed_url",
        "oauth_code",
        "password",
        "token",
    }
)
_NAMES = "|".join(re.escape(name) for name in sorted(SENSITIVE_KEYS))
_AUTHORIZATION = re.compile(
    r"(?im)(?<![A-Za-z0-9_])"
    r"(?P<key_quote>[\"']?)(?P<key>authorization)(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)[^\r\n]*"
)
_COOKIE_HEADER = re.compile(
    r"(?im)(?<![A-Za-z0-9_])"
    r"(?P<key_quote>[\"']?)(?P<key>(?:set-)?cookie)(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)[^\r\n]*"
)
_QUOTED_PAIR = re.compile(
    rf"(?i)(?<![A-Za-z0-9_])"
    rf"(?P<key_quote>[\"']?)(?P<key>{_NAMES})(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<value_quote>[\"'])(?:\\.|[^\\\r\n])*?(?P=value_quote)"
)
_PAIR = re.compile(
    rf"(?i)(?<![A-Za-z0-9_])"
    rf"(?P<key_quote>[\"']?)(?P<key>{_NAMES})(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)(?P<value>(?![\"'])[^\s,;&}\]]+)"
)
_URL_USERINFO = re.compile(
    r"(?i)\b(?P<scheme>https?://)(?P<userinfo>[^/?#\s@]+)@"
)
_URL_SECRET = re.compile(rf"(?i)([?&](?:{_NAMES})=)([^&#\s]+)")
_MEGA_FRAGMENT = re.compile(
    r"(?i)(https://(?:www\.)?mega\.nz/(?:file|folder)/[A-Za-z0-9_-]{6,64})"
    r"#[A-Za-z0-9_-]{16,128}"
)
_DIAGNOSTIC_FIELD_NAMES = (
    "artifact_sha256|exit_code|faulting_module|faulting_offset|module|phase|"
    "reader_complete|stdout_reader_complete"
)
_PATH_BOUNDARY = (
    rf"(?=\s+(?:{_DIAGNOSTIC_FIELD_NAMES})\s*=|[\r\n\t\"'<>|]|$)"
)
_ABSOLUTE_PATH_QUOTED = re.compile(
    r"(?i)(?P<quote>[\"'])(?P<path>"
    r"(?:[A-Z]:[\\/]|\\\\|/(?:home|Users|tmp|var|opt|srv|mnt|media|Volumes)[\\/])"
    r"(?:\\.|[^\r\n])*?)(?P=quote)"
)
_ABSOLUTE_PATH = re.compile(
    rf"(?i)(?<![A-Za-z0-9])(?P<path>"
    rf"(?:[A-Z]:[\\/]|\\\\|/(?:home|Users|tmp|var|opt|srv|mnt|media|Volumes)[\\/])"
    rf"[^\r\n\t\"'<>|]*?){_PATH_BOUNDARY}"
)
_WINDOWS_PRIVATE_ROOT = re.compile(
    r"(?i)^(?P<prefix>[A-Z]:[\\/](?:Users|Profiles)[\\/])"
)
_UNSAFE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BIDI_CONTROL = re.compile(r"[\u202a-\u202e\u2066-\u2069]")
_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _private_user_path(prefix: str) -> str:
    separator = "/" if prefix.endswith("/") else "\\"
    return f"{prefix}[USER]{separator}[PRIVATE_PATH]"


def _redact_quoted_pair(match: re.Match[str]) -> str:
    key_quote = match.group("key_quote")
    key = match.group("key")
    separator = match.group("separator")
    value_quote = match.group("value_quote")
    return (
        f"{key_quote}{key}{key_quote}{separator}"
        f"{value_quote}[REDACTED]{value_quote}"
    )


def _redact_header(match: re.Match[str]) -> str:
    key_quote = match.group("key_quote")
    return (
        f"{key_quote}{match.group('key')}{key_quote}"
        f"{match.group('separator')}[REDACTED]"
    )


def _redact_bare_pair(match: re.Match[str]) -> str:
    return _redact_header(match)


def _private_path(path: str) -> str:
    user_root = _WINDOWS_PRIVATE_ROOT.match(path)
    if user_root is not None:
        return _private_user_path(user_root.group("prefix"))
    return "[PRIVATE_PATH]"


def _redact_quoted_path(match: re.Match[str]) -> str:
    quote = match.group("quote")
    return f"{quote}{_private_path(match.group('path'))}{quote}"


def _redact_path(match: re.Match[str]) -> str:
    return _private_path(match.group("path"))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        value = _URL_USERINFO.sub(r"\g<scheme>[REDACTED]@", value)
        value = _AUTHORIZATION.sub(_redact_header, value)
        value = _COOKIE_HEADER.sub(_redact_header, value)
        value = _QUOTED_PAIR.sub(_redact_quoted_pair, value)
        value = _PAIR.sub(_redact_bare_pair, value)
        value = _URL_SECRET.sub(r"\1[REDACTED]", value)
        value = _MEGA_FRAGMENT.sub(r"\1#[REDACTED]", value)
        value = _ABSOLUTE_PATH_QUOTED.sub(_redact_quoted_path, value)
        return _ABSOLUTE_PATH.sub(_redact_path, value)
    return value


def bounded_redacted_text(value: Any, *, max_utf8_bytes: int = 240) -> str:
    """Redact first, then return valid UTF-8 within an explicit byte budget."""

    if type(max_utf8_bytes) is not int or max_utf8_bytes < 1:
        raise ValueError("max_utf8_bytes must be a positive integer")
    sanitized = str(redact(str(redact(value))))
    sanitized = _UNSAFE_CONTROL.sub("�", sanitized)
    sanitized = _BIDI_CONTROL.sub("", sanitized)
    sanitized = _SURROGATE.sub("\ufffd", sanitized)
    encoded = sanitized.encode("utf-8")
    if len(encoded) <= max_utf8_bytes:
        return sanitized
    marker = "[diagnostic truncated]"
    marker_bytes = marker.encode("utf-8")
    if len(marker_bytes) >= max_utf8_bytes:
        return marker_bytes[:max_utf8_bytes].decode("utf-8", errors="ignore")
    prefix_bytes = encoded[: max_utf8_bytes - len(marker_bytes)]
    prefix = prefix_bytes.decode("utf-8", errors="ignore")
    return f"{prefix}{marker}"
