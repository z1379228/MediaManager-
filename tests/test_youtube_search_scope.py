from __future__ import annotations

from pathlib import Path
import runpy

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


def test_search_scope_adds_music_hint_only_when_explicitly_selected() -> None:
    namespace = provider_namespace()
    scoped_query = namespace["scoped_query"]

    assert scoped_query("周杰倫", "music") == "周杰倫 music"
    assert scoped_query("作業用 BGM", "music") == "作業用 BGM"
    assert scoped_query("教學影片", "video") == "教學影片"
    assert scoped_query("教學影片", "all") == "教學影片"


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
