from __future__ import annotations

import json
from pathlib import Path
import runpy
from urllib import parse

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "peertube-search"


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_ROOT / "provider.py"))


def test_peertube_manifest_requires_explicit_https_origin() -> None:
    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)

    assert provider.provider_id == "peertube-search"
    assert provider.hosts == frozenset()
    assert provider.permissions == ("network.peertube",)
    assert manifest["url_hosts"] == []
    assert provider.search_capability is not None
    assert provider.search_capability.source_scope == "https-origin"
    provider._require_search_network()


def test_peertube_search_uses_local_public_api_and_normalizes_results(
    monkeypatch,
) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    captured: dict[str, str] = {}

    monkeypatch.setitem(
        search.__globals__, "_public_addresses", lambda host: ("93.184.216.34",)
    )

    def fake_request(host: str, address: str, target: str):
        captured.update(host=host, address=address, target=target)
        return {
            "total": 21,
            "data": [
                {
                    "uuid": "4e32d323-4d12-4c04-9e31-708f16bb987a",
                    "name": "  Open   video  ",
                    "isLocal": True,
                    "isLive": False,
                    "nsfw": False,
                    "privacy": {"id": 1, "label": "Public"},
                    "state": {"id": 1, "label": "Published"},
                    "duration": 123,
                    "language": {"id": "zh", "label": "Chinese"},
                    "channel": {"displayName": "Open Channel"},
                    "thumbnails": [
                        {"fileUrl": "https://video.example/private-probe.jpg"}
                    ],
                },
                {
                    "uuid": "ec9443da-963b-4eab-a48d-54e1561f5e07",
                    "name": "Remote result",
                    "isLocal": False,
                },
            ],
        }

    monkeypatch.setitem(search.__globals__, "_request_json", fake_request)
    result = search(
        {
            "query": "open source",
            "limit": 20,
            "content_type": "video",
            "cursor": "",
            "source_scope": "https://video.example/",
        }
    )

    assert captured["host"] == "video.example"
    assert captured["address"] == "93.184.216.34"
    parsed = parse.urlsplit(captured["target"])
    assert parsed.path == "/api/v1/search/videos"
    assert parse.parse_qs(parsed.query) == {
        "search": ["open source"],
        "searchTarget": ["local"],
        "isLocal": ["true"],
        "start": ["0"],
        "count": ["20"],
    }
    assert result == {
        "items": [
            {
                "video_id": "4e32d323-4d12-4c04-9e31-708f16bb987a",
                "url": (
                    "https://video.example/videos/watch/"
                    "4e32d323-4d12-4c04-9e31-708f16bb987a"
                ),
                "title": "Open video",
                "artist": "Open Channel",
                "duration": 123,
                "language": "zh",
                "category": "video",
                "thumbnail_url": "",
            }
        ],
        "next_cursor": "",
    }


@pytest.mark.parametrize(
    "origin",
    (
        "http://video.example",
        "https://user@video.example",
        "https://video.example:8443",
        "https://video.example/subpath",
        "https://video.example/?token=secret",
        "https://127.0.0.1",
    ),
)
def test_peertube_origin_rejects_non_root_or_credentialed_urls(origin: str) -> None:
    validate = provider_namespace()["_validated_origin"]

    with pytest.raises(ValueError, match="HTTPS origin|non-public"):
        validate(origin)


def test_peertube_dns_rejects_private_or_mixed_resolution(monkeypatch) -> None:
    namespace = provider_namespace()
    public_addresses = namespace["_public_addresses"]
    socket_module = namespace["socket"]
    monkeypatch.setattr(
        socket_module,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )

    with pytest.raises(ValueError, match="non-public"):
        public_addresses("video.example")


def test_peertube_rejects_url_search_before_network(monkeypatch) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    def network(*_args, **_kwargs):
        pytest.fail("network should not be used")

    monkeypatch.setitem(search.__globals__, "_public_addresses", network)

    with pytest.raises(ValueError, match="not a URL"):
        search(
            {
                "query": "https://remote.example/videos/watch/123",
                "limit": 12,
                "content_type": "all",
                "cursor": "",
                "source_scope": "https://video.example",
            }
        )


def test_peertube_request_does_not_follow_redirects(monkeypatch) -> None:
    namespace = provider_namespace()
    request_json = namespace["_request_json"]
    closed: list[bool] = []

    class Response:
        status = 302

        def getheader(self, _name: str):
            return None

    class Connection:
        def __init__(self, host: str, address: str) -> None:
            assert (host, address) == ("video.example", "93.184.216.34")

        def request(self, method: str, target: str, *, headers):
            assert method == "GET"
            assert target.startswith("/api/v1/search/videos?")
            assert "Authorization" not in headers

        def getresponse(self):
            return Response()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setitem(
        request_json.__globals__, "_PinnedHTTPSConnection", Connection
    )

    with pytest.raises(ValueError, match="redirects are not followed"):
        request_json(
            "video.example",
            "93.184.216.34",
            "/api/v1/search/videos?search=test",
        )
    assert closed == [True]
