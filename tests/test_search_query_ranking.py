from contracts.discovery_v1 import DiscoveryItemV1
from core.discovery.query_ranking import (
    matching_search_indices,
    prepare_search_query,
    rank_search_results,
)


def _item(
    video_id: str,
    title: str,
    artist: str,
    *,
    language: str = "",
) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        f"https://example.test/{video_id}",
        title,
        artist,
        120,
        language,
        "music",
        "",
    )


def test_query_alias_and_typo_correction_is_bounded() -> None:
    prepared = prepare_search_query("  LO-FI   offical lyrcis  ")

    assert prepared.query == "lofi official lyrics"
    assert prepared.corrections == (
        "lo-fi → lofi",
        "offical → official",
        "lyrcis → lyrics",
    )


def test_query_lofi_alias_accepts_typographic_hyphens() -> None:
    for raw in ("LO‑FI", "lo–fi", "lo―fi", "lo−fi"):
        prepared = prepare_search_query(raw)

        assert prepared.query == "lofi"
        assert prepared.corrections == ("lo-fi → lofi",)


def test_query_lofi_alias_accepts_spaced_hyphens() -> None:
    for raw in ("LO - FI", "lo – fi", "lo— fi", "lo −fi"):
        prepared = prepare_search_query(raw)

        assert prepared.query == "lofi"
        assert prepared.corrections == ("lo-fi → lofi",)


def test_query_lofi_spaced_hyphen_keeps_phrase_boundaries() -> None:
    for raw in ("flo - fi beats", "lo - fighter"):
        prepared = prepare_search_query(raw)

        assert prepared.query == raw
        assert prepared.corrections == ()


def test_query_lofi_typographic_hyphen_keeps_phrase_boundaries() -> None:
    prepared = prepare_search_query("flo–fi beats")

    assert prepared.query == "flo–fi beats"
    assert prepared.corrections == ()


def test_query_aliases_do_not_rewrite_inside_larger_words() -> None:
    prepared = prepare_search_query("flo-fi beats sound tracker bg musicology")

    assert prepared.query == "flo-fi beats sound tracker bg musicology"
    assert prepared.corrections == ()


def test_query_typo_corrections_preserve_surrounding_punctuation() -> None:
    prepared = prepare_search_query("song (OFFICAL), lyrcis!")

    assert prepared.query == "song (official), lyrics!"
    assert prepared.corrections == (
        "OFFICAL → official",
        "lyrcis → lyrics",
    )


def test_query_corrections_do_not_expand_past_contract_limit() -> None:
    phrase_query = f"{'x' * 191} bg music"
    typo_query = f"{'x' * 192} offical"

    prepared_phrase = prepare_search_query(phrase_query)
    prepared_typo = prepare_search_query(typo_query)

    assert prepared_phrase.query == phrase_query
    assert prepared_phrase.corrections == ()
    assert prepared_typo.query == typo_query
    assert prepared_typo.corrections == ()


def test_local_ranking_is_stable_and_explainable() -> None:
    items = (
        _item("weak", "Live recording", "Other"),
        _item("artist", "Live recording", "Example Artist"),
        _item("title", "Example Song official", "Artist"),
    )

    ranked = rank_search_results("example song", items)

    assert [item.index for item in ranked] == [2, 1, 0]
    assert ranked[0].score == 60
    assert ranked[0].reasons == ("標題完整符合",)
    assert ranked[-1].score == 0


