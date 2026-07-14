"""Ed25519 signature verification with strict, explicit encodings."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


@dataclass(frozen=True, slots=True)
class SignatureResult:
    valid: bool
    reason: str


class SignatureVerifier:
    """Verify raw or base64 Ed25519 signatures against base64 public keys."""

    def verify(self, payload: bytes, signature: bytes, public_key: str) -> SignatureResult:
        try:
            key_bytes = self._decode_text(public_key)
            signature_bytes = self._decode_signature(signature)
            if len(key_bytes) != 32:
                return SignatureResult(False, "Ed25519 public key must be 32 bytes")
            if len(signature_bytes) != 64:
                return SignatureResult(False, "Ed25519 signature must be 64 bytes")
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature_bytes,
                payload,
            )
            return SignatureResult(True, "Ed25519 signature is valid")
        except InvalidSignature:
            return SignatureResult(False, "Ed25519 signature does not match")
        except (UnicodeDecodeError, ValueError, binascii.Error) as error:
            return SignatureResult(False, f"invalid Ed25519 encoding: {error}")

    @staticmethod
    def _decode_text(value: str) -> bytes:
        encoded = value.removeprefix("ed25519:").strip()
        return base64.b64decode(encoded, validate=True)

    @classmethod
    def _decode_signature(cls, value: bytes) -> bytes:
        if len(value) == 64:
            return value
        return cls._decode_text(value.decode("ascii"))