from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.security.signature_verifier import SignatureVerifier


def key_pair() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return private_key, "ed25519:" + base64.b64encode(public_bytes).decode("ascii")


def test_accepts_raw_ed25519_signature() -> None:
    private_key, public_key = key_pair()
    payload = b"signed plugin manifest"
    result = SignatureVerifier().verify(payload, private_key.sign(payload), public_key)
    assert result.valid


def test_accepts_base64_ed25519_signature() -> None:
    private_key, public_key = key_pair()
    payload = b"signed plugin manifest"
    signature = base64.b64encode(private_key.sign(payload))
    result = SignatureVerifier().verify(payload, signature, public_key)
    assert result.valid


def test_rejects_modified_payload() -> None:
    private_key, public_key = key_pair()
    signature = private_key.sign(b"original")
    result = SignatureVerifier().verify(b"modified", signature, public_key)
    assert not result.valid
    assert result.reason == "Ed25519 signature does not match"


def test_rejects_malformed_key_without_raising() -> None:
    result = SignatureVerifier().verify(b"payload", b"x" * 64, "not-base64")
    assert not result.valid
    assert result.reason.startswith("invalid Ed25519 encoding:")
