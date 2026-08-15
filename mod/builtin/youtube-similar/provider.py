"""User-triggered bounded similar media selection MOD."""

from __future__ import annotations

import json
import re
import secrets
import sys
import unicodedata
from itertools import islice
from typing import Any

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_SEARCH_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\ufe0e": None,
        "\ufe0f": None,
    }
)
_SEARCH_SEPARATOR_SPACING_RE = re.compile(r"\s*([|:/·・-])\s*")
_BALANCED_QUOTE_PATTERNS = tuple(
    re.compile(
        rf"{re.escape(opening)}([^{re.escape(opening + closing)}]*)"
        rf"{re.escape(closing)}"
    )
    for opening, closing in (("「", "」"), ("『", "』"), ("《", "》"), ("〈", "〉"))
)


def canonicalize_balanced_quote_pairs(value: str) -> str:
    for pattern in _BALANCED_QUOTE_PATTERNS:
        value = pattern.sub(lambda match: f'"{match.group(1)}"', value)
    return value


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def normalized_text_key(value: Any, limit: int = 200) -> str:
    normalized = canonicalize_balanced_quote_pairs(
        unicodedata.normalize("NFKC", text(value, limit)).casefold()
    )
    normalized = normalized.translate(_SEARCH_PUNCTUATION_TRANSLATION)
    normalized = _SEARCH_SEPARATOR_SPACING_RE.sub(r"\1", normalized)
    decomposed = unicodedata.normalize("NFKD", normalized)
    result: list[str] = []
    latin_base = False
    for character in decomposed:
        if unicodedata.combining(character):
            if not latin_base:
                result.append(character)
            continue
        result.append(character)
        latin_base = "LATIN" in unicodedata.name(character, "")
    return unicodedata.normalize("NFKC", "".join(result))


def tokens(value: Any, limit: int = 300) -> set[str]:
    return set(_TOKEN.findall(normalized_text_key(value, limit)))


def preference_groups(values: Any) -> dict[str, tuple[str, int]]:
    """Aggregate bounded preference counters by their Unicode text identity."""

    if not isinstance(values, dict):
        return {}
    groups: dict[str, tuple[str, int]] = {}
    for raw_value, raw_count in islice(values.items(), 100):
        value = text(raw_value, 200)
        key = normalized_text_key(value)
        if (
            not key
            or not isinstance(raw_count, int)
            or isinstance(raw_count, bool)
            or raw_count <= 0
        ):
            continue
        representative, total = groups.get(key, (value, 0))
        groups[key] = (representative, total + raw_count)
    return groups


def preferred_value(values: Any) -> str:
    groups = preference_groups(values)
    if not groups:
        return ""
    return max(groups.values(), key=lambda item: (item[1], item[0]))[0]


def preference_weight(values: Any, value: Any) -> int:
    key = normalized_text_key(value)
    group = preference_groups(values).get(key)
    return group[1] if group is not None else 0


def plan(item: dict[str, Any], preferences: dict[str, Any]) -> dict[str, Any]:
    title = text(item.get("title"), 160)
    artist = text(item.get("artist"), 100)
    language = text(item.get("language"), 24)
    category = text(item.get("category"), 40) or "video"
    queries: list[str] = []
    query_keys: set[str] = set()

    preferred_artists = preferences.get("artists")
    preferred_artist = text(preferred_value(preferred_artists), 100)

    combined_title = title
    if artist and title:
        artist_tokens = tokens(artist)
        title_tokens = tokens(title)
        combined_title = (
            title
            if artist_tokens and artist_tokens <= title_tokens
            else f"{artist} {title}"
        )

    for query in (
        combined_title,
        f"{artist} {category}" if artist else "",
        (
            f"{preferred_artist} {category}"
            if preferred_artist
            and normalized_text_key(preferred_artist, 100)
            != normalized_text_key(artist, 100)
            else ""
        ),
        f"{title} related" if title else "",
        f"{language} {category}" if language else "",
    ):
        query = text(query, 200)
        query_key = normalized_text_key(query)
        if query_key and query_key not in query_keys:
            query_keys.add(query_key)
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
    original_title, candidate_title = tokens(original.get("title"), 300), tokens(
        candidate.get("title"), 300
    )
    if original_title and candidate_title:
        overlap = round(
            35 * len(original_title & candidate_title)
            / len(original_title | candidate_title)
        )
        score += overlap
        if overlap:
            reasons.append("title")
    original_artist, candidate_artist = tokens(original.get("artist"), 200), tokens(
        candidate.get("artist"), 200
    )
    if original_artist and candidate_artist:
        overlap = round(
            30 * len(original_artist & candidate_artist)
            / len(original_artist | candidate_artist)
        )
        score += overlap
        if overlap:
            reasons.append("artist")
    original_language = normalized_text_key(original.get("language"), 24)
    candidate_language = normalized_text_key(candidate.get("language"), 24)
    if original_language and original_language == candidate_language:
        score += 10
        reasons.append("language")
    original_category = normalized_text_key(original.get("category"), 40)
    candidate_category = normalized_text_key(candidate.get("category"), 40)
    if original_category and original_category == candidate_category:
        score += 15
        reasons.append("category")

    artists = preferences.get("artists")
    artist = text(candidate.get("artist"), 200)
    artist_preference = preference_weight(artists, artist)
    if artist_preference:
        score += min(10, artist_preference)
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
