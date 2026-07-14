from __future__ import annotations

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.release_preflight import check_release
from tools.sign_release import sign_release


def _public_text(private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")


def test_preflight_blocks_unconfigured_release_identity(tmp_path) -> None:
    (tmp_path / "MediaManager.exe").write_bytes(b"release")
    result = check_release(
        tmp_path,
        key_id="",
        public_key="",
        files=("MediaManager.exe",),
        builtin_hashes={},
        require_authenticode=False,
    )
    assert not result.ready
    assert result.errors == (
        "compiled release key id or Ed25519 public key is invalid",
    )


def test_preflight_reports_authenticode_even_when_release_identity_is_invalid(
    tmp_path,
) -> None:
    (tmp_path / "MediaManager.exe").write_bytes(b"release")
    result = check_release(
        tmp_path,
        key_id="",
        public_key="",
        files=("MediaManager.exe",),
        builtin_hashes={},
        authenticode_checker=lambda _path: "NotSigned",
    )

    assert not result.ready
    assert result.errors == (
        "compiled release key id or Ed25519 public key is invalid",
        "Authenticode signature is not valid: NotSigned",
    )


def test_preflight_blocks_missing_required_file(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    result = check_release(
        tmp_path,
        key_id="release-test",
        public_key=_public_text(private_key),
        files=("MediaManager.exe",),
        builtin_hashes={},
        require_authenticode=False,
    )
    assert not result.ready
    assert "required release file missing or unsafe: MediaManager.exe" in result.errors
    assert "signed release manifest is missing" in result.errors


def test_preflight_accepts_complete_signed_release(tmp_path) -> None:
    target = tmp_path / "MediaManager.exe"
    target.write_bytes(b"release")
    private_key = Ed25519PrivateKey.generate()
    public_key = _public_text(private_key)
    sign_release(
        tmp_path,
        private_key,
        key_id="release-test",
        expected_public_key=public_key,
        files=("MediaManager.exe",),
    )
    result = check_release(
        tmp_path,
        key_id="release-test",
        public_key=public_key,
        files=("MediaManager.exe",),
        builtin_hashes={},
        require_authenticode=False,
    )
    assert result.ready
    assert result.errors == ()
    assert result.checked == 2


def test_preflight_detects_builtin_mod_hash_mismatch(tmp_path) -> None:
    target = tmp_path / "mod" / "builtin" / "youtube" / "provider.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"provider")
    executable = tmp_path / "MediaManager.exe"
    executable.write_bytes(b"release")
    private_key = Ed25519PrivateKey.generate()
    public_key = _public_text(private_key)
    files = ("MediaManager.exe", "mod/builtin/youtube/provider.py")
    sign_release(
        tmp_path,
        private_key,
        key_id="release-test",
        expected_public_key=public_key,
        files=files,
    )
    result = check_release(
        tmp_path,
        key_id="release-test",
        public_key=public_key,
        files=files,
        builtin_hashes={"youtube": {"provider.py": hashlib.sha256(b"other").hexdigest()}},
        require_authenticode=False,
    )
    assert not result.ready
    assert result.errors == (
        "built-in MOD hash mismatch: mod/builtin/youtube/provider.py",
    )


def test_preflight_requires_valid_authenticode_for_publishable_build(tmp_path) -> None:
    target = tmp_path / "MediaManager.exe"
    target.write_bytes(b"release")
    private_key = Ed25519PrivateKey.generate()
    public_key = _public_text(private_key)
    sign_release(
        tmp_path,
        private_key,
        key_id="release-test",
        expected_public_key=public_key,
        files=("MediaManager.exe",),
    )

    blocked = check_release(
        tmp_path,
        key_id="release-test",
        public_key=public_key,
        files=("MediaManager.exe",),
        builtin_hashes={},
        authenticode_checker=lambda _path: "NotSigned",
    )
    ready = check_release(
        tmp_path,
        key_id="release-test",
        public_key=public_key,
        files=("MediaManager.exe",),
        builtin_hashes={},
        authenticode_checker=lambda _path: "Valid",
    )

    assert not blocked.ready
    assert "Authenticode signature is not valid: NotSigned" in blocked.errors
    assert ready.ready
