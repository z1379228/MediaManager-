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
