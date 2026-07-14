from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.security.integrity_verifier import IntegrityVerifier
from tools.sign_release import sign_release


def public_text(private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")


def test_release_signing_round_trip_and_tamper_detection(tmp_path) -> None:
    target = tmp_path / "MediaManager.exe"
    target.write_bytes(b"release")
    private_key = Ed25519PrivateKey.generate()
    public_key = public_text(private_key)
    manifest, _ = sign_release(
        tmp_path,
        private_key,
        key_id="release-test",
        expected_public_key=public_key,
        files=("MediaManager.exe",),
    )
    verifier = IntegrityVerifier(
        tmp_path,
        public_key=public_key,
        key_id="release-test",
    )
    assert verifier.verify(manifest).valid
    target.write_bytes(b"tampered")
    assert verifier.verify(manifest).errors == ("hash mismatch: MediaManager.exe",)


def test_release_signer_rejects_wrong_private_key(tmp_path) -> None:
    (tmp_path / "MediaManager.exe").write_bytes(b"release")
    with pytest.raises(ValueError, match="does not match"):
        sign_release(
            tmp_path,
            Ed25519PrivateKey.generate(),
            key_id="release-test",
            expected_public_key=public_text(Ed25519PrivateKey.generate()),
            files=("MediaManager.exe",),
        )


def test_release_signer_rejects_path_escape(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError, match="unsafe release path"):
        sign_release(
            tmp_path,
            private_key,
            key_id="release-test",
            expected_public_key=public_text(private_key),
            files=("../outside.exe",),
        )
