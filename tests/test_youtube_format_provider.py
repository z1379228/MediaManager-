from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_provider():
    path = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "youtube"
        / "provider.py"
    )
    spec = importlib.util.spec_from_file_location("youtube_format_provider", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_ytdlp(monkeypatch, captured: list[dict[str, object]]) -> None:
    package = ModuleType("yt_dlp")
    utils = ModuleType("yt_dlp.utils")

    class YoutubeDL:
        def __init__(self, options):
            self.options = options
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, _url, download):
            assert download
            template = str(self.options["outtmpl"])
            codec = self.options.get("postprocessors", [{}])[0].get(
                "preferredcodec"
            )
            extension = (
                codec
                if codec in {"m4a", "mp3", "opus", "flac", "wav"}
                else str(self.options.get("merge_output_format") or "mp4")
            )
            path = Path(template.replace("%(ext)s", extension))
            path.write_bytes(b"media")
            return {"filepath": str(path)}

        def prepare_filename(self, info):
            return info["filepath"]

    package.YoutubeDL = YoutubeDL
    utils.download_range_func = lambda *_args: "range"
    monkeypatch.setitem(sys.modules, "yt_dlp", package)
    monkeypatch.setitem(sys.modules, "yt_dlp.utils", utils)


def request(tmp_path: Path, **changes):
    raw = {
        "url": "https://www.youtube.com/watch?v=example",
        "output_dir": str(tmp_path),
        "output_filename": "result.mp4",
        "format_preset": "video-720",
        "subtitle_mode": "selected",
        "subtitle_languages": ["zh-TW", "en"],
    }
    raw.update(changes)
    return raw


