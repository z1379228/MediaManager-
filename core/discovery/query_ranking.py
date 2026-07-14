"""Bounded local query cleanup and explainable result ranking."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from contracts.discovery_v1 import DiscoveryItemV1


_PHRASE_ALIASES = {
    "lo-fi": "lofi",
    "lo fi": "lofi",
    "sound track": "soundtrack",
    "bg music": "background music",
}
_TOKEN_TYPOS = {
    "intrumental": "instrumental",
    "lyrcis": "lyrics",
    "offical": "official",
    "karoake": "karaoke",
}
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class PreparedSearchQuery:
    query: str
    corrections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SearchRanking:
    index: int
    score: int
    reasons: tuple[str, ...]


def prepare_search_query(raw: str) -> PreparedSearchQuery:
    """Normalize explicit text and fix only a small known local vocabulary."""

    query = " ".join(unicodedata.normalize("NFKC", raw).split())[:200]
    corrections: list[str] = []
    folded = query.casefold()
    for source, target in _PHRASE_ALIASES.items():
        if source in folded:
            pattern = re.compile(re.escape(source), re.IGNORECASE)
            query = pattern.sub(target, query)
            folded = query.casefold()
            corrections.append(f"{source} → {target}")
    words = query.split()
    for index, word in enumerate(words):
        replacement = _TOKEN_TYPOS.get(word.casefold())
        if replacement is not None:
            corrections.append(f"{word} → {replacement}")
            words[index] = replacement
    return PreparedSearchQuery(" ".join(words), tuple(corrections[:8]))


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(value.casefold()))


def rank_search_results(
    query: str,
    items: tuple[DiscoveryItemV1, ...],
) -> tuple[SearchRanking, ...]:
    """Return a stable local ordering with compact, user-visible reasons."""

    normalized = " ".join(query.casefold().split())
    query_tokens = _tokens(normalized)
    rankings: list[SearchRanking] = []
    for index, item in enumerate(items):
        title = " ".join(item.title.casefold().split())
        artist = " ".join(item.artist.casefold().split())
        title_tokens = _tokens(title)
        artist_tokens = _tokens(artist)
        score = 0
        reasons: list[str] = []
        if normalized and normalized in title:
            score += 60
            reasons.append("標題完整符合")
        elif query_tokens:
            matches = len(query_tokens & title_tokens)
            if matches:
                score += round(45 * matches / len(query_tokens))
                reasons.append("標題關鍵字")
        if normalized and normalized in artist:
            score += 30
            reasons.append("作者完整符合")
        elif query_tokens & artist_tokens:
            score += 20
            reasons.append("作者關鍵字")
        rankings.append(SearchRanking(index, min(score, 100), tuple(reasons)))
    return tuple(sorted(rankings, key=lambda item: (-item.score, item.index)))


def matching_search_indices(
    items: tuple[DiscoveryItemV1, ...],
    *,
    minimum_duration: int | None = None,
    maximum_duration: int | None = None,
    language: str = "",
) -> tuple[int, ...]:
    """Apply explicit local filters while preserving provider order."""

    if minimum_duration is not None and minimum_duration < 0:
        raise ValueError("minimum duration is invalid")
    if maximum_duration is not None and maximum_duration < 0:
        raise ValueError("maximum duration is invalid")
    if (
        minimum_duration is not None
        and maximum_duration is not None
        and minimum_duration > maximum_duration
    ):
        raise ValueError("duration filter range is invalid")
    normalized_language = language.strip().casefold()
    result: list[int] = []
    for index, item in enumerate(items):
        if minimum_duration is not None and (
            item.duration is None or item.duration < minimum_duration
        ):
            continue
        if maximum_duration is not None and (
            item.duration is None or item.duration > maximum_duration
        ):
            continue
        if normalized_language and item.language.casefold() != normalized_language:
            continue
        result.append(index)
    return tuple(result)
