"""Bounded local query cleanup and explainable result ranking."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.text_normalization import (
    normalized_comparison_text as _normalized_comparison_text,
    normalized_search_text as _normalized_search_text,
)


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
_TOKEN_TYPO_RE = re.compile(
    rf"(?<!\w)(?:{'|'.join(re.escape(value) for value in _TOKEN_TYPOS)})(?!\w)",
    re.IGNORECASE,
)
_ALIAS_HYPHEN_PATTERN = r"[-\u2010-\u2015\u2212]"
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_MAX_QUERY_LENGTH = 200
_COMBINED_FIELD_SEPARATORS = (
    " ",
    "-",
    "|",
    ":",
    "·",
    "・",
    "/",
)
_UNSPACED_SCRIPT_MARKERS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
    "THAI",
    "LAO",
    "KHMER",
    "MYANMAR",
)


@dataclass(frozen=True, slots=True)
class PreparedSearchQuery:
    query: str
    corrections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SearchRanking:
    index: int
    score: int
    reasons: tuple[str, ...]


def _phrase_alias_pattern(source: str) -> str:
    return "".join(
        (
            rf"\s*{_ALIAS_HYPHEN_PATTERN}\s*"
            if character == "-"
            else re.escape(character)
        )
        for character in source
    )


def prepare_search_query(raw: str) -> PreparedSearchQuery:
    """Normalize explicit text and fix only a small known local vocabulary."""

    query = " ".join(unicodedata.normalize("NFKC", raw).split())[
        :_MAX_QUERY_LENGTH
    ]
    corrections: list[str] = []
    for source, target in _PHRASE_ALIASES.items():
        pattern = re.compile(
            rf"(?<!\w){_phrase_alias_pattern(source)}(?!\w)",
            re.IGNORECASE,
        )
        candidate, replacements = pattern.subn(target, query)
        if replacements and len(candidate) <= _MAX_QUERY_LENGTH:
            query = candidate
            corrections.append(f"{source} → {target}")
    offset = 0
    while match := _TOKEN_TYPO_RE.search(query, offset):
        source = match.group(0)
        replacement = _TOKEN_TYPOS[source.casefold()]
        candidate = f"{query[: match.start()]}{replacement}{query[match.end() :]}"
        if len(candidate) <= _MAX_QUERY_LENGTH:
            query = candidate
            corrections.append(f"{source} → {replacement}")
            offset = match.start() + len(replacement)
        else:
            offset = match.end()
    return PreparedSearchQuery(query, tuple(corrections[:8]))


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(_normalized_comparison_text(value)))


def _requires_word_boundary(character: str) -> bool:
    name = unicodedata.name(character, "")
    return character.isalnum() and not any(
        marker in name for marker in _UNSPACED_SCRIPT_MARKERS
    )


def _contains_search_phrase(field: str, phrase: str) -> bool:
    if not phrase:
        return False
    prefix = r"(?<!\w)" if _requires_word_boundary(phrase[0]) else ""
    suffix = r"(?!\w)" if _requires_word_boundary(phrase[-1]) else ""
    return re.search(f"{prefix}{re.escape(phrase)}{suffix}", field) is not None


def _combined_field_candidates(artist: str, title: str) -> frozenset[str]:
    candidates = {
        candidate
        for separator in _COMBINED_FIELD_SEPARATORS
        for artist_candidate in (artist, f'"{artist}"')
        for title_candidate in (title, f'"{title}"')
        for candidate in (
            f"{artist_candidate}{separator}{title_candidate}",
            f"{title_candidate}{separator}{artist_candidate}",
        )
    }
    candidates.update(
        f'"{title}" by {artist_candidate}'
        for artist_candidate in (artist, f'"{artist}"')
    )
    return frozenset(candidates)


def _balanced_quoted_phrase(value: str) -> str:
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return ""
    return value[1:-1].strip()


def rank_search_results(
    query: str,
    items: tuple[DiscoveryItemV1, ...],
) -> tuple[SearchRanking, ...]:
    """Return a stable local ordering with compact, user-visible reasons."""

    normalized = _normalized_comparison_text(query)
    folded_query = _normalized_search_text(query)
    normalized_field_queries = frozenset(
        value for value in (normalized, _balanced_quoted_phrase(normalized)) if value
    )
    folded_field_queries = frozenset(
        value
        for value in (folded_query, _balanced_quoted_phrase(folded_query))
        if value
    )
    query_tokens = _tokens(folded_query)
    rankings: list[SearchRanking] = []
    for index, item in enumerate(items):
        title = _normalized_comparison_text(item.title)
        artist = _normalized_comparison_text(item.artist)
        folded_title = _normalized_search_text(item.title)
        folded_artist = _normalized_search_text(item.artist)
        title_tokens = _tokens(folded_title)
        artist_tokens = _tokens(folded_artist)
        score = 0
        reasons: list[str] = []
        combined_exact = bool(
            normalized
            and artist
            and title
            and normalized in _combined_field_candidates(artist, title)
        )
        folded_combined_exact = bool(
            not combined_exact
            and folded_query
            and folded_artist
            and folded_title
            and (
                folded_query != normalized
                or folded_artist != artist
                or folded_title != title
            )
            and folded_query
            in _combined_field_candidates(folded_artist, folded_title)
        )
        if combined_exact:
            score = 100
            reasons.append("作者與標題完整符合")
        elif folded_combined_exact:
            score = 95
            reasons.append("作者與標題忽略重音符合")
        else:
            if title and title in normalized_field_queries:
                score += 85
                reasons.append("標題完全相等")
            elif (
                folded_title
                and folded_title in folded_field_queries
                and (
                    folded_title not in normalized_field_queries
                    or folded_title != title
                )
            ):
                score += 80
                reasons.append("標題忽略重音相等")
            elif _contains_search_phrase(title, normalized):
                score += 60
                reasons.append("標題完整符合")
            elif (
                (folded_query != normalized or folded_title != title)
                and _contains_search_phrase(folded_title, folded_query)
            ):
                score += 55
                reasons.append("標題忽略重音符合")
            elif query_tokens:
                matches = len(query_tokens & title_tokens)
                if matches:
                    score += round(45 * matches / len(query_tokens))
                    reasons.append("標題關鍵字")
            if artist and artist in normalized_field_queries:
                score += 70
                reasons.append("作者完全相等")
            elif (
                folded_artist
                and folded_artist in folded_field_queries
                and (
                    folded_artist not in normalized_field_queries
                    or folded_artist != artist
                )
            ):
                score += 65
                reasons.append("作者忽略重音相等")
            elif _contains_search_phrase(artist, normalized):
                score += 30
                reasons.append("作者完整符合")
            elif (
                (folded_query != normalized or folded_artist != artist)
                and _contains_search_phrase(folded_artist, folded_query)
            ):
                score += 25
                reasons.append("作者忽略重音符合")
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
    normalized_language = _normalized_comparison_text(language)
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
        if (
            normalized_language
            and _normalized_comparison_text(item.language) != normalized_language
        ):
            continue
        result.append(index)
    return tuple(result)
