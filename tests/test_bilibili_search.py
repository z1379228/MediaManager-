from __future__ import annotations

import json
from pathlib import Path
import runpy
from urllib import error, parse

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "bilibili-search"


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_ROOT / "provider.py"))


def test_bilibili_search_manifest_is_independent_from_youtube() -> None:
    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)

    assert provider.provider_id == "bilibili-search"
    assert manifest["permissions"] == ["network.bilibili"]
    assert "network.youtube" not in provider.permissions
    assert provider.search_capability is not None
    assert provider.search_capability.sites == ("bilibili",)
    provider._require_search_network()


def test_bilibili_search_normalizes_official_results(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    captured: dict[str, object] = {}

    def fake_fetch(query: str, page: int, page_size: int):
        captured.update(query=query, page=page, page_size=page_size)
        return {
            "numResults": 60,
            "result": [
                {
                    "bvid": "BV1zW411u7T6",
                    "title": ' <em class="keyword">進擊</em> &amp; 巨人 ',
                    "author": " 作者 ",
                    "duration": "2:03",
                    "pic": "//i0.hdslb.com/bfs/archive/example.jpg",
                },
                {"bvid": "not-a-bvid", "title": "ignored"},
            ],
        }

    monkeypatch.setitem(search.__globals__, "fetch_search", fake_fetch)
    result = search(
        {"query": "進擊的巨人", "limit": 20, "content_type": "video", "cursor": ""}
    )

    assert captured == {"query": "進擊的巨人", "page": 1, "page_size": 20}
    assert result["next_cursor"] == "2:20"
    assert result["items"] == [
        {
            "video_id": "BV1zW411u7T6",
            "url": "https://www.bilibili.com/video/BV1zW411u7T6",
            "title": "進擊 & 巨人",
            "artist": "作者",
            "duration": 123,
            "language": "",
            "category": "video",
            "thumbnail_url": "https://i0.hdslb.com/bfs/archive/example.jpg",
        }
    ]


def test_bilibili_search_cursor_and_music_hint_are_bounded(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    captured: list[tuple[str, int, int]] = []

    def fake_fetch(query: str, page: int, page_size: int):
        captured.append((query, page, page_size))
        return {"numResults": 999, "result": []}

    monkeypatch.setitem(search.__globals__, "fetch_search", fake_fetch)
    result = search(
        {"query": "工作用", "limit": 20, "content_type": "music", "cursor": "2:20"}
    )

    assert captured == [("工作用 音樂", 2, 20)]
    assert result == {"items": [], "next_cursor": ""}
    with pytest.raises(ValueError, match="cursor"):
        search(
            {"query": "test", "limit": 20, "content_type": "all", "cursor": "2:50"}
        )


def test_bilibili_search_request_is_limited_to_official_api(monkeypatch) -> None:
    namespace = provider_namespace()
    fetch_search = namespace["fetch_search"]
    request_module = namespace["request"]
    seen: list[str] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self) -> str:
            return "https://api.bilibili.com/x/web-interface/search/type"

        def read(self, _limit: int) -> bytes:
            return b'{"code":0,"data":{"result":[],"numResults":0}}'

    class Opener:
        def open(self, outgoing, *, timeout: int):
            seen.append(outgoing.full_url)
            assert timeout == 20
            return Response()

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    assert fetch_search("test query", 1, 12)["result"] == []
    parsed = parse.urlsplit(seen[0])
    assert parsed.scheme == "https" and parsed.hostname == "api.bilibili.com"
    assert parse.parse_qs(parsed.query)["keyword"] == ["test query"]


def test_bilibili_search_rejects_cross_site_redirect_before_following() -> None:
    namespace = provider_namespace()
    handler = namespace["_OfficialRedirectHandler"]()
    outgoing = namespace["request"].Request(
        "https://api.bilibili.com/x/web-interface/search/type"
    )

    with pytest.raises(ValueError, match="left the official API"):
        handler.redirect_request(
            outgoing,
            None,
            302,
            "Found",
            {},
            "https://evil.example/redirected",
        )


def test_bilibili_search_reports_official_verification_without_fallback(
    monkeypatch,
) -> None:
    namespace = provider_namespace()
    fetch_search = namespace["fetch_search"]
    request_module = namespace["request"]

    class Opener:
        def open(self, outgoing, *, timeout: int):
            raise error.HTTPError(outgoing.full_url, 412, "blocked", {}, None)

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    with pytest.raises(RuntimeError, match="no YouTube fallback"):
        fetch_search("test query", 1, 12)
