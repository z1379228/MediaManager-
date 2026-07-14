from __future__ import annotations

import hashlib

import pytest

from core.downloads.builtin import BuiltinProviderIntegrityError, verify_builtin_provider
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES


def test_all_builtin_integrity_digests_are_sha256() -> None:
    for files in BUILTIN_PROVIDER_HASHES.values():
        for digest in files.values():
            assert len(digest) == 64
            assert all(character in "0123456789abcdef" for character in digest)


def test_builtin_provider_integrity_detects_tampering(tmp_path, monkeypatch) -> None:
    root = tmp_path / "sample"
    root.mkdir()
    provider = root / "provider.py"
    provider.write_bytes(b"trusted")
    digest = hashlib.sha256(provider.read_bytes()).hexdigest()
    monkeypatch.setitem(BUILTIN_PROVIDER_HASHES, "sample", {"provider.py": digest})
    verify_builtin_provider(root, "sample")
    provider.write_bytes(b"tampered")
    with pytest.raises(BuiltinProviderIntegrityError, match="integrity mismatch"):
        verify_builtin_provider(root, "sample")


def test_builtin_provider_integrity_rejects_symlink(tmp_path, monkeypatch) -> None:
    root = tmp_path / "sample"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"trusted")
    link = root / "provider.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    monkeypatch.setitem(BUILTIN_PROVIDER_HASHES, "sample", {"provider.py": digest})
    with pytest.raises(BuiltinProviderIntegrityError, match="unsafe"):
        verify_builtin_provider(root, "sample")
