from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

from core.downloads.builtin import (
    BuiltinProviderIntegrityError,
    ensure_builtin_provider,
    verify_builtin_provider,
)
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES


def test_all_builtin_integrity_digests_are_sha256() -> None:
    for files in BUILTIN_PROVIDER_HASHES.values():
        for digest in files.values():
            assert len(digest) == 64
            assert all(character in "0123456789abcdef" for character in digest)


def test_pinned_builtin_integrity_matches_repository_files() -> None:
    builtin_root = Path(__file__).resolve().parents[1] / "mod" / "builtin"
    for provider_id, files in BUILTIN_PROVIDER_HASHES.items():
        for relative_path, expected in files.items():
            content = (builtin_root / provider_id / relative_path).read_bytes()
            assert hashlib.sha256(content).hexdigest() == expected, (
                f"stale built-in integrity hash: {provider_id}/{relative_path}"
            )


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


def test_single_builtin_provision_does_not_require_sibling_mods(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "builtin"
    provider = root / "sample"
    provider.mkdir(parents=True)
    entry = provider / "provider.py"
    entry.write_bytes(b"trusted")
    monkeypatch.setattr(
        "core.downloads.builtin.BUILTIN_PROVIDER_HASHES",
        {
            "sample": {"provider.py": hashlib.sha256(b"trusted").hexdigest()},
            "missing-sibling": {"provider.py": "0" * 64},
        },
    )

    assert ensure_builtin_provider(root, "sample") == provider.resolve()


def test_frozen_builtin_provision_populates_an_existing_partial_cache(
    tmp_path, monkeypatch
) -> None:
    bundle = tmp_path / "bundle"
    source_root = bundle / "mod" / "builtin"
    hashes: dict[str, dict[str, str]] = {}
    for provider_id in ("first", "second"):
        provider = source_root / provider_id
        provider.mkdir(parents=True)
        content = f"trusted-{provider_id}".encode()
        (provider / "provider.py").write_bytes(content)
        hashes[provider_id] = {
            "provider.py": hashlib.sha256(content).hexdigest()
        }

    monkeypatch.setattr(
        "core.downloads.builtin.BUILTIN_PROVIDER_HASHES", hashes
    )
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    cache = tmp_path / "cache"

    first = ensure_builtin_provider(cache, "first")
    second = ensure_builtin_provider(cache, "second")

    assert first == (cache / "first").resolve()
    assert second == (cache / "second").resolve()
    assert (first / "provider.py").read_bytes() == b"trusted-first"
    assert (second / "provider.py").read_bytes() == b"trusted-second"
