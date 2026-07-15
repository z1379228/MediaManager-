"""Restricted entry used by frozen MediaManager to execute an external provider."""

from __future__ import annotations

import runpy
from pathlib import Path

from core.downloads.builtin import (
    BuiltinProviderIntegrityError,
    verify_builtin_provider,
)
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES


def run_provider(
    path: Path,
    application_root: Path,
    *,
    provider_root: Path | None = None,
) -> int:
    del application_root
    if provider_root is None or ".." in path.parts or ".." in provider_root.parts:
        return 2
    provider = path.absolute()
    root = provider_root.absolute()
    try:
        relative = provider.relative_to(root)
    except ValueError:
        return 2
    if (
        len(relative.parts) != 2
        or relative.parts[1] != "provider.py"
        or relative.parts[0] not in BUILTIN_PROVIDER_HASHES
    ):
        return 2
    provider_id = relative.parts[0]
    provider_directory = root / provider_id
    expected_provider = provider_directory / "provider.py"
    try:
        if (
            provider != expected_provider
            or not root.is_dir()
            or root.is_symlink()
            or not provider_directory.is_dir()
            or provider_directory.is_symlink()
            or not provider.is_file()
            or provider.is_symlink()
        ):
            return 2
        verify_builtin_provider(provider_directory, provider_id)
    except (BuiltinProviderIntegrityError, OSError):
        return 2
    try:
        runpy.run_path(str(provider), run_name="__main__")
    except SystemExit as error:
        return int(error.code or 0)
    return 0
