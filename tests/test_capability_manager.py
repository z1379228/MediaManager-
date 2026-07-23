from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from core.plugins.capability_manager import CapabilityManager


def _decode_claims(token: str) -> dict[str, Any]:
    encoded, _signature = token.split(".", 1)
    return json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )


def _sign_claims(secret: bytes, claims: dict[str, Any]) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode()
    ).rstrip(b"=")
    signature = hmac.new(secret, payload, hashlib.sha256).digest()
    return (
        f"{payload.decode()}."
        f"{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"
    )


def test_capability_token_rejects_signed_unknown_claim() -> None:
    secret = b"k" * 32
    manager = CapabilityManager(secret)
    original = manager.issue("example.plugin", 321, ("media.read",))
    claims = _decode_claims(original)
    claims["unexpected_privileged_claim"] = True
    token = _sign_claims(secret, claims)
    with manager._active_tokens_lock:
        manager._active_tokens[token] = int(claims["expires_at"])

    assert manager.verify(
        token,
        plugin_id="example.plugin",
        process_id=321,
        capability="media.read",
    ) is None


def test_capability_token_still_accepts_exact_issued_claims() -> None:
    manager = CapabilityManager(b"k" * 32)
    token = manager.issue("example.plugin", 321, ("media.read",))

    claims = manager.verify(
        token,
        plugin_id="example.plugin",
        process_id=321,
        capability="media.read",
    )

    assert claims is not None
    assert claims.capabilities == ("media.read",)


def test_capability_token_rejects_payload_tampering_without_valid_signature(
) -> None:
    manager = CapabilityManager(b"k" * 32)
    token = manager.issue("example.plugin", 321, ("media.read",))
    encoded, signature = token.split(".", 1)
    claims = _decode_claims(token)
    claims["plugin_id"] = "attacker.plugin"
    tampered_payload = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    tampered = f"{tampered_payload}.{signature}"
    assert tampered_payload != encoded

    assert manager.verify(
        tampered,
        plugin_id="attacker.plugin",
        process_id=321,
        capability="media.read",
    ) is None
