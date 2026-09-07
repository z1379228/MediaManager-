from __future__ import annotations

from pathlib import Path
import runpy
from urllib.parse import parse_qs, urlsplit

import pytest


PROVIDER_PATH = (
    Path(__file__).parents[1]
    / "mod"
    / "builtin"
    / "youtube-search"
    / "provider.py"
)


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_PATH))


def test_search_target_routes_only_music_scope_to_youtube_music_songs() -> None:
    namespace = provider_namespace()
    search_target = namespace["search_target"]

    target = urlsplit(search_target("周杰倫 / 晴天", "music", 13))
    assert (target.scheme, target.hostname, target.path, target.fragment) == (
        "https",
        "music.youtube.com",
        "/search",
        "songs",
    )
    assert parse_qs(target.query) == {"q": ["周杰倫 / 晴天"]}
    assert search_target("教學影片", "video", 13) == "ytsearch13:教學影片"
    assert search_target("教學影片", "all", 13) == "ytsearch13:教學影片"


def test_music_search_target_preserves_the_bounded_query_value() -> None:
    namespace = provider_namespace()
    search_target = namespace["search_target"]

    maximum_query = "x" * 200
    target = urlsplit(search_target(maximum_query, "music", 50))

    assert parse_qs(target.query) == {"q": [maximum_query]}


def test_music_signals_do_not_match_inside_unrelated_latin_words() -> None:
    namespace = provider_namespace()
    result_category = namespace["result_category"]

    assert result_category(
        {"title": "Concrete mixing tutorial"},
        "all",
        "DIY",
    ) == "video"
    assert result_category(
        {"title": "Cloud cost breakdown"},
        "all",
        "FinOps",
    ) == "video"


@pytest.mark.parametrize(
    "query",
    (
        "Aimer remix",
        "top songs 2026",
        "new albums 2026",
        "focus playlists",
        "DJ mixes",
        "Final Fantasy OST",
        "Original soundtrack",
        "movie soundtracks",
        "karaoke version",
    ),
)
def test_music_signals_include_explicit_common_word_forms(query: str) -> None:
    namespace = provider_namespace()
    result_category = namespace["result_category"]

    assert result_category({"title": query}, "all", "") == "music"


@pytest.mark.parametrize(
    "channel",
    ("Example Artist - Topic", "Example Artist – Topic", "Example Artist − Topic"),
)
def test_all_scope_classifies_youtube_topic_channels_as_music(
    channel: str,
) -> None:
    namespace = provider_namespace()
    result_category = namespace["result_category"]

    assert result_category(
        {"title": "Example Track", "channel": channel},
        "all",
        "Example Artist",
    ) == "music"


@pytest.mark.parametrize("channel", ("Topic World", "Discussion off-topic", ""))
def test_all_scope_does_not_treat_general_topic_text_as_music(
    channel: str,
) -> None:
    namespace = provider_namespace()
    result_category = namespace["result_category"]

    assert result_category(
        {"title": "Example Track", "channel": channel},
        "all",
        "Example Artist",
    ) == "video"


def test_search_scope_validates_request_and_classifies_results() -> None:
    namespace = provider_namespace()
    search_scope = namespace["search_scope"]
    result_category = namespace["result_category"]

    assert search_scope({}) == "all"
    assert search_scope({"content_type": "music"}) == "music"
    with pytest.raises(ValueError, match="content type"):
        search_scope({"content_type": "unknown"})

    assert result_category({"title": "Official Audio"}, "all", "歌手") == "music"
    assert result_category({"title": "軟體教學"}, "all", "Python") == "video"
    assert result_category({"title": "任意內容"}, "music", "關鍵字") == "music"


def test_search_offset_is_bounded_and_page_aligned() -> None:
    namespace = provider_namespace()
    search_offset = namespace["search_offset"]

    assert search_offset({}) == 0
    assert search_offset({"cursor": "20"}) == 20
    with pytest.raises(ValueError, match="cursor"):
        search_offset({"cursor": "200"})
    with pytest.raises(ValueError, match="cursor"):
        search_offset({"cursor": "../../outside"})
