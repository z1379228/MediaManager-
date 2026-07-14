"""Bounded filesystem media discovery used by the trusted desktop UI."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

MEDIA_TYPES = {
    "圖片": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".svg"},
    "影片": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv"},
    "音訊": {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus", ".wma"},
}


@dataclass(frozen=True, slots=True)
class MediaItem:
    path: Path
    media_type: str
    size: int
    modified: float

    @property
    def name(self) -> str:
        return self.path.name


def classify(path: Path) -> str | None:
    suffix = path.suffix.lower()
    return next(
        (kind for kind, extensions in MEDIA_TYPES.items() if suffix in extensions), None
    )


def scan_media(folder: Path, *, limit: int = 50_000) -> list[MediaItem]:
    """Return supported regular files without following directory symlinks.

    The limit keeps an accidentally broad root from consuming unbounded memory.
    """

    if limit < 1:
        raise ValueError("media scan limit must be positive")
    results: list[MediaItem] = []
    if not folder.is_dir() or folder.is_symlink():
        return results
    root = folder.resolve()
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name for name in directories if not (current_path / name).is_symlink()
        ]
        for name in files:
            path = current_path / name
            kind = classify(path)
            if kind is None or path.is_symlink():
                continue
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            results.append(MediaItem(path.resolve(), kind, stat.st_size, stat.st_mtime))
            if len(results) >= limit:
                return sorted(results, key=lambda item: item.name.casefold())
    return sorted(results, key=lambda item: item.name.casefold())
