from __future__ import annotations

import json
from pathlib import Path
import runpy
from urllib import parse

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "ani-gamer-episodes"


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_ROOT / "provider.py"))


def test_episode_manifest_is_paged_official_open_only_source() -> None:
    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)

    assert provider.provider_id == "ani-gamer-episodes"
    assert manifest["permissions"] == ["network.ani-gamer"]
    assert provider.search_capability is not None
    assert provider.search_capability.pagination == "offset"
    assert not provider.search_capability.audio_preview
    assert not provider.search_capability.video_preview
    provider._require_search_network()


def test_episode_parser_lists_only_official_season_links(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    html = """
    <html><head><title>幼女戰記 2 [1] 線上看 - 巴哈姆特動畫瘋</title></head>
    <body>
      <img src="https://p2.bahamut.com.tw/B/ACG/c/64/cover.JPG" alt="幼女戰記 2">
      <section class="season">
        <a href="?sn=49943" data-ani-video-sn="49943">1</a>
        <a href="?sn=49944" data-ani-video-sn="49944">2</a>
        <a href="https://evil.example/?sn=1" data-ani-video-sn="1">惡意</a>
      </section>
    </body></html>
    """
    monkeypatch.setitem(
        search.__globals__,
        "fetch_html",
        lambda _url: ("https://ani.gamer.com.tw/animeVideo.php?sn=49943", html),
    )

    first = search(
        {
            "query": "https://ani.gamer.com.tw/animeRef.php?sn=114115",
            "limit": 1,
            "content_type": "video",
            "cursor": "",
        }
    )
    assert first["next_cursor"] == "1"
    assert first["items"][0]["url"] == (
        "https://ani.gamer.com.tw/animeVideo.php?sn=49943"
    )
    assert first["items"][0]["title"] == "幼女戰記 2 [1]"

    second = search(
        {
            "query": "https://ani.gamer.com.tw/animeRef.php?sn=114115",
            "limit": 1,
            "content_type": "video",
            "cursor": "1",
        }
    )
    assert second["next_cursor"] == ""
    assert second["items"][0]["video_id"] == "ani-episode-49944"


def test_episode_provider_rejects_cross_site_and_malformed_inputs(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    monkeypatch.setitem(
        search.__globals__,
        "fetch_html",
        lambda _url: pytest.fail("invalid input must not contact AniGamer"),
    )

    for invalid in (
        "https://evil.example/animeRef.php?sn=1",
        "https://ani.gamer.com.tw/animeRef.php?sn=1&extra=1",
        "https://ani.gamer.com.tw/animeList.php",
    ):
        with pytest.raises(ValueError, match="series URL"):
            search(
                {
                    "query": invalid,
                    "limit": 20,
                    "content_type": "video",
                    "cursor": "",
                }
            )

    with pytest.raises(ValueError, match="cursor"):
        search(
            {
                "query": "https://ani.gamer.com.tw/animeRef.php?sn=1",
                "limit": 20,
                "content_type": "video",
                "cursor": "../1",
            }
        )


def test_episode_request_stays_on_official_pages(monkeypatch) -> None:
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
            return "https://ani.gamer.com.tw/animeVideo.php?sn=49943"

        def read(self, _limit: int) -> bytes:
            return b"<html></html>"

    class Opener:
        def open(self, outgoing, *, timeout: int):
            seen.append(outgoing.full_url)
            assert timeout == 20
            return Response()

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    final, html = fetch_html("https://ani.gamer.com.tw/animeRef.php?sn=114115")
    assert final.endswith("animeVideo.php?sn=49943")
    assert html == "<html></html>"
    assert parse.urlsplit(seen[0]).hostname == "ani.gamer.com.tw"
