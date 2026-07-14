"""Secret redaction for structured and plain-text logs."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = frozenset({"authorization", "cookie", "set-cookie", "access_token", "refresh_token", "api_key", "proxy_password", "signed_url", "oauth_code", "password", "token"})
_PAIR = re.compile(r"(?i)(authorization|cookie|set-cookie|access_token|refresh_token|api_key|proxy_password|signed_url|oauth_code|password|token)(\s*[:=]\s*)([^\s,;&]+)")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _PAIR.sub(r"\1\2[REDACTED]", value)
    return value

