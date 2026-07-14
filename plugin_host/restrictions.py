"""Host-side path restrictions (defense in depth, not an OS sandbox)."""

from __future__ import annotations

from pathlib import Path


def confined_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise PermissionError("path escaped plugin root")
    return candidate

