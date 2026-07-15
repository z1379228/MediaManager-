"""Bounded JSON import/export for reviewed playlist entries."""

from __future__ import annotations

import json
from pathlib import Path

from contracts.playlist_v1 import MAX_PLAYLIST_ENTRIES_V1, PlaylistEntryV1


_PLAYLIST_KIND = "mediamanager-playlist-ids"
_MAX_PLAYLIST_FILE_BYTES = 2 * 1024 * 1024


def export_playlist_entries(
    target: Path, entries: tuple[PlaylistEntryV1, ...]
) -> int:
    if not entries:
        raise ValueError("playlist export is empty")
    if len(entries) > MAX_PLAYLIST_ENTRIES_V1:
        raise ValueError("playlist export is too large")
    if len({entry.entry_id for entry in entries}) != len(entries):
        raise ValueError("playlist export contains duplicate IDs")
    payload = {
        "schema_version": 1,
        "kind": _PLAYLIST_KIND,
        "entries": [_entry_payload(entry) for entry in entries],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        if temporary.stat().st_size > _MAX_PLAYLIST_FILE_BYTES:
            raise ValueError("playlist export is too large")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return len(entries)


def import_playlist_entries(source: Path) -> tuple[PlaylistEntryV1, ...]:
    if not source.is_file():
        raise ValueError("playlist file does not exist")
    if source.stat().st_size > _MAX_PLAYLIST_FILE_BYTES:
        raise ValueError("playlist file is too large")
    raw = json.loads(source.read_text(encoding="utf-8"))
    if (
        not isinstance(raw, dict)
        or set(raw) != {"schema_version", "kind", "entries"}
        or raw.get("schema_version") != 1
        or raw.get("kind") != _PLAYLIST_KIND
        or not isinstance(raw.get("entries"), list)
        or not 1 <= len(raw["entries"]) <= MAX_PLAYLIST_ENTRIES_V1
    ):
        raise ValueError("playlist file is invalid")
    try:
        entries = tuple(PlaylistEntryV1.from_dict(item) for item in raw["entries"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"playlist entry is invalid: {error}") from error
    if len({entry.entry_id for entry in entries}) != len(entries):
        raise ValueError("playlist file contains duplicate IDs")
    return entries


def _entry_payload(entry: PlaylistEntryV1) -> dict[str, object]:
    return {
        "entry_id": entry.entry_id,
        "url": entry.url,
        "title": entry.title,
        "artist": entry.artist,
        "duration": entry.duration,
        "position": entry.position,
        "available": entry.available,
        "unavailable_reason": entry.unavailable_reason,
        "thumbnail_url": entry.thumbnail_url,
    }
