from __future__ import annotations

import json
from pathlib import Path
import runpy
from urllib import error, parse

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "ani-gamer-search"


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_ROOT / "provider.py"))


def test_ani_gamer_search_manifest_is_official_open_only_source() -> None:
    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)

    assert provider.provider_id == "ani-gamer-search"
    assert manifest["permissions"] == ["network.ani-gamer"]
    assert "network.youtube" not in provider.permissions
    assert provider.search_capability is not None
    assert provider.search_capability.sites == ("ani-gamer",)
    assert provider.search_capability.content_types == ("all", "video")
    assert not provider.search_capability.audio_preview
    assert not provider.search_capability.video_preview
    provider._require_search_network()


def test_ani_gamer_search_parses_only_canonical_official_results(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    html = """
    <a href='animeRef.php?sn=113784' class='theme-list-main'>
      <img class='theme-img lazyload'
           data-src='https://p2.bahamut.com.tw/B/ACG/c/13/example.JPG'
           alt='舊標題'>
      <p class='theme-name'>劇場版「進擊的巨人」完結篇</p>
    </a>
    <a href='https://evil.example/animeRef.php?sn=1' class='theme-list-main'>
      <p class='theme-name'>不可接受</p>
    </a>
    """
    monkeypatch.setitem(search.__globals__, "fetch_html", lambda _query: html)

    result = search(
        {"query": "進擊的巨人", "limit": 12, "content_type": "video", "cursor": ""}
    )

    assert result["next_cursor"] == ""
    assert result["items"] == [
        {
            "video_id": "ani-113784",
            "url": "https://ani.gamer.com.tw/animeRef.php?sn=113784",
            "title": "劇場版「進擊的巨人」完結篇",
            "artist": "巴哈姆特動畫瘋",
            "duration": None,
            "language": "",
            "category": "video",
            "thumbnail_url": "https://p2.bahamut.com.tw/B/ACG/c/13/example.JPG",
        }
    ]


def test_ani_gamer_search_rejects_noncanonical_result_urls() -> None:
    safe_result_url = provider_namespace()["safe_result_url"]

    assert safe_result_url("animeRef.php?sn=123") == (
        "https://ani.gamer.com.tw/animeRef.php?sn=123",
        "123",
    )
    assert safe_result_url("https://evil.example/animeRef.php?sn=123") is None
    assert safe_result_url("animeVideo.php?sn=123") is None
    assert safe_result_url("animeRef.php?sn=123&extra=1") is None


def test_ani_gamer_accepts_canonical_official_series_url_without_network(
    monkeypatch,
) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    monkeypatch.setitem(
        search.__globals__,
        "fetch_page",
        lambda _url: pytest.fail("direct series URL must not contact AniGamer"),
    )
    result = search(
        {
            "query": "https://ani.gamer.com.tw/animeRef.php?sn=114096",
            "limit": 12,
            "content_type": "video",
            "cursor": "",
        }
    )
    assert result["next_cursor"] == ""
    assert result["items"][0]["video_id"] == "ani-114096"
    assert result["items"][0]["url"].endswith("animeRef.php?sn=114096")


def test_ani_gamer_rejects_unsupported_music_scope_without_network(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    monkeypatch.setitem(
        search.__globals__,
        "fetch_html",
        lambda _query: pytest.fail("music scope must not contact AniGamer"),
    )

    with pytest.raises(ValueError, match="content type"):
        search(
            {
                "query": "x" * 200,
                "limit": 12,
                "content_type": "music",
                "cursor": "",
            }
        )


def test_ani_gamer_request_is_limited_to_official_search(monkeypatch) -> None:
    namespace = provider_namespace()
    fetch_html = namespace["fetch_html"]
    request_module = namespace["request"]
    seen: list[str] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self) -> str:
            return "https://ani.gamer.com.tw/search.php?keyword=test"

        def read(self, _limit: int) -> bytes:
            return b"<html></html>"

    class Opener:
        def open(self, outgoing, *, timeout: int):
            seen.append(outgoing.full_url)
            assert timeout == 20
            return Response()

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    assert fetch_html("test query") == "<html></html>"
    parsed = parse.urlsplit(seen[0])
    assert parsed.scheme == "https" and parsed.hostname == "ani.gamer.com.tw"
    assert parse.parse_qs(parsed.query)["keyword"] == ["test query"]


def test_ani_gamer_search_maps_cloudflare_403_to_browser_verification(
    monkeypatch,
) -> None:
    namespace = provider_namespace()
    fetch_html = namespace["fetch_html"]
    request_module = namespace["request"]

    class Opener:
        def open(self, outgoing, *, timeout: int):
            assert timeout == 20
            raise error.HTTPError(
                outgoing.full_url,
                403,
                "Forbidden",
                {"cf-mitigated": "challenge"},
                None,
            )

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    with pytest.raises(
        RuntimeError,
        match="ani-gamer-browser-verification-required",
    ):
        fetch_html("test query")


def test_ani_gamer_catalog_queries_filter_home_sections(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    html = """
    <h1>近期熱播</h1>
    <a href='animeRef.php?sn=100' class='theme-list-main'>
      <img class='theme-img' data-src='https://p2.bahamut.com.tw/B/ACG/a.JPG' alt='熱門作品'>
      <p class='theme-name'>熱門作品</p>
    </a>
    <h1>新上架</h1>
    <a href='animeRef.php?sn=200' class='theme-list-main'>
      <img class='theme-img' data-src='https://p2.bahamut.com.tw/B/ACG/b.JPG' alt='新作品'>
      <p class='theme-name'>新作品</p>
    </a>
    """
    monkeypatch.setitem(search.__globals__, "fetch_page", lambda _url: html)

    recent = search(
        {
            "query": namespace["RECENT_QUERY"],
            "limit": 12,
            "content_type": "video",
            "cursor": "",
        }
    )
    new = search(
        {
            "query": namespace["NEW_QUERY"],
            "limit": 12,
            "content_type": "video",
            "cursor": "",
        }
    )

    assert [item["title"] for item in recent["items"]] == ["熱門作品"]
    assert [item["title"] for item in new["items"]] == ["新作品"]


def test_ani_gamer_catalog_query_is_strictly_bounded(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    monkeypatch.setitem(
        search.__globals__,
        "fetch_page",
        lambda _url: pytest.fail("invalid catalog URL must not contact AniGamer"),
    )

    with pytest.raises(ValueError, match="catalog URL"):
        search(
            {
                "query": "https://ani.gamer.com.tw/animeList.php?sort=1",
                "limit": 12,
                "content_type": "video",
                "cursor": "",
            }
        )


def test_ani_gamer_rejects_cross_site_redirect_before_following() -> None:
    namespace = provider_namespace()
    handler = namespace["_OfficialRedirectHandler"]()
    outgoing = namespace["request"].Request(
        "https://ani.gamer.com.tw/search.php?keyword=test"
    )

    with pytest.raises(ValueError, match="left the official site"):
        handler.redirect_request(
            outgoing,
            None,
            302,
            "Found",
            {},
            "https://evil.example/redirected",
        )
