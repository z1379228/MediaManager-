from __future__ import annotations

import json
from pathlib import Path
import runpy
from urllib import parse

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "musicbrainz-metadata"


def provider_namespace() -> dict[str, object]:
    return runpy.run_path(str(PROVIDER_ROOT / "provider.py"))


def test_musicbrainz_manifest_is_a_bounded_optional_search_mod() -> None:
    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)

    assert provider.provider_id == "musicbrainz-metadata"
    assert manifest["permissions"] == ["network.musicbrainz"]
    assert provider.search_visibility == "manual"
    assert provider.search_capability is not None
    assert provider.search_capability.sites == ("musicbrainz",)
    assert provider.search_capability.content_types == ("music",)
    assert provider.search_capability.max_page_size == 10
    assert not provider.search_capability.audio_preview
    provider._require_search_network()


def test_musicbrainz_provider_normalizes_only_bounded_recordings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = provider_namespace()
    search = namespace["search"]
    monkeypatch.setitem(
        search.__globals__,
        "_request_json",
        lambda query, limit: {
            "recordings": [
                {
                    "id": "026fa041-3917-4c73-9079-ed16e36f20f8",
                    "title": " Song Title ",
                    "length": 178_000,
                    "artist-credit": [
                        {"name": "Artist X", "joinphrase": " feat. "},
                        {"artist": {"name": "Artist Y"}},
                    ],
                },
                {"id": "not-an-mbid", "title": "Ignored"},
            ]
        },
    )

    result = search(
        {
            "query": "Song Title Artist X",
            "limit": 5,
            "content_type": "music",
            "cursor": "",
        }
    )

    assert result == {
        "items": [
            {
                "video_id": "026fa041-3917-4c73-9079-ed16e36f20f8",
                "url": (
                    "https://musicbrainz.org/recording/"
                    "026fa041-3917-4c73-9079-ed16e36f20f8"
                ),
                "title": "Song Title",
                "artist": "Artist X feat. Artist Y",
                "duration": 178,
                "language": "",
                "category": "music",
                "thumbnail_url": "",
            }
        ],
        "next_cursor": "",
    }


def test_musicbrainz_request_uses_official_api_and_identifiable_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = provider_namespace()
    request_json = namespace["_request_json"]
    request_module = namespace["url_request"]
    observed: dict[str, object] = {}

    class Response:
        headers = {"Content-Length": "17"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self) -> str:
            return (
                "https://musicbrainz.org/ws/2/recording/"
                "?query=test&fmt=json&limit=3"
            )

        def read(self, limit: int) -> bytes:
            observed["read_limit"] = limit
            return b'{"recordings":[]}'

    class Opener:
        def open(self, outgoing, *, timeout: int):
            observed["url"] = outgoing.full_url
            observed["user_agent"] = outgoing.get_header("User-agent")
            observed["accept"] = outgoing.get_header("Accept")
            observed["timeout"] = timeout
            return Response()

    monkeypatch.setattr(
        request_module,
        "build_opener",
        lambda _handler: Opener(),
    )

    assert request_json("test recording", 3) == {"recordings": []}
    parsed = parse.urlsplit(str(observed["url"]))
    assert parsed.scheme == "https" and parsed.hostname == "musicbrainz.org"
    assert parsed.path == "/ws/2/recording/"
    assert parse.parse_qs(parsed.query) == {
        "query": ["test recording"],
        "fmt": ["json"],
        "limit": ["3"],
    }
    assert "MediaManager/39.0" in str(observed["user_agent"])
    assert "github.com/z1379228/MediaManager-" in str(observed["user_agent"])
    assert observed["accept"] == "application/json"
    assert observed["timeout"] == 15
    assert observed["read_limit"] == 512 * 1024 + 1


def test_musicbrainz_redirect_cannot_leave_the_official_api() -> None:
    namespace = provider_namespace()
    handler = namespace["_OfficialRedirectHandler"]()
    outgoing = namespace["url_request"].Request(
        "https://musicbrainz.org/ws/2/recording/?query=test"
    )

    with pytest.raises(ValueError, match="left the official API"):
        handler.redirect_request(
            outgoing,
            None,
            302,
            "Found",
            {},
            "https://127.0.0.1/private",
        )


def test_musicbrainz_search_rate_is_limited_per_provider_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.downloads.subprocess_provider as provider_module

    provider = SubprocessDownloadProvider(PROVIDER_ROOT, application_root=ROOT)
    now = [100.0]
    sleeps: list[float] = []
    provider._last_search_started = 99.25

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(provider_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(provider_module.time, "sleep", sleep)
    monkeypatch.setattr(
        provider,
        "_execute",
        lambda *_args, **_kwargs: {"items": [], "next_cursor": ""},
    )

    assert provider.search("first", limit=3, content_type="music") == ()
    assert provider.search("second", limit=3, content_type="music") == ()
    assert sleeps == pytest.approx([0.25, 1.0])


@pytest.mark.parametrize(
    "payload",
    (
        {"query": "", "limit": 5, "content_type": "music", "cursor": ""},
        {"query": "song", "limit": 11, "content_type": "music", "cursor": ""},
        {"query": "song", "limit": 5, "content_type": "video", "cursor": ""},
        {"query": "song", "limit": 5, "content_type": "music", "cursor": "1"},
    ),
)
def test_musicbrainz_provider_rejects_unbounded_search_options(
    payload: dict[str, object],
) -> None:
    search = provider_namespace()["search"]

    with pytest.raises(ValueError):
        search(payload)
