"""Resolve the trusted MediaManager application icon."""

from __future__ import annotations

from pathlib import Path


def app_icon_path() -> Path | None:
    """Return the bundled PNG icon without following an external symlink."""

    root = Path(__file__).resolve().parent / "assets"
    candidate = root / "app-icon.png"
    if candidate.is_symlink() or not candidate.is_file():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        return None
    return resolved
