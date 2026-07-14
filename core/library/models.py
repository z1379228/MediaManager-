"""Public models for the local media library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LibraryItem:
    item_id: str
    path: Path
    media_type: str
    size: int
    modified: float
    available: bool
    fingerprint: str | None = None
    title: str = ""
    artist: str = ""
    tags: tuple[str, ...] = ()
    play_count: int = 0
    last_played: float | None = None
    artwork_path: Path | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def display_title(self) -> str:
        return self.title or self.path.stem


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    fingerprint: str
    size: int
    items: tuple[LibraryItem, ...]


@dataclass(frozen=True, slots=True)
class MovePlan:
    item_id: str
    source: Path
    target: Path
    size: int
    modified: float


@dataclass(frozen=True, slots=True)
class PlaylistPreview:
    name: str
    paths: tuple[Path, ...]
    missing: tuple[Path, ...]
    duplicates: tuple[Path, ...]
    source_format: str
