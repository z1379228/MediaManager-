from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from plugin_host import external_provider


def _pinned_provider(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider_id: str = "test-pinned",
) -> Path:
    provider_directory = root / provider_id
    provider_directory.mkdir(parents=True)
    provider = provider_directory / "provider.py"
    provider.write_bytes(b"trusted built-in provider")
    monkeypatch.setitem(
        BUILTIN_PROVIDER_HASHES,
        provider_id,
        {"provider.py": hashlib.sha256(provider.read_bytes()).hexdigest()},
    )
    return provider


def test_cached_pinned_provider_executes_after_integrity_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_root = tmp_path / "application"
    provider_root = tmp_path / "cache" / "builtin-mod"
    provider = _pinned_provider(provider_root, monkeypatch)
    executed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        external_provider.runpy,
        "run_path",
        lambda path, *, run_name: executed.append((path, run_name)),
    )

    assert (
        external_provider.run_provider(
            provider,
            application_root,
            provider_root=provider_root,
        )
        == 0
    )
    assert executed == [(str(provider.absolute()), "__main__")]


def test_cached_pinned_provider_rejects_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_root = tmp_path / "cache" / "builtin-mod"
    provider = _pinned_provider(provider_root, monkeypatch)
    provider.write_bytes(b"tampered")
    monkeypatch.setattr(
        external_provider.runpy,
        "run_path",
        lambda *_args, **_kwargs: pytest.fail("tampered provider executed"),
    )

    assert (
        external_provider.run_provider(
            provider,
            tmp_path / "application",
            provider_root=provider_root,
        )
        == 2
    )


def test_cached_provider_rejects_unknown_provider_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_root = tmp_path / "cache" / "builtin-mod"
    provider = provider_root / "not-pinned" / "provider.py"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(b"unknown")

    def run_path(*_args, **_kwargs) -> None:
        pytest.fail("unknown provider executed")

    monkeypatch.setattr(external_provider.runpy, "run_path", run_path)

    assert (
        external_provider.run_provider(
            provider,
            tmp_path / "application",
            provider_root=provider_root,
        )
        == 2
    )


def test_cached_provider_rejects_path_escape_even_to_a_pinned_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_root = tmp_path / "cache" / "builtin-mod"
    trusted_root = tmp_path / "application" / "mod" / "builtin"
    provider = _pinned_provider(trusted_root, monkeypatch)
    escaped_path = (
        provider_root
        / "placeholder"
        / ".."
        / ".."
        / ".."
        / "application"
        / "mod"
        / "builtin"
        / "test-pinned"
        / "provider.py"
    )
    monkeypatch.setattr(
        external_provider.runpy,
        "run_path",
        lambda *_args, **_kwargs: pytest.fail("escaped provider executed"),
    )

    assert escaped_path.resolve() == provider.resolve()
    assert (
        external_provider.run_provider(
            escaped_path,
            tmp_path / "application",
            provider_root=trusted_root,
        )
        == 2
    )


def test_cached_provider_requires_explicit_verified_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_root = tmp_path / "cache" / "builtin-mod"
    provider = _pinned_provider(provider_root, monkeypatch)
    monkeypatch.setattr(
        external_provider.runpy,
        "run_path",
        lambda *_args, **_kwargs: pytest.fail("provider without root executed"),
    )

    assert external_provider.run_provider(provider, tmp_path / "application") == 2
