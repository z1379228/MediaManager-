"""Explicit query planning and candidate ranking for video recovery."""

from __future__ import annotations

import json
import re
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


def plan(item: dict[str, Any]) -> dict[str, Any]:
    title = text(item.get("title"), 200)
    if not title:
        raise ValueError("recovery title missing")
    artist = text(item.get("artist"), 120)
    language = text(item.get("language"), 32)
    category = text(item.get("category"), 60)
    fallbacks: list[str] = []
    for query in (
        f"{artist} {title}" if artist else "",
        f"{artist} {category}" if artist and category else "",
        f"{language} {category} {title}" if language else "",
    ):
        query = text(query, 200)
        if query and query != title and query not in fallbacks:
            fallbacks.append(query)
    return {"primary_query": title, "fallback_queries": fallbacks[:4]}


def rank(
    original: dict[str, Any], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    original_title = tokens(original.get("title"))
    original_artist = tokens(original.get("artist"))
    ranked: list[dict[str, Any]] = []
    for candidate in candidates[:50]:
        if candidate.get("video_id") == original.get("video_id"):
            continue
        score = 0
        reasons: list[str] = []
        candidate_title = tokens(candidate.get("title"))
        candidate_artist = tokens(candidate.get("artist"))
        union = original_title | candidate_title
        if union:
            title_score = round(60 * len(original_title & candidate_title) / len(union))
            score += title_score
            if title_score:
                reasons.append("title")
        if original_artist and candidate_artist:
            artist_score = round(
                25 * len(original_artist & candidate_artist)
                / len(original_artist | candidate_artist)
            )
            score += artist_score
            if artist_score:
                reasons.append("artist")
        if (
            original.get("language")
            and original.get("language") == candidate.get("language")
        ):
            score += 5
            reasons.append("language")
        if (
            original.get("category")
            and original.get("category") == candidate.get("category")
        ):
            score += 10
            reasons.append("category")
        if score >= 20:
            ranked.append(
                {
                    "item": candidate,
                    "score": min(score, 100),
                    "reasons": reasons or ["related"],
                }
            )
    ranked.sort(key=lambda value: (-value["score"], value["item"]["title"].casefold()))
    return ranked


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "recovery_plan":
            value = plan(raw["item"])
        elif operation == "recovery_rank":
            value = rank(raw["item"], raw["candidates"])
        else:
            raise ValueError("unsupported recovery operation")
        emit({"type": "result", "value": value})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
