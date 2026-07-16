"""Bounded local viewing history for the official AniGamer workspace.

The history stores only URLs and public titles selected by the user.  It never
stores cookies, login state, page HTML, stream URLs, or playback credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

from contracts.discovery_v1 import DiscoveryItemV1
from core.site_routing import classify_site_url


HISTORY_SCHEMA = 1
HISTORY_KIND = "ani-gamer-local-history"
MAX_HISTORY_ENTRIES = 100
MAX_HISTORY_FILE_BYTES = 128 * 1024
MAX_TITLE_LENGTH = 300


@dataclass(frozen=True, slots=True)
class AniGamerHistoryEntry:
    series_id: str
    series_title: str
    episode_id: str
    episode_title: str
    url: str
    opened_at_utc: str


def history_path(data_root: Path) -> Path:
    """Return the local-only history path below the application data root."""

    root = Path(data_root).expanduser()
    if root.is_symlink():
        raise ValueError("AniGamer history data root is unsafe")
    return root / "ani-gamer-history.json"


def _text(value: object, limit: int = MAX_TITLE_LENGTH) -> str:
    return " ".join(str(value).split())[:limit]


def _valid_entry(raw: object) -> AniGamerHistoryEntry | None:
    if not isinstance(raw, dict):
        return None
    values = {
        key: _text(raw.get(key, ""))
        for key in (
            "series_id",
            "series_title",
            "episode_id",
            "episode_title",
            "url",
            "opened_at_utc",
        )
    }
    route = classify_site_url(values["url"])
    if (
        not values["series_id"]
        or not values["series_title"]
        or not values["episode_id"]
        or not values["episode_title"]
        or route is None
        or route.site_family != "ani-gamer"
        or route.resource_kind != "episode"
        or not values["opened_at_utc"]
    ):
        return None
    return AniGamerHistoryEntry(**values)


def load_history(path: Path) -> tuple[AniGamerHistoryEntry, ...]:
    """Load a bounded history file; invalid records are ignored safely."""

    candidate = Path(path).expanduser()
    if candidate.is_symlink() or not candidate.is_file():
        return ()
    if candidate.stat().st_size > MAX_HISTORY_FILE_BYTES:
        return ()
    try:
        document = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return ()
    if (
        not isinstance(document, dict)
        or document.get("schema") != HISTORY_SCHEMA
        or document.get("kind") != HISTORY_KIND
        or not isinstance(document.get("entries"), list)
    ):
        return ()
    result: list[AniGamerHistoryEntry] = []
    seen: set[tuple[str, str]] = set()
    for raw in document["entries"][:MAX_HISTORY_ENTRIES]:
        entry = _valid_entry(raw)
        if entry is None:
            continue
        key = (entry.episode_id, entry.url)
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return tuple(result)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("AniGamer history destination is unsafe")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(payload)
            output.flush()
        for attempt in range(3):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.02 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _history_document(
    entries: tuple[AniGamerHistoryEntry, ...], timestamp: datetime
) -> bytes:
    document = {
        "schema": HISTORY_SCHEMA,
        "kind": HISTORY_KIND,
        "updated_at_utc": timestamp.isoformat(),
        "entries": [
            {
                "series_id": item.series_id,
                "series_title": item.series_title,
                "episode_id": item.episode_id,
                "episode_title": item.episode_title,
                "url": item.url,
                "opened_at_utc": item.opened_at_utc,
            }
            for item in entries
        ],
    }
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    if len(payload) > MAX_HISTORY_FILE_BYTES:
        raise ValueError("AniGamer history is too large")
    return payload


def clear_history(path: Path) -> None:
    """Clear local viewing history without touching any media archive."""

    timestamp = datetime.now(timezone.utc)
    _atomic_write(Path(path).expanduser(), _history_document((), timestamp))


def export_history(path: Path, destination: Path) -> Path:
    """Export a validated copy of local history to a user-selected JSON file."""

    target = Path(destination).expanduser()
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise ValueError("AniGamer history export destination is unsafe")
    entries = load_history(path)
    payload = _history_document(entries, datetime.now(timezone.utc))
    _atomic_write(target, payload)
    return target


def record_history(
    path: Path,
    series: DiscoveryItemV1,
    episode: DiscoveryItemV1,
    *,
    opened_at: datetime | None = None,
) -> tuple[AniGamerHistoryEntry, ...]:
    """Prepend one explicit official episode visit and persist it atomically."""

    series_route = classify_site_url(series.url)
    episode_route = classify_site_url(episode.url)
    if (
        series_route is None
        or series_route.site_family != "ani-gamer"
        or series_route.resource_kind != "series"
        or episode_route is None
        or episode_route.site_family != "ani-gamer"
        or episode_route.resource_kind != "episode"
    ):
        raise ValueError("AniGamer history item URL is invalid")
    timestamp = (opened_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entry = AniGamerHistoryEntry(
        _text(series.video_id, 100),
        _text(series.title),
        _text(episode.video_id, 100),
        _text(episode.title),
        _text(episode.url, 500),
        timestamp.isoformat(),
    )
    previous = load_history(path)
    entries = (entry,) + tuple(
        item
        for item in previous
        if (item.episode_id, item.url) != (entry.episode_id, entry.url)
    )
    entries = entries[:MAX_HISTORY_ENTRIES]
    payload = _history_document(entries, timestamp)
    _atomic_write(Path(path).expanduser(), payload)
    return entries
