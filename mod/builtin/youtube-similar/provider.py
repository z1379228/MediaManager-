"""User-triggered bounded similar media selection MOD."""

from __future__ import annotations

import json
import re
import secrets
import sys
from typing import Any

_TOKEN = re.compile(r"[\w]+", re.UNICODE)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def tokens(value: Any) -> set[str]:
    return {part.casefold() for part in _TOKEN.findall(str(value or ""))}


def plan(item: dict[str, Any], preferences: dict[str, Any]) -> dict[str, Any]:
    title = text(item.get("title"), 160)
    artist = text(item.get("artist"), 100)
    language = text(item.get("language"), 24)
    category = text(item.get("category"), 40) or "video"
    queries: list[str] = []

    preferred_artists = preferences.get("artists")
    preferred_artist = ""
    if isinstance(preferred_artists, dict) and preferred_artists:
        preferred_artist = text(next(iter(preferred_artists)), 100)

    for query in (
        f"{artist} {category}" if artist else "",
        f"{title} related" if title else "",
        (
            f"{preferred_artist} {category}"
            if preferred_artist and preferred_artist.casefold() != artist.casefold()
            else ""
        ),
        f"{language} {category}" if language else "",
    ):
        query = text(query, 200)
        if query and query not in queries:
            queries.append(query)
        if len(queries) == 3:
            break
    if not queries:
        raise ValueError("similar query signals missing")
    return {"queries": queries}


def rank_one(
    original: dict[str, Any],
    candidate: dict[str, Any],
    preferences: dict[str, Any],
) -> dict[str, Any] | None:
    if candidate.get("video_id") == original.get("video_id"):
        return None
    score = 0
    reasons: list[str] = []
    original_title, candidate_title = tokens(original.get("title")), tokens(
        candidate.get("title")
    )
    if original_title and candidate_title:
        overlap = round(
            35 * len(original_title & candidate_title)
            / len(original_title | candidate_title)
        )
        score += overlap
        if overlap:
            reasons.append("title")
    original_artist, candidate_artist = tokens(original.get("artist")), tokens(
        candidate.get("artist")
    )
    if original_artist and candidate_artist:
        overlap = round(
            30 * len(original_artist & candidate_artist)
            / len(original_artist | candidate_artist)
        )
        score += overlap
        if overlap:
            reasons.append("artist")
    if original.get("language") and original.get("language") == candidate.get("language"):
        score += 10
        reasons.append("language")
    if original.get("category") and original.get("category") == candidate.get("category"):
        score += 15
        reasons.append("category")

    artists = preferences.get("artists")
    artist = text(candidate.get("artist"), 200)
    if isinstance(artists, dict) and artist in artists:
        score += min(10, int(artists[artist]))
        reasons.append("preference")
    if score < 15:
        return None
    return {
        "item": candidate,
        "score": min(score, 100),
        "reasons": reasons or ["related"],
    }


def select(
    original: dict[str, Any],
    candidates: list[dict[str, Any]],
    preferences: dict[str, Any],
) -> dict[str, Any] | None:
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates[:60]:
        video_id = text(candidate.get("video_id"), 100)
        if video_id and video_id not in unique:
            unique[video_id] = candidate
    ranked = [
        result
        for candidate in unique.values()
        if (result := rank_one(original, candidate, preferences)) is not None
    ]
    if not ranked:
        return None
    ranked.sort(key=lambda value: -value["score"])
    best = ranked[0]["score"]
    pool = [value for value in ranked[:8] if value["score"] >= best - 15]
    return secrets.choice(pool)


def rank(
    original: dict[str, Any],
    candidates: list[dict[str, Any]],
    preferences: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """Return a bounded, explainable list instead of only one random item."""

    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("similar result limit invalid")
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates[:120]:
        video_id = text(candidate.get("video_id"), 100)
        if (
            video_id
            and video_id != text(original.get("video_id"), 100)
            and video_id not in unique
        ):
            unique[video_id] = candidate
    ranked: list[dict[str, Any]] = []
    for candidate in unique.values():
        result = rank_one(original, candidate, preferences)
        if result is None:
            # The candidate already came from a bounded related query. Keep it
            # as a low-confidence fallback instead of collapsing the UI to one
            # result merely because localized titles share few text tokens.
            result = {"item": candidate, "score": 5, "reasons": ["search-query"]}
        ranked.append(result)
    ranked.sort(
        key=lambda value: (
            -value["score"],
            text(value["item"].get("title"), 300).casefold(),
            text(value["item"].get("video_id"), 100),
        )
    )
    return ranked[:limit]


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        preferences = raw.get("preferences")
        if not isinstance(preferences, dict):
            raise ValueError("similar preferences invalid")
        if operation == "similar_plan":
            value = plan(raw["item"], preferences)
        elif operation == "similar_select":
            value = select(raw["item"], raw["candidates"], preferences)
        elif operation == "similar_rank":
            value = rank(
                raw["item"], raw["candidates"], preferences, raw.get("limit", 12)
            )
        else:
            raise ValueError("unsupported similar operation")
        emit({"type": "result", "value": value})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
