"""Short-lived, process-bound capability tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass

from core.plugins.permission_policy import PermissionPolicy


_CLAIM_FIELDS = frozenset(
    {"plugin_id", "process_id", "capabilities", "expires_at", "nonce"}
)


@dataclass(frozen=True, slots=True)
class CapabilityClaims:
    plugin_id: str
    process_id: int
    capabilities: tuple[str, ...]
    expires_at: int
    nonce: str


class CapabilityManager:
    def __init__(self, secret: bytes | None = None) -> None:
        self._secret = secret or secrets.token_bytes(32)
        self._policy = PermissionPolicy()
        self._active_tokens: dict[str, int] = {}
        self._active_tokens_lock = threading.Lock()

    def issue(self, plugin_id: str, process_id: int, capabilities: tuple[str, ...], *, ttl: int = 300) -> str:
        claims = {"plugin_id": plugin_id, "process_id": process_id, "capabilities": capabilities,
                  "expires_at": int(time.time()) + min(max(ttl, 1), 900), "nonce": secrets.token_urlsafe(16)}
        payload = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).rstrip(b"=")
        signature = hmac.new(self._secret, payload, hashlib.sha256).digest()
        token = f"{payload.decode()}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"
        with self._active_tokens_lock:
            self._remove_expired_locked(int(time.time()))
            self._active_tokens[token] = int(claims["expires_at"])
        return token

    def revoke(self, token: str) -> None:
        """Immediately invalidate one issued process-bound capability token."""

        with self._active_tokens_lock:
            self._active_tokens.pop(token, None)

    def verify(self, token: str, *, plugin_id: str, process_id: int, capability: str) -> CapabilityClaims | None:
        try:
            encoded, signature = token.split(".", 1)
            payload = encoded.encode()
            supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
            expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(supplied, expected):
                return None
            raw = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            if not isinstance(raw, dict) or set(raw) != _CLAIM_FIELDS:
                return None
            claims = CapabilityClaims(raw["plugin_id"], int(raw["process_id"]), tuple(raw["capabilities"]), int(raw["expires_at"]), raw["nonce"])
            now = int(time.time())
            if claims.plugin_id != plugin_id or claims.process_id != process_id or claims.expires_at < now:
                return None
            with self._active_tokens_lock:
                self._remove_expired_locked(now)
                if self._active_tokens.get(token) != claims.expires_at:
                    return None
            return claims if self._policy.allows(claims.capabilities, capability) else None
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _remove_expired_locked(self, now: int) -> None:
        expired = tuple(
            token
            for token, expires_at in self._active_tokens.items()
            if expires_at < now
        )
        for token in expired:
            self._active_tokens.pop(token, None)
