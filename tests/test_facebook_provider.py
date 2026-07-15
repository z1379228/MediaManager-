from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


def load_provider():
    path = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "facebook"
        / "provider.py"
    )
    spec = importlib.util.spec_from_file_location("facebook_provider_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (
            "https://m.facebook.com/watch/?v=123456",
            "https://www.facebook.com/watch/?v=123456",
        ),
        (
            "https://facebook.com/reel/123456",
            "https://www.facebook.com/reel/123456/",
        ),
        ("https://fb.watch/AbCd_123/", "https://fb.watch/AbCd_123/"),
    ),
)
def test_canonical_url_accepts_exact_public_video_forms(
    value: str, expected: str
) -> None:
    assert load_provider().canonical_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://www.facebook.com/reel/123456",
        "https://www.facebook.com/watch/?v=1&tracking=1",
        "https://www.facebook.com/reel/not-a-number",
        "https://www.facebook.com.evil.test/reel/123456",
        "https://user@www.facebook.com/reel/123456",
    ),
)
def test_canonical_url_rejects_nonpublic_or_ambiguous_forms(value: str) -> None:
    assert load_provider().canonical_url(value) is None


def test_analyze_returns_bounded_title_thumbnail_and_formats(monkeypatch) -> None:
    package = ModuleType("yt_dlp")

    captured: list[dict[str, object]] = []

    class YoutubeDL:
        def __init__(self, options):
            captured.append(options)
            assert options["noplaylist"] is True

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, url, download):
            assert url == "https://www.facebook.com/reel/123456/"
            assert download is False
            return {
                "id": "123456",
                "title": "Public video",
                "duration": 61,
                "uploader": "Public page",
                "thumbnail": "https://scontent.xx.fbcdn.net/preview.jpg",
                "formats": [
                    {
                        "format_id": "720p",
                        "ext": "mp4",
                        "width": 1280,
                        "height": 720,
                        "fps": 30,
                        "vcodec": "h264",
                        "acodec": "aac",
                        "filesize": 1024,
                        "language": "en",
                    }
                ],
                "subtitles": {"zh-TW": [{"url": "https://example.invalid"}]},
            }

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)

    provider = load_provider()
    target = object()
    monkeypatch.setattr(provider, "_browser_impersonation_target", lambda: target)
    result = provider.analyze(
        {"url": "https://facebook.com/reel/123456"}
    )

    assert result["title"] == "Public video"
    assert result["thumbnail"] == "https://scontent.xx.fbcdn.net/preview.jpg"
    assert result["audio_languages"] == ["en"]
    assert result["subtitle_languages"] == ["zh-TW"]
    assert result["formats"][0]["height"] == 720
    assert captured[0]["impersonate"] is target


def test_real_ytdlp_accepts_programmatic_impersonation_target() -> None:
    pytest.importorskip("curl_cffi")
    from yt_dlp import YoutubeDL
    from yt_dlp.networking.impersonate import ImpersonateTarget

    target = load_provider()._browser_impersonation_target()

    assert isinstance(target, ImpersonateTarget)
    with YoutubeDL({"quiet": True, "impersonate": target}):
        pass


def test_parse_failure_explains_public_page_requirement(monkeypatch) -> None:
    package = ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, _url, download):
            assert download is False
            raise RuntimeError("Cannot parse data")

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)

    provider = load_provider()
    monkeypatch.setattr(provider, "_browser_impersonation_target", lambda: object())

    with pytest.raises(RuntimeError, match="不會讀取 Cookie"):
        provider.analyze({"url": "https://facebook.com/reel/123456"})


def test_parse_failure_explains_missing_impersonation_support(monkeypatch) -> None:
    package = ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, _url, download):
            assert download is False
            raise RuntimeError("Cannot parse data")

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)
    provider = load_provider()
    monkeypatch.setattr(provider, "_browser_impersonation_target", lambda: None)

    with pytest.raises(RuntimeError, match="未偵測到 curl-cffi"):
        provider.analyze({"url": "https://facebook.com/reel/123456"})


def test_thumbnail_rejects_non_facebook_cdn() -> None:
    provider = load_provider()
    assert provider._thumbnail("https://example.com/preview.jpg") == ""
    assert provider._thumbnail("https://fbcdn.net.evil.test/preview.jpg") == ""