def test_video_preset_and_subtitles_map_to_bounded_ytdlp_options(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    path = load_provider().download(request(tmp_path))
    assert Path(path).read_bytes() == b"media"
    options = captured[0]
    assert "height<=720" in str(options["format"])
    assert options["writesubtitles"] is True
    assert options["writeautomaticsub"] is True
    assert options["subtitleslangs"] == ["zh-TW", "en"]
    assert options["continuedl"] is True
    assert options["nopart"] is False
    assert options["overwrites"] is False


def test_mp3_preset_uses_audio_postprocessor(tmp_path: Path, monkeypatch) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    path = load_provider().download(
        request(
            tmp_path,
            output_filename="",
            format_preset="audio-mp3",
            subtitle_mode="none",
            subtitle_languages=[],
        )
    )
    assert Path(path).suffix == ".mp3"
    assert captured[0]["postprocessors"][0]["preferredcodec"] == "mp3"


@pytest.mark.parametrize(
    ("preset", "codec", "quality"),
    (
        ("audio-m4a-256", "m4a", "256"),
        ("audio-mp3-320", "mp3", "320"),
        ("audio-opus", "opus", "160"),
        ("audio-flac", "flac", None),
        ("audio-wav", "wav", None),
    ),
)
def test_new_audio_presets_use_bounded_ffmpeg_outputs(
    tmp_path: Path,
    monkeypatch,
    preset: str,
    codec: str,
    quality: str | None,
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    path = load_provider().download(
        request(
            tmp_path,
            output_filename="",
            format_preset=preset,
            subtitle_mode="none",
            subtitle_languages=[],
        )
    )

    postprocessor = captured[0]["postprocessors"][0]
    assert Path(path).suffix == f".{codec}"
    assert postprocessor["preferredcodec"] == codec
    if quality is None:
        assert "preferredquality" not in postprocessor
    else:
        assert postprocessor["preferredquality"] == quality


def test_h264_preset_selects_avc1_and_aac_without_video_transcoding(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    load_provider().download(
        request(
            tmp_path,
            format_preset="video-h264-1080",
            subtitle_mode="none",
            subtitle_languages=[],
        )
    )

    options = captured[0]
    assert "vcodec^=avc1" in str(options["format"])
    assert "acodec^=mp4a" in str(options["format"])
    assert "postprocessors" not in options


@pytest.mark.parametrize(
    ("preset", "height"),
    (("video-1440", 1440), ("video-2160", 2160)),
)
def test_high_resolution_presets_remain_height_bounded(
    tmp_path: Path, monkeypatch, preset: str, height: int
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    load_provider().download(
        request(
            tmp_path,
            format_preset=preset,
            subtitle_mode="none",
            subtitle_languages=[],
        )
    )

    assert f"height<={height}" in str(captured[0]["format"])
    assert not str(captured[0]["format"]).endswith("/b")


def test_high_resolution_segment_keeps_separate_streams_bounded(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    load_provider().download(
        request(
            tmp_path,
            format_preset="video-2160",
            subtitle_mode="none",
            subtitle_languages=[],
            start_time=10,
            end_time=20,
        )
    )

    assert "bv*[height<=2160]" in str(captured[0]["format"])
    assert captured[0]["download_ranges"] == "range"


def test_provider_rejects_unbounded_subtitle_languages(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="subtitle options"):
        load_provider().download(
            request(tmp_path, subtitle_languages=["bad language"])
        )


def test_analysis_format_summaries_are_bounded_and_sorted() -> None:
    provider = load_provider()
    summaries = provider.format_summaries(
        {
            "formats": [
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "acodec": "aac",
                    "vcodec": "none",
                    "filesize": 100,
                },
                {
                    "format_id": "720p",
                    "ext": "mp4",
                    "width": 1280,
                    "height": 720,
                    "fps": 30,
                    "acodec": "aac",
                    "vcodec": "h264",
                    "filesize_approx": 1000,
                    "dynamic_range": "HDR10",
                },
            ]
        }
    )

    assert [item["format_id"] for item in summaries] == ["720p", "audio"]
    assert summaries[0]["estimated_bytes"] == 1000
    assert summaries[0]["dynamic_range"] == "HDR10"
    assert summaries[1]["height"] is None


def test_explicit_webm_container_selects_webm_streams(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    path = load_provider().download(
        request(
            tmp_path,
            output_filename="",
            format_preset="video-1080",
            container_preset="webm",
            subtitle_mode="none",
            subtitle_languages=[],
        )
    )

    assert Path(path).suffix == ".webm"
    assert "ext=webm" in str(captured[0]["format"])
    assert captured[0]["merge_output_format"] == "webm"


def test_optional_metadata_thumbnail_and_chapters_are_explicit(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)

    load_provider().download(
        request(
            tmp_path,
            subtitle_mode="none",
            subtitle_languages=[],
            provider_options={
                "embed_metadata": "true",
                "embed_thumbnail": "true",
                "embed_chapters": "true",
            },
        )
    )

    options = captured[0]
    assert options["writethumbnail"] is True
    assert options["postprocessors"] == [
        {
            "key": "FFmpegMetadata",
            "add_metadata": True,
            "add_chapters": True,
            "add_infojson": False,
        },
        {"key": "EmbedThumbnail", "already_have_thumbnail": False},
    ]


def test_analysis_separates_manual_and_automatic_subtitles(monkeypatch) -> None:
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
            return {
                "id": "example",
                "title": "Example",
                "formats": [],
                "subtitles": {"zh-TW": [{"ext": "vtt"}]},
                "automatic_captions": {
                    "en": [{"ext": "vtt"}],
                    "bad language": [{"ext": "vtt"}],
                },
            }

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)

    result = load_provider().analyze(request(Path("downloads")))

    assert result["manual_subtitle_languages"] == ["zh-TW"]
    assert result["automatic_subtitle_languages"] == ["en"]
    assert result["subtitle_languages"] == ["en", "zh-TW"]


def test_provider_rejects_incompatible_or_audio_container(
    tmp_path: Path, monkeypatch
) -> None:
    captured = []
    fake_ytdlp(monkeypatch, captured)
    provider = load_provider()
    with pytest.raises(ValueError, match="incompatible"):
        provider.download(
            request(
                tmp_path,
                format_preset="video-h264-1080",
                container_preset="webm",
                subtitle_mode="none",
                subtitle_languages=[],
            )
        )
    with pytest.raises(ValueError, match="audio formats"):
        provider.download(
            request(
                tmp_path,
                format_preset="audio-mp3",
                container_preset="mkv",
                subtitle_mode="none",
                subtitle_languages=[],
            )
        )


def test_playlist_keeps_only_official_youtube_thumbnails(monkeypatch) -> None:
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
            return {
                "entries": [
                    {
                        "id": "one",
                        "title": "One",
                        "url": "one",
                        "thumbnail": "https://i.ytimg.com/vi/one/mqdefault.jpg",
                    },
                    {
                        "id": "two",
                        "title": "Two",
                        "url": "two",
                        "thumbnail": "https://example.com/tracker.jpg",
                    },
                ]
            }

    package.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", package)

    entries = load_provider().playlist(
        {"url": "https://music.youtube.com/playlist?list=example"}
    )

    assert entries[0]["thumbnail_url"].startswith("https://i.ytimg.com/")
    assert entries[1]["thumbnail_url"] == ""
