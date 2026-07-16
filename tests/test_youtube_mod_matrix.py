from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import ModuleType

import pytest

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.downloads.capabilities import builtin_download_capability
from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
YOUTUBE_MOD_IDS = (
    "youtube",
    "youtube-search",
    "youtube-history",
    "youtube-recovery",
    "youtube-similar",
    "youtube-player",
    "youtube-auto-split",
)
ROUTED_YOUTUBE_MOD_IDS = (
    "youtube",
    "youtube-search",
    "youtube-player",
    "youtube-auto-split",
)
YOUTUBE_HOSTS = (
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
)
MUSIC_PLAYLIST_URL = (
    "https://music.youtube.com/watch?v=zqMOLz9q7Ig"
    "&list=PL2yqXecZHhEYKaKiTSsfUhEeqeAm89wcp"
)


def _namespace(provider_id: str) -> dict[str, object]:
    return runpy.run_path(
        str(ROOT / "mod" / "builtin" / provider_id / "provider.py")
    )


def test_youtube_download_mod_routes_only_exact_hosts_without_authority_tricks() -> None:
    provider = SubprocessDownloadProvider(
        ROOT / "mod" / "builtin" / "youtube",
        application_root=ROOT,
    )

    for url in (
        "https://youtube.com/watch?v=example",
        "https://www.youtube.com/watch?v=example",
        "https://m.youtube.com/watch?v=example",
        MUSIC_PLAYLIST_URL,
        "https://youtu.be/example",
        "https://www.youtube-nocookie.com/embed/example",
    ):
        assert provider.supports(url), url

    for url in (
        "https://youtube.com.evil.test/watch?v=example",
        "https://music.youtube.com.evil.test/watch?v=example",
        "https://evil.test/?next=https://youtube.com/watch?v=example",
        "https://user@youtube.com/watch?v=example",
        "https://user:password@youtube.com/watch?v=example",
        "https://youtube.com:443/watch?v=example",
        "https://youtube.com:444/watch?v=example",
        "javascript:https://youtube.com/watch?v=example",
    ):
        assert not provider.supports(url), url


def test_routed_youtube_mods_share_the_same_exact_host_contract() -> None:
    for provider_id in ROUTED_YOUTUBE_MOD_IDS:
        root = ROOT / "mod" / "builtin" / provider_id
        manifest = json.loads((root / "provider.json").read_text(encoding="utf-8"))
        provider = SubprocessDownloadProvider(root, application_root=ROOT)

        assert tuple(manifest["url_hosts"]) == YOUTUBE_HOSTS
        assert provider.hosts == frozenset(YOUTUBE_HOSTS)
        assert provider.supports(MUSIC_PLAYLIST_URL)
        assert provider.supports("https://m.youtube.com/watch?v=example")
        assert provider.supports("https://www.youtube-nocookie.com/embed/example")


def test_music_watch_playlist_is_forwarded_to_analysis_and_playlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool, dict[str, object]]] = []
    package = ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, url: str, download: bool):
            calls.append((url, download, self.options))
            if self.options.get("extract_flat") == "in_playlist":
                return {
                    "entries": [
                        {
                            "id": "first",
                            "url": "first",
                            "title": "First",
                            "duration": 60,
                        },
                        {
                            "id": "private",
                            "url": "private",
                            "title": "Private",
                            "availability": "private",
                        },
                    ]
                }
            return {
                "id": "zqMOLz9q7Ig",
                "title": "Music item",
                "duration": 120,
                "uploader": "Artist",
                "formats": [],
            }

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)
    namespace = _namespace("youtube")

    analysis = namespace["analyze"]({"url": MUSIC_PLAYLIST_URL})
    playlist = namespace["playlist"](
        {"url": MUSIC_PLAYLIST_URL, "limit": 25}
    )

    assert analysis["id"] == "zqMOLz9q7Ig"
    assert calls[0][0:2] == (MUSIC_PLAYLIST_URL, False)
    assert calls[1][0:2] == (MUSIC_PLAYLIST_URL, False)
    assert calls[1][2]["playlistend"] == 25
    assert calls[1][2]["extract_flat"] == "in_playlist"
    assert playlist[0]["url"] == "https://www.youtube.com/watch?v=first"
    assert playlist[0]["available"] is True
    assert playlist[1]["available"] is False


