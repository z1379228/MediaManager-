"""Small cross-platform filesystem commit helpers."""

from __future__ import annotations

import os
from pathlib import Path


def commit_file_without_overwrite(source: Path, target: Path) -> None:
    """Atomically expose a same-volume file while refusing an existing target."""

    if target.exists():
        raise FileExistsError(target)
    if os.name == "nt":
        # MoveFile on Windows refuses an existing destination and works on
        # NTFS, FAT and exFAT, unlike hard-link creation.
        source.rename(target)
        return
    os.link(source, target)
    source.unlink()
