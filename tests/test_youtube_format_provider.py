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
            extension = "mp3" if self.options.get("postprocessors", [{}])[0].get(
                "preferredcodec"
            ) == "mp3" else "mp4"
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
                },
            ]
        }
    )

    assert [item["format_id"] for item in summaries] == ["720p", "audio"]
    assert summaries[0]["estimated_bytes"] == 1000
    assert summaries[1]["height"] is None
