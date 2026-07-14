"""Restricted entry used by frozen MediaManager to execute an external provider."""

from __future__ import annotations

import runpy
from pathlib import Path


def run_provider(path: Path, application_root: Path) -> int:
    provider = path.resolve()
    mod_root = (application_root / "mod").resolve()
    if not provider.is_relative_to(mod_root) or not provider.is_file() or provider.is_symlink():
        return 2
    try:
        runpy.run_path(str(provider), run_name="__main__")
    except SystemExit as error:
        return int(error.code or 0)
    return 0
