"""Provision and verify bundled MOD templates."""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES


class BuiltinProviderIntegrityError(RuntimeError):
    pass


def verify_builtin_provider(root: Path, provider_id: str) -> None:
    expected = BUILTIN_PROVIDER_HASHES.get(provider_id)
    if expected is None:
        raise BuiltinProviderIntegrityError(f"unknown built-in provider: {provider_id}")
    resolved_root = root.resolve()
    for relative, digest in expected.items():
        path = (resolved_root / relative).resolve()
        if (
            not path.is_relative_to(resolved_root)
            or not path.is_file()
            or path.is_symlink()
        ):
            raise BuiltinProviderIntegrityError(
                f"unsafe built-in provider file: {provider_id}/{relative}"
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise BuiltinProviderIntegrityError(
                f"built-in provider integrity mismatch: {provider_id}/{relative}"
            )


def _verify_provider_root(root: Path) -> None:
    for provider_id in sorted(BUILTIN_PROVIDER_HASHES):
        verify_builtin_provider(root / provider_id, provider_id)


def ensure_builtin_provider(
    preferred_root: Path,
    provider_id: str,
    cache_root: Path | None = None,
) -> Path:
    """Provision one bundled MOD without coupling it to sibling MODs."""

    if provider_id not in BUILTIN_PROVIDER_HASHES:
        raise BuiltinProviderIntegrityError(
            f"unknown built-in provider: {provider_id}"
        )
    preferred_root = preferred_root.resolve()
    provider_root = preferred_root / provider_id
    if provider_root.exists():
        verify_builtin_provider(provider_root, provider_id)
        return provider_root

    bundle_root = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])
    )
    source_root = (bundle_root / "mod" / "builtin").resolve()
    if not source_root.is_dir():
        raise BuiltinProviderIntegrityError("bundled provider directory is missing")
    source = source_root / provider_id
    verify_builtin_provider(source, provider_id)

    destination_root = (cache_root or preferred_root).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / provider_id
    if not destination.exists():
        shutil.copytree(source, destination)
    verify_builtin_provider(destination, provider_id)
    return destination


def ensure_builtin_providers(
    preferred_root: Path,
    cache_root: Path | None = None,
) -> Path:
    preferred_root = preferred_root.resolve()
    if preferred_root.is_dir():
        for provider_id in sorted(BUILTIN_PROVIDER_HASHES):
            ensure_builtin_provider(preferred_root, provider_id, cache_root)
        return preferred_root
    destination_root = (cache_root or preferred_root).resolve()
    for provider_id in sorted(BUILTIN_PROVIDER_HASHES):
        ensure_builtin_provider(preferred_root, provider_id, destination_root)
    return destination_root