def test_local_ranking_normalizes_unicode_compatibility_forms() -> None:
    items = (
        _item("weak", "Full session", "Other"),
        _item(
            "fullwidth",
            "ＦＵＬＬＷＩＤＴＨ ＭＵＳＩＣ",
            "ＥＸＡＭＰＬＥ ＡＲＴＩＳＴ",
        ),
    )

    ranked = rank_search_results("fullwidth music", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_local_ranking_normalizes_composed_and_decomposed_text() -> None:
    items = (
        _item("weak", "Cafe session", "Other"),
        _item("accent", "Cafe\u0301 session", "Example Artist"),
    )

    ranked = rank_search_results("café session", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_local_ranking_matches_latin_text_without_typed_diacritics() -> None:
    items = (
        _item("plain-extension", "Cafe live cover", "Other Artist"),
        _item("accented-exact", "Café", "Example Artist"),
    )

    ranked = rank_search_results("cafe", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 80
    assert ranked[0].reasons == ("標題忽略重音相等",)


def test_latin_diacritic_fallback_covers_artist_and_combined_fields() -> None:
    artist_items = (
        _item("mention", "Beyonce documentary", "Other Artist"),
        _item("artist", "Halo", "Beyoncé"),
    )

    artist_ranked = rank_search_results("beyonce", artist_items)

    assert [item.index for item in artist_ranked] == [1, 0]
    assert artist_ranked[0].score == 65
    assert artist_ranked[0].reasons == ("作者忽略重音相等",)

    combined_items = (
        _item("title-copy", "Beyonce Halo live cover", "Other Artist"),
        _item("split", "Halo", "Beyoncé"),
    )

    combined_ranked = rank_search_results("Beyonce Halo", combined_items)

    assert [item.index for item in combined_ranked] == [1, 0]
    assert combined_ranked[0].score == 95
    assert combined_ranked[0].reasons == ("作者與標題忽略重音符合",)


def test_smart_apostrophe_exact_title_outranks_a_longer_ascii_phrase() -> None:
    items = (
        _item("extended", "Don't Stop live cover", "Fan Channel"),
        _item("exact", "Don’t Stop", "Example Artist"),
    )

    ranked = rank_search_results("Don't Stop", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_typographic_dash_exact_title_outranks_a_longer_ascii_phrase() -> None:
    items = (
        _item("extended", "AC-DC live cover", "Fan Channel"),
        _item("exact", "AC\u2013DC", "Example Artist"),
    )

    ranked = rank_search_results("AC-DC", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_unicode_minus_exact_title_outranks_a_longer_ascii_phrase() -> None:
    items = (
        _item("extended", "AC-DC live cover", "Fan Channel"),
        _item("exact", "AC−DC", "Example Artist"),
    )

    ranked = rank_search_results("AC-DC", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_hyphen_spacing_exact_title_outranks_a_longer_phrase() -> None:
    items = (
        _item("extended", "AC-DC live cover", "Fan Channel"),
        _item("exact", "AC – DC", "Example Artist"),
    )

    ranked = rank_search_results("AC-DC", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_smart_double_quote_exact_title_outranks_a_longer_phrase() -> None:
    items = (
        _item("extended", '"Hello" live cover', "Fan Channel"),
        _item("exact", "“Hello”", "Example Artist"),
    )

    ranked = rank_search_results('"Hello"', items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_balanced_quoted_query_matches_an_unquoted_exact_title() -> None:
    items = (
        _item("extended", '"Midnight Echo" live cover', "Fan Channel"),
        _item("exact", "Midnight Echo", "Example Artist"),
    )

    ranked = rank_search_results("“Midnight Echo”", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_east_asian_balanced_title_marks_match_an_unquoted_exact_title() -> None:
    for opening, closing in (("「", "」"), ("『", "』"), ("《", "》"), ("〈", "〉")):
        query = f"{opening}Midnight Echo{closing}"
        items = (
            _item("extended", f"{query} live cover", "Fan Channel"),
            _item("exact", "Midnight Echo", "Example Artist"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert ranked[0].score == 85


def test_mismatched_east_asian_title_marks_are_not_stripped() -> None:
    items = (_item("title", "Midnight Echo", "Example Artist"),)

    ranked = rank_search_results("「Midnight Echo』", items)

    assert ranked[0].score != 85


def test_unclosed_quoted_query_is_not_treated_as_an_exact_title() -> None:
    items = (_item("title", "Midnight Echo", "Example Artist"),)

    ranked = rank_search_results('"Midnight Echo', items)

    assert ranked[0].score != 85
    assert "標題完全相等" not in ranked[0].reasons


def test_emoji_variation_selector_exact_title_outranks_a_longer_phrase() -> None:
    items = (
        _item("extended", "❤ Song live cover", "Fan Channel"),
        _item("exact", "❤️ Song", "Example Artist"),
    )

    ranked = rank_search_results("❤ Song", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 85
    assert ranked[0].reasons == ("標題完全相等",)


def test_latin_phrase_match_does_not_match_inside_another_word() -> None:
    items = (
        _item("substring", "Cartoon archive", "Example Artist"),
        _item("word", "Art documentary", "Example Artist"),
    )

    ranked = rank_search_results("art", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].reasons[0] == "標題完整符合"
    assert "標題完整符合" not in ranked[1].reasons


def test_exact_title_outranks_a_longer_title_phrase() -> None:
    items = (
        _item("extended", "Midnight Echo live cover", "Fan Channel"),
        _item("exact", "Midnight Echo", "Example Artist"),
    )

    ranked = rank_search_results("midnight echo", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score > ranked[1].score
    assert ranked[0].reasons == ("標題完全相等",)


def test_exact_artist_outranks_a_title_that_only_mentions_artist() -> None:
    items = (
        _item("mention", "Nora Vale documentary", "Other Artist"),
        _item("artist", "Midnight Echo", "Nora Vale"),
    )

    ranked = rank_search_results("nora vale", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score > ranked[1].score
    assert ranked[0].reasons == ("作者完全相等",)


def test_balanced_quoted_query_matches_an_unquoted_exact_artist() -> None:
    items = (
        _item("mention", '"Nora Vale" documentary', "Other Artist"),
        _item("artist", "Midnight Echo", "Nora Vale"),
    )

    ranked = rank_search_results("“Nora Vale”", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 70
    assert ranked[0].reasons == ("作者完全相等",)


def test_unclosed_quoted_query_is_not_treated_as_an_exact_artist() -> None:
    items = (_item("artist", "Midnight Echo", "Nora Vale"),)

    ranked = rank_search_results('"Nora Vale', items)

    assert ranked[0].score != 70
    assert "作者完全相等" not in ranked[0].reasons


def test_unspaced_script_phrase_match_preserves_substring_search() -> None:
    items = (_item("cjk", "盜墓王 完整版", "Example Artist"),)

    ranked = rank_search_results("盜墓", items)

    assert ranked[0].score == 60
    assert ranked[0].reasons == ("標題完整符合",)


def test_mixed_script_phrase_keeps_latin_word_boundary() -> None:
    items = (
        _item("substring", "Cart 音樂 archive", "Example Artist"),
        _item("word", "Art 音樂 documentary", "Example Artist"),
    )

    ranked = rank_search_results("art 音樂", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].reasons[0] == "標題完整符合"
    assert "標題完整符合" not in ranked[1].reasons


def test_local_ranking_prioritizes_exact_artist_and_title_query() -> None:
    items = (
        _item(
            "title-copy",
            "Nora Vale Midnight Echo live cover",
            "Other Artist",
        ),
        _item("split-exact", "Midnight Echo", "Nora Vale"),
    )

    ranked = rank_search_results("Nora Vale Midnight Echo", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score > ranked[1].score
    assert "作者與標題完整符合" in ranked[0].reasons


def test_exact_artist_and_title_outranks_title_phrase_plus_artist_keywords() -> None:
    items = (
        _item(
            "title-and-artist-keywords",
            "Nora Vale Midnight Echo live cover",
            "Nora Vale fan channel",
        ),
        _item("split-exact", "Midnight Echo", "Nora Vale"),
    )

    ranked = rank_search_results("Nora Vale Midnight Echo", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score > ranked[1].score
    assert ranked[0].reasons == ("作者與標題完整符合",)


def test_local_ranking_accepts_common_artist_title_separators() -> None:
    for separator in (" - ", " – ", " — ", " | ", ": ", " · "):
        query = f"Nora Vale{separator}Midnight Echo"
        items = (
            _item(
                "title-copy",
                f"{query} live cover",
                "Other Artist",
            ),
            _item("split-exact", "Midnight Echo", "Nora Vale"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert "作者與標題完整符合" in ranked[0].reasons


def test_local_ranking_accepts_unspaced_artist_title_separators() -> None:
    for separator in ("-", "–", "—", "|", ":", "·"):
        query = f"Nora Vale{separator}Midnight Echo"
        items = (
            _item(
                "title-copy",
                f"{query} live cover",
                "Other Artist",
            ),
            _item("split-exact", "Midnight Echo", "Nora Vale"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert ranked[0].score == 100
        assert ranked[0].reasons == ("作者與標題完整符合",)


def test_local_ranking_accepts_additional_strict_field_separators() -> None:
    for query in (
        "Nora Vale/Midnight Echo",
        "Midnight Echo /Nora Vale",
        "Nora Vale/ Midnight Echo",
        "Midnight Echo ／ Nora Vale",
        "Nora Vale・Midnight Echo",
        "Midnight Echo ・ Nora Vale",
        "Nora Vale| Midnight Echo",
        "Midnight Echo :Nora Vale",
    ):
        items = (
            _item("title-copy", f"{query} live cover", "Other Artist"),
            _item("split-exact", "Midnight Echo", "Nora Vale"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert ranked[0].score == 100


def test_additional_field_separators_do_not_match_partial_artist() -> None:
    items = (_item("full-artist", "Midnight Echo", "Nora Vale"),)

    ranked = rank_search_results("Nora/Midnight Echo", items)

    assert ranked[0].score != 100


def test_local_ranking_accepts_quoted_title_by_artist_query() -> None:
    query = '"Midnight Echo" by Nora Vale'
    items = (
        _item("title-copy", f"{query} live cover", "Other Artist"),
        _item("split-exact", "Midnight Echo", "Nora Vale"),
    )

    ranked = rank_search_results(query, items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].score == 100
    assert ranked[0].reasons == ("作者與標題完整符合",)


def test_local_ranking_accepts_quoted_title_with_artist_separators() -> None:
    for query in (
        '"Midnight Echo" Nora Vale',
        'Nora Vale "Midnight Echo"',
        '"Midnight Echo" - Nora Vale',
        'Nora Vale - "Midnight Echo"',
    ):
        items = (
            _item("title-copy", f"{query} live cover", "Other Artist"),
            _item("split-exact", "Midnight Echo", "Nora Vale"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert ranked[0].score == 100
        assert ranked[0].reasons == ("作者與標題完整符合",)


def test_local_ranking_accepts_quoted_artist_with_title_separators() -> None:
    for query in (
        '"Nora Vale" Midnight Echo',
        'Midnight Echo "Nora Vale"',
        '“Nora Vale” - Midnight Echo',
        'Midnight Echo - “Nora Vale”',
        '"Nora Vale" "Midnight Echo"',
        '"Midnight Echo" by "Nora Vale"',
    ):
        items = (
            _item("title-copy", f"{query} live cover", "Other Artist"),
            _item("split-exact", "Midnight Echo", "Nora Vale"),
        )

        ranked = rank_search_results(query, items)

        assert [item.index for item in ranked] == [1, 0]
        assert ranked[0].score == 100


def test_partial_quoted_artist_does_not_become_a_combined_exact_match() -> None:
    items = (_item("full-artist", "Midnight Echo", "Nora Vale"),)

    ranked = rank_search_results('"Nora" Midnight Echo', items)

    assert ranked[0].score != 100


def test_partial_quoted_title_does_not_become_a_combined_exact_match() -> None:
    items = (_item("full-title", "Midnight Echo", "Nora Vale"),)

    ranked = rank_search_results('"Midnight" Nora Vale', items)

    assert ranked[0].score != 100
    assert "作者與標題完整符合" not in ranked[0].reasons


def test_local_ranking_does_not_treat_unquoted_by_as_a_field_separator() -> None:
    items = (
        _item("split-words", "Stand", "Me"),
        _item("exact-title", "Stand by Me", "Ben E. King"),
    )

    ranked = rank_search_results("Stand by Me", items)

    assert [item.index for item in ranked] == [1, 0]
    assert ranked[0].reasons == ("標題完全相等",)
    assert "作者與標題完整符合" not in ranked[1].reasons


def test_local_duration_and_language_filters_preserve_order() -> None:
    items = (
        DiscoveryItemV1(
            "short-ja",
            "https://example.test/short-ja",
            "Short",
            "Artist",
            180,
            "ja",
            "music",
            "",
        ),
        DiscoveryItemV1(
            "long-ja",
            "https://example.test/long-ja",
            "Long",
            "Artist",
            1800,
            "ja",
            "music",
            "",
        ),
        DiscoveryItemV1(
            "unknown",
            "https://example.test/unknown",
            "Unknown",
            "Artist",
            None,
            "",
            "music",
            "",
        ),
    )

    assert matching_search_indices(
        items, minimum_duration=1200, language="ja"
    ) == (1,)
    assert matching_search_indices(items) == (0, 1, 2)


def test_language_filter_normalizes_unicode_compatibility_forms() -> None:
    items = (_item("fullwidth", "Song", "Artist", language="ＪＡ"),)

    assert matching_search_indices(items, language="ja") == (0,)


def test_language_filter_normalizes_composed_and_decomposed_text() -> None:
    items = (_item("accent", "Song", "Artist", language="Cafe\u0301"),)

    assert matching_search_indices(items, language="café") == (0,)
