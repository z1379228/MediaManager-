from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys
from types import ModuleType

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "generic-ytdlp"


@pytest.mark.parametrize(
    "url",
    (
        "https://vimeo.com/123",
        "https://www.dailymotion.com/video/example",
        "https://soundcloud.com/artist/track",
        "https://www.tiktok.com/@artist/video/123",
        "https://clips.twitch.tv/Example",
    ),
)
def test_generic_provider_accepts_only_explicit_matrix_hosts(url: str) -> None:
    provider = SubprocessDownloadProvider(
        PROVIDER_ROOT,
        application_root=ROOT,
    )

    assert provider.provider_id == "generic-ytdlp"
    assert provider.supports(url)


@pytest.mark.parametrize(
    "url",
    (
        "https://geo.dailymotion.com/player/x123.html?video=x84sh87",
        "https://m.soundcloud.com/artist/track",
        (
            "https://w.soundcloud.com/player/?"
            "url=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
        ),
        "https://vt.tiktok.com/ZSexample/",
        "https://player.twitch.tv/?video=v40464143&parent=example.com",
        "https://go.twitch.tv/videos/40464143",
    ),
)
def test_generic_provider_accepts_verified_official_media_subdomains(
    url: str,
) -> None:
    provider = SubprocessDownloadProvider(
        PROVIDER_ROOT,
        application_root=ROOT,
    )

    assert provider.supports(url)


@pytest.mark.parametrize(
    "url",
    (
        "https://www.youtube.com/watch?v=example",
        "https://www.bilibili.com/video/BVexample",
        "https://www.facebook.com/watch/?v=123",
        "https://www.instagram.com/reel/example",
        "https://x.com/example/status/123",
        "https://twitter.com/example/status/123",
        "https://user:secret@vimeo.com/123",
        "https://vimeo.com:99999/123",
        "https://touch.dailymotion.com/video/example",
        "https://w.soundcloud.com/player/",
        (
            "https://w.soundcloud.com/player/?"
            "URL=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
        ),
        (
            "https://w.soundcloud.com/player/?"
            "%75rl=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
        ),
        "https://w.soundcloud.com/player/?url=https%3A%2F%2Fevil.test%2Ftrack",
        (
            "https://w.soundcloud.com/player/?"
            "url=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F1&"
            "url=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F2"
        ),
    ),
)
def test_generic_provider_rejects_excluded_or_credential_urls(url: str) -> None:
    provider = SubprocessDownloadProvider(
        PROVIDER_ROOT,
        application_root=ROOT,
    )

    assert not provider.supports(url)


def test_site_matrix_matches_manifest_and_installed_extractors() -> None:
    from yt_dlp.extractor import gen_extractor_classes

    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    matrix = json.loads(
        (PROVIDER_ROOT / "site-matrix.json").read_text(encoding="utf-8")
    )
    matrix_hosts = {
        host for site in matrix["sites"] for host in site["hosts"]
    }
    extractor_names = {
        str(getattr(extractor, "IE_NAME", "")).casefold()
        for extractor in gen_extractor_classes()
    }

    assert matrix["provider_id"] == manifest["provider_id"]
    assert matrix_hosts == set(manifest["url_hosts"])
    meta_exclusion = next(
        item
        for item in matrix["excluded"]
        if item["site_id"] == "facebook-instagram-threads"
    )
    assert meta_exclusion["reason"].startswith("Excluded from automated access")
    assert not matrix_hosts.intersection(
        {"facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com"}
    )
    for site in matrix["sites"]:
        prefix = site["extractor_prefix"].casefold()
        assert any(name.startswith(prefix) for name in extractor_names)
        assert site["support_status"] in {
            "verified-public-analysis",
            "beta-offline-contract",
        }
        assert isinstance(site["last_live_check"], str)


def test_soundcloud_widget_allowlist_matches_installed_extractor() -> None:
    from yt_dlp.extractor import gen_extractor_classes

    extractor = next(
        item
        for item in gen_extractor_classes()
        if str(getattr(item, "IE_NAME", "")).casefold() == "soundcloudembed"
    )
    supported = (
        "https://w.soundcloud.com/player/?"
        "url=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
    )
    unsupported = (
        "https://w.soundcloud.com/player/?"
        "URL=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
    )
    encoded_key = (
        "https://w.soundcloud.com/player/?"
        "%75rl=https%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F293"
    )

    assert extractor.suitable(supported)
    assert not extractor.suitable(unsupported)
    assert not extractor.suitable(encoded_key)


def test_generic_analyze_is_bounded_and_does_not_expand_playlists(
    monkeypatch,
) -> None:
    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, url, *, download):
            assert url == "https://vimeo.com/123"
            assert not download
            return {
                "id": "x" * 120,
                "title": "Example",
                "duration": 90,
                "uploader": "Artist",
                "webpage_url": url,
                "description": "d" * 30_000,
                "chapters": [
                    {"start_time": 0, "end_time": 2, "title": "Part"}
                ],
            }

    fake_module = ModuleType("yt_dlp")
    fake_module.YoutubeDL = FakeYoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", fake_module)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["analyze"]({"url": "https://vimeo.com/123"})

    assert len(result["id"]) == 100
    assert len(result["description"]) == 20_000
    assert result["chapters"][0]["start_time"] == 0
    assert result["chapters"][0]["title"] == "Part"
    assert captured[0]["noplaylist"] is True
    assert captured[0]["skip_download"] is True
