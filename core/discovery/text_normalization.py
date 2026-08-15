"""Shared Unicode identities for local discovery matching and deduplication."""

from __future__ import annotations

import re
import unicodedata


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


def _canonicalize_balanced_quote_pairs(value: str) -> str:
    for pattern in _BALANCED_QUOTE_PATTERNS:
        value = pattern.sub(lambda match: f'"{match.group(1)}"', value)
    return value


def normalized_comparison_text(value: str) -> str:
    """Return a stable NFKC, case-insensitive, whitespace-folded identity."""

    normalized = _canonicalize_balanced_quote_pairs(
        unicodedata.normalize("NFKC", value).casefold()
    )
    whitespace_folded = " ".join(
        normalized.translate(_SEARCH_PUNCTUATION_TRANSLATION).split()
    )
    return _SEARCH_SEPARATOR_SPACING_RE.sub(r"\1", whitespace_folded)


def normalized_search_text(value: str) -> str:
    """Also fold Latin diacritics while preserving marks in other scripts."""

    decomposed = unicodedata.normalize(
        "NFKD",
        normalized_comparison_text(value),
    )
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