def test_music_playlist_segment_download_stays_single_item_and_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    package = ModuleType("yt_dlp")
    utils = ModuleType("yt_dlp.utils")

    def download_range_func(callback, ranges):
        captured["range_args"] = (callback, ranges)
        return "bounded-range"

    class YoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            captured["options"] = options
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, url: str, download: bool):
            captured["url"] = url
            assert download is True
            path = Path(str(self.options["outtmpl"]).replace("%(ext)s", "mp4"))
            path.write_bytes(b"media")
            return {"filepath": str(path)}

        @staticmethod
        def prepare_filename(info):
            return info["filepath"]

    package.YoutubeDL = YoutubeDL
    utils.download_range_func = download_range_func
    monkeypatch.setitem(sys.modules, "yt_dlp", package)
    monkeypatch.setitem(sys.modules, "yt_dlp.utils", utils)
    namespace = _namespace("youtube")

    result = namespace["download"](
        {
            "url": MUSIC_PLAYLIST_URL,
            "output_dir": str(tmp_path),
            "output_filename": "segment.mp4",
            "format_preset": "video-720",
            "subtitle_mode": "all",
            "subtitle_languages": [],
            "start_time": 5.0,
            "end_time": 10.0,
        }
    )

    options = captured["options"]
    assert Path(result).read_bytes() == b"media"
    assert captured["url"] == MUSIC_PLAYLIST_URL
    assert options["noplaylist"] is True
    assert options["download_ranges"] == "bounded-range"
    assert options["force_keyframes_at_cuts"] is True
    assert options["subtitleslangs"] == ["all"]
    assert captured["range_args"] == (None, [(5.0, 10.0)])


def test_youtube_search_contract_returns_unicode_results_and_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    package = ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        @staticmethod
        def extract_info(url: str, download: bool):
            captured["url"] = url
            assert download is False
            return {
                "entries": [
                    {
                        "id": "one",
                        "title": "幻月環 Official",
                        "channel": "Channel",
                        "duration": 180,
                    },
                    {"id": "two", "title": "Second", "duration": 60},
                    {"id": "three", "title": "Third", "duration": 30},
                ]
            }

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)
    namespace = _namespace("youtube-search")

    result = namespace["search"](
        {"query": "幻月環", "limit": 2, "content_type": "all"}
    )

    assert captured["url"] == "ytsearch3:幻月環"
    assert [item["video_id"] for item in result["items"]] == ["one", "two"]
    assert result["items"][0]["thumbnail_url"].endswith("/one/mqdefault.jpg")
    assert result["next_cursor"] == "2"


def test_all_youtube_mods_are_pinned_and_included_by_frozen_build() -> None:
    for provider_id in YOUTUBE_MOD_IDS:
        provider_root = ROOT / "mod" / "builtin" / provider_id
        pinned = BUILTIN_PROVIDER_HASHES[provider_id]
        assert {"provider.py", "provider.json"} <= set(pinned)
        for relative, digest in pinned.items():
            path = provider_root / relative
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest

    spec = (ROOT / "MediaManager.spec").read_text(encoding="utf-8")
    assert "('mod/builtin', 'mod/builtin')" in spec
    assert "collect_submodules('yt_dlp.extractor')" in spec
    assert "collect_submodules('yt_dlp.postprocessor')" in spec
    assert "collect_submodules('yt_dlp_ejs')" in spec
    assert "copy_metadata('yt-dlp-ejs')" in spec
    assert "collect_submodules('curl_cffi')" in spec
    assert "copy_metadata('curl-cffi')" in spec


def test_youtube_download_capability_covers_batch_media_options() -> None:
    capability = builtin_download_capability("youtube")

    assert capability.sites == ("youtube",)
    assert capability.supports_playlist is True
    assert capability.supports_segments is True
    assert capability.supports_resume is True
    assert capability.max_batch_size == 500
    assert {"best", "video-1080", "video-720", "video-480"} <= set(
        capability.format_presets
    )
    assert {"audio-m4a", "audio-mp3"} <= set(capability.format_presets)
    assert {"none", "selected", "all"} <= set(capability.subtitle_modes)
