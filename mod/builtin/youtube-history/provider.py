"""Bounded local discovery history MOD."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

MAX_EVENTS = 500


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("history store schema invalid")
    events = raw.get("events")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError("history store events invalid")
    return events


def save(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {"schema_version": 1, "events": events[-MAX_EVENTS:]},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def normalized_query(value: Any) -> str:
    query = " ".join(str(value or "").split())
    if not 1 <= len(query) <= 200:
        raise ValueError("history query length invalid")
    return query


def record(path: Path, raw: dict[str, Any]) -> bool:
    event_type = raw.get("event_type")
    if event_type not in {"search", "selection"}:
        raise ValueError("history event type invalid")
    item = raw.get("item")
    if event_type == "search" and item is not None:
        raise ValueError("search history item must be empty")
    if event_type == "selection" and not isinstance(item, dict):
        raise ValueError("selection history item missing")
    events = load(path)
    events.append(
        {
            "event_type": event_type,
            "query": normalized_query(raw.get("query")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "item": item,
        }
    )
    save(path, events)
    return True


def recent(path: Path, limit: int) -> list[dict[str, Any]]:
    return list(reversed(load(path)))[: max(1, min(int(limit), 100))]


def preferences(path: Path) -> dict[str, Any]:
    events = load(path)
    selections = [
        event.get("item")
        for event in events
        if event.get("event_type") == "selection"
        and isinstance(event.get("item"), dict)
    ]
    content_types: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    artists: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    for item in selections:
        category = str(item.get("category") or "video")[:100]
        content_types["music" if category == "music" else "video"] += 1
        if value := str(item.get("language") or "")[:32]:
            languages[value] += 1
        if value := str(item.get("artist") or "")[:200]:
            artists[value] += 1
        categories[category] += 1
    return {
        "total_searches": sum(
            event.get("event_type") == "search" for event in events
        ),
        "total_selections": len(selections),
        "content_types": dict(content_types.most_common(100)),
        "languages": dict(languages.most_common(100)),
        "artists": dict(artists.most_common(100)),
        "categories": dict(categories.most_common(100)),
    }


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        path = Path(str(raw.get("state_path", ""))).resolve()
        operation = raw.get("operation")
        if operation == "history_record":
            value = record(path, raw["event"])
        elif operation == "history_recent":
            value = recent(path, int(raw.get("limit", 20)))
        elif operation == "history_preferences":
            value = preferences(path)
        else:
            raise ValueError("unsupported history operation")
        emit({"type": "result", "value": value})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
