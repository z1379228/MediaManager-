from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1
from core.discovery.suggestions import preference_search_queries


def preferences() -> HistoryPreferencesV1:
    return HistoryPreferencesV1(
        10,
        4,
        {"music": 3},
        {"中文": 4},
        {"Aimer": 5},
        {"作業用 BGM": 3},
    )


def test_preference_queries_are_bounded_ranked_and_deduplicated() -> None:
    events = (
        HistoryEventV1("search", "Aimer", "2026-07-14T00:00:00Z", None),
        HistoryEventV1("search", "動漫音樂", "2026-07-14T00:00:01Z", None),
    )
    assert preference_search_queries(preferences(), events, limit=4) == (
        "Aimer",
        "中文 作業用 BGM",
        "音樂",
        "動漫音樂",
    )


def test_preference_queries_do_not_exceed_hard_limit() -> None:
    assert len(preference_search_queries(preferences(), limit=999)) <= 12


def test_preference_queries_stop_consuming_events_when_limit_is_full() -> None:
    consumed: list[int] = []

    def events():
        for index in range(20):
            consumed.append(index)
            yield HistoryEventV1(
                "search",
                f"query {index}",
                "2026-07-14T00:00:00Z",
                None,
            )

    empty_preferences = HistoryPreferencesV1(0, 0, {}, {}, {}, {})

    assert preference_search_queries(
        empty_preferences,
        events(),
        limit=2,
    ) == ("query 0", "query 1")
    assert consumed == [0, 1]


def test_preference_queries_deduplicate_unicode_equivalents() -> None:
    unicode_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"ＦＵＬＬＷＩＤＴＨ": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "fullwidth",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(unicode_preferences, events) == (
        "ＦＵＬＬＷＩＤＴＨ",
    )


def test_preference_queries_aggregate_unicode_equivalent_counters() -> None:
    unicode_preferences = HistoryPreferencesV1(
        6,
        6,
        {},
        {},
        {"Aimer": 3, "ＡＩＭＥＲ": 3, "Other Artist": 5},
        {},
    )

    assert preference_search_queries(unicode_preferences, limit=1) == ("Aimer",)


def test_preference_queries_aggregate_whitespace_equivalent_counters() -> None:
    whitespace_preferences = HistoryPreferencesV1(
        6,
        6,
        {},
        {},
        {"Aimer": 3, "  Aimer  ": 3, "Other Artist": 5},
        {},
    )

    assert preference_search_queries(whitespace_preferences, limit=1) == (
        "Aimer",
    )


def test_preference_queries_aggregate_latin_diacritic_equivalents() -> None:
    accent_preferences = HistoryPreferencesV1(
        11,
        0,
        {},
        {},
        {"Beyoncé": 3, "Beyonce": 3, "Other Artist": 5},
        {},
    )

    assert preference_search_queries(accent_preferences, limit=1) == (
        "Beyoncé",
    )


def test_preference_queries_deduplicate_latin_diacritic_event_variants() -> None:
    accent_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"Beyoncé": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "Beyonce",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(accent_preferences, events) == (
        "Beyoncé",
    )


def test_preference_queries_deduplicate_smart_apostrophe_variants() -> None:
    apostrophe_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"Guns N’ Roses": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "Guns N' Roses",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(apostrophe_preferences, events) == (
        "Guns N’ Roses",
    )


def test_preference_queries_deduplicate_typographic_dash_variants() -> None:
    dash_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"AC\u2013DC": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "AC-DC",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(dash_preferences, events) == (
        "AC\u2013DC",
    )


def test_preference_queries_deduplicate_unicode_minus_variants() -> None:
    minus_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"AC−DC": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "AC-DC",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(minus_preferences, events) == (
        "AC−DC",
    )


def test_preference_queries_deduplicate_hyphen_spacing_variants() -> None:
    dash_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"AC – DC": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "AC-DC",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(dash_preferences, events) == (
        "AC – DC",
    )


def test_preference_queries_deduplicate_field_separator_spacing() -> None:
    separator_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"Nora Vale / Midnight Echo": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "Nora Vale/Midnight Echo",
            "2026-07-14T00:00:00Z",
            None,
        ),
        HistoryEventV1(
            "search",
            "Nora Vale Midnight Echo",
            "2026-07-13T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(separator_preferences, events) == (
        "Nora Vale / Midnight Echo",
        "Nora Vale Midnight Echo",
    )


def test_preference_queries_deduplicate_east_asian_quote_variants() -> None:
    quote_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"「Nora Vale」": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            '"Nora Vale"',
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(quote_preferences, events) == (
        "「Nora Vale」",
    )


def test_preference_queries_deduplicate_smart_double_quote_variants() -> None:
    quote_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"The “Band”": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            'The "Band"',
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(quote_preferences, events) == (
        "The “Band”",
    )


def test_preference_queries_deduplicate_emoji_variation_selectors() -> None:
    emoji_preferences = HistoryPreferencesV1(
        1,
        0,
        {},
        {},
        {"Band❤️": 1},
        {},
    )
    events = (
        HistoryEventV1(
            "search",
            "Band❤",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(emoji_preferences, events) == (
        "Band❤️",
    )


def test_preference_queries_exclude_selection_event_queries() -> None:
    selected = DiscoveryItemV1(
        "selected",
        "https://example.test/selected",
        "Selected title",
        "Selected artist",
        120,
        "",
        "music",
        "",
    )
    events = (
        HistoryEventV1(
            "selection",
            "selection-only query",
            "2026-07-14T00:00:01Z",
            selected,
        ),
        HistoryEventV1(
            "search",
            "actual search",
            "2026-07-14T00:00:00Z",
            None,
        ),
    )

    assert preference_search_queries(
        HistoryPreferencesV1(0, 0, {}, {}, {}, {}),
        events,
    ) == ("actual search",)
