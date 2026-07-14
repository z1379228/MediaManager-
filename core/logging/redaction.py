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
_PAIR = re.compile(rf"(?i)({_NAMES})(\s*[:=]\s*)([^\s,;&]+)")
_URL_SECRET = re.compile(rf"(?i)([?&](?:{_NAMES})=)([^&#\s]+)")
_MEGA_FRAGMENT = re.compile(
    r"(?i)(https://(?:www\.)?mega\.nz/(?:file|folder)/[A-Za-z0-9_-]{6,64})"
    r"#[A-Za-z0-9_-]{16,128}"
)
_WINDOWS_USER = re.compile(r"(?i)\b([A-Z]:\\Users\\)[^\\/\s]+")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        value = _PAIR.sub(r"\1\2[REDACTED]", value)
        value = _URL_SECRET.sub(r"\1[REDACTED]", value)
        value = _MEGA_FRAGMENT.sub(r"\1#[REDACTED]", value)
        return _WINDOWS_USER.sub(r"\1[USER]", value)
    return value
