from __future__ import annotations

import json
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest

from core.downloads.subprocess_provider import SubprocessDownloadProvider


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = ROOT / "mod" / "builtin" / "bilibili"


@pytest.mark.parametrize(
    "url",
    (
        "https://www.bilibili.com/video/BVexample",
        "https://m.bilibili.com/video/BVexample",
        "https://space.bilibili.com/123/video",
        "https://player.bilibili.com/player.html?aid=170001",
        "https://b23.tv/example",
        "https://bilibili.com/video/BVexample",
        "https://www.bilibili.tv/en/video/2041863208",
        "https://bilibili.tv/en/play/1018660/11515462",
    ),
)
def test_bilibili_provider_accepts_only_explicit_hosts(url: str) -> None:
    provider = SubprocessDownloadProvider(
        PROVIDER_ROOT,
        application_root=ROOT,
    )

    assert provider.provider_id == "bilibili"
    assert provider.supports(url)


@pytest.mark.parametrize(
    "url",
    (
        "https://live.bilibili.com/123",
        "https://www.youtube.com/watch?v=example",
        "https://user:secret@www.bilibili.com/video/BVexample",
        "https://www.bilibili.com:99999/video/BVexample",
        "https://www.biliintl.com/en/video/2041863208",
        "https://player.bilibili.com/player.html?AID=170001",
        "https://player.bilibili.com/player.html?%61id=170001",
        "https://player.bilibili.com/player.html?aid=%31",
        "https://player.bilibili.com/player.html?aid=1%32",
        "https://player.bilibili.com/player.html?bvid=BV1B7411m7LV",
        "https://player.bilibili.com/player.html?aid=one",
        "https://player.bilibili.com/player.html?aid=1&unknown=1",
    ),
)
def test_bilibili_provider_rejects_unlisted_or_credential_urls(url: str) -> None:
    provider = SubprocessDownloadProvider(
        PROVIDER_ROOT,
        application_root=ROOT,
    )

    assert not provider.supports(url)


def test_bilibili_manifest_uses_separate_permission_and_installed_extractor() -> None:
    from yt_dlp.extractor import gen_extractor_classes

    manifest = json.loads(
        (PROVIDER_ROOT / "provider.json").read_text(encoding="utf-8")
    )
    extractor_names = {
        str(getattr(extractor, "IE_NAME", "")).casefold()
        for extractor in gen_extractor_classes()
    }

    assert manifest["permissions"][0] == "network.bilibili"
    assert "network.generic" not in manifest["permissions"]
    assert any(name.startswith("bilibili") for name in extractor_names)


def test_bilibili_player_allowlist_matches_installed_extractor() -> None:
    from yt_dlp.extractor import gen_extractor_classes

    extractor = next(
        item
        for item in gen_extractor_classes()
        if str(getattr(item, "IE_NAME", "")).casefold() == "bilibiliplayer"
    )

    assert extractor.suitable(
        "https://player.bilibili.com/player.html?aid=170001"
    )
    assert not extractor.suitable(
        "https://player.bilibili.com/player.html?AID=170001"
    )


def test_bilibili_analyze_bounds_metadata_and_reports_parts(monkeypatch) -> None:
    import yt_dlp

    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, url, *, download):
            assert url == "https://www.bilibili.com/video/BVexample"
            assert not download
            return {
                "id": "x" * 120,
                "title": "Example",
                "duration": 90,
                "uploader": "Artist",
                "webpage_url": url,
                "thumbnail": "https://image.example/cover.jpg",
                "description": "d" * 30_000,
                "extractor_key": "BiliBiliBangumi",
                "subtitles": {"zh-Hant": [{"url": "https://sub.example"}]},
                "entries": [{"id": "p1"}, {"id": "p2"}],
                "chapters": [
                    {"start_time": 0, "end_time": 2, "title": "Part"}
                ],
                "formats": [
                    {
                        "format_id": "1080p",
                        "ext": "mp4",
                        "width": 1920,
                        "height": 1080,
                        "fps": 60,
                        "vcodec": "avc1.640028",
                        "acodec": "none",
                        "dynamic_range": "HDR10",
                        "filesize": 1000,
                    }
                ],
            }

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["analyze"](
        {"url": "https://www.bilibili.com/video/BVexample"}
    )

    assert len(result["id"]) == 100
    assert len(result["description"]) == 20_000
    assert result["thumbnail"] == "https://image.example/cover.jpg"
    assert result["part_count"] == 2
    assert result["content_kind"] == "bangumi"
    assert result["subtitle_languages"] == ["zh-Hant"]
    assert result["manual_subtitle_languages"] == ["zh-Hant"]
    assert result["automatic_subtitle_languages"] == []
    assert result["danmaku_available"] is False
    assert result["chapters"][0]["start_time"] == 0
    assert result["formats"][0]["dynamic_range"] == "HDR10"
    assert captured[0]["noplaylist"] is True


def test_bilibili_playlist_normalizes_multipart_and_bangumi_urls(
    monkeypatch,
) -> None:
    import yt_dlp

    class FakeYoutubeDL:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, *, download):
            assert not download
            return {
                "title": "Parent title",
                "uploader": "Parent uploader",
                "thumbnail": "https://i0.hdslb.com/bfs/archive/parent.jpg",
                "entries": [
                    {"id": "BVpart", "url": "BVpart", "part": "Opening"},
                    {"id": "BVpart", "url": "BVpart"},
                    {
                        "id": "ep123",
                        "url": "https://www.bilibili.com/bangumi/play/ep123",
                        "title": "EP",
                    },
                ]
            }

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    namespace["playlist"].__globals__["_official_video_pages"] = lambda *_: {
        1: ("官方 Opening", 31.0, "https://i0.hdslb.com/bfs/storyff/one.jpg"),
        2: ("官方 Lesson", 62.0, ""),
    }
    entries = namespace["playlist"](
        {"url": "https://www.bilibili.com/video/BVpart", "limit": 10}
    )

    assert [entry["entry_id"] for entry in entries] == [
        "BVpart",
        "BVpart-p2",
        "ep123",
    ]
    assert entries[0]["url"].endswith("/video/BVpart")
    assert entries[1]["url"].endswith("/video/BVpart?p=2")
    assert "/bangumi/play/ep123" in entries[2]["url"]
    assert all(entry["available"] for entry in entries)
    assert entries[0]["title"] == "官方 Opening"
    assert entries[1]["title"] == "官方 Lesson"
    assert entries[0]["duration"] == 31.0
    assert entries[1]["artist"] == "Parent uploader"
    assert entries[0]["thumbnail_url"].endswith("/one.jpg")
    assert entries[1]["thumbnail_url"].endswith("/parent.jpg")


def test_bilibili_creator_playlist_resolves_titles_with_bounded_limit(
    monkeypatch,
) -> None:
    import yt_dlp

    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, url, *, download):
            assert url == "https://space.bilibili.com/123/video"
            assert not download
            return {
                "entries": [
                    {
                        "id": "BV1zW411u7T6",
                        "webpage_url": "https://www.bilibili.com/video/BV1zW411u7T6",
                        "title": "UP 主影片標題",
                        "uploader": "UP 主",
                        "duration": 80,
                        "thumbnail": "http://i0.hdslb.com/bfs/archive/creator.jpg",
                    }
                ]
            }

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    namespace["playlist"].__globals__["_official_video_pages"] = lambda *_: {}
    entries = namespace["playlist"](
        {"url": "https://space.bilibili.com/123/video", "limit": 500}
    )

    assert captured[0]["extract_flat"] is False
    assert captured[0]["playlistend"] == 50
    assert entries[0]["title"] == "UP 主影片標題"
    assert entries[0]["thumbnail_url"] == (
        "https://i0.hdslb.com/bfs/archive/creator.jpg"
    )


def test_bilibili_official_pages_are_bounded_and_exact(monkeypatch) -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    request_module = namespace["url_request"]
    payload = json.dumps(
        {
            "code": 0,
            "data": {
                "bvid": "BV1zW411u7T6",
                "pages": [
                    {
                        "page": 1,
                        "part": " 第一段 ",
                        "duration": 45,
                        "first_frame": "http://i0.hdslb.com/bfs/storyff/one.jpg",
                    }
                ],
            },
        }
    ).encode()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self):
            return "https://api.bilibili.com/x/web-interface/view?bvid=BV1zW411u7T6"

        def read(self, _limit):
            return payload

    class Opener:
        def open(self, outgoing, *, timeout):
            assert timeout == 20
            assert "bvid=BV1zW411u7T6" in outgoing.full_url
            return Response()

    monkeypatch.setattr(request_module, "build_opener", lambda _handler: Opener())
    pages = namespace["_official_video_pages"](
        "https://www.bilibili.com/video/BV1zW411u7T6",
        20,
    )

    assert pages == {
        1: (
            "第一段",
            45.0,
            "https://i0.hdslb.com/bfs/storyff/one.jpg",
        )
    }
    assert namespace["_official_video_pages"](
        "https://www.youtube.com/watch?v=wrong",
        20,
    ) == {}


def test_bilibili_support_matrix_is_explicit() -> None:
    matrix = json.loads(
        (PROVIDER_ROOT / "site-matrix.json").read_text(encoding="utf-8")
    )
    feature_ids = {feature["feature_id"] for feature in matrix["features"]}
    assert matrix["provider_id"] == "bilibili"
    assert {
        "multipart-playlist",
        "bangumi-public-episode",
        "subtitles",
        "segment-download",
    }.issubset(feature_ids)


def test_bilibili_download_keeps_danmaku_as_xml_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import yt_dlp

    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, url, *, download):
            assert url == "https://www.bilibili.com/video/BVexample"
            assert download
            (tmp_path / "clip.mp4").write_bytes(b"video")
            (tmp_path / "clip.danmaku.xml").write_text(
                "<i></i>", encoding="utf-8"
            )
            return {"id": "BVexample", "title": "Example"}

        def prepare_filename(self, _info):
            return str(tmp_path / "clip.webm")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["download"](
        {
            "url": "https://www.bilibili.com/video/BVexample",
            "output_dir": str(tmp_path),
            "output_filename": "clip.mp4",
            "format_preset": "best",
            "subtitle_mode": "none",
            "subtitle_languages": [],
            "timed_comment_mode": "source",
            "container_preset": "auto",
        }
    )

    assert Path(result) == tmp_path / "clip.mp4"
    assert (tmp_path / "clip.danmaku.xml").is_file()
    assert captured[0]["writesubtitles"] is True
    assert captured[0]["subtitleslangs"] == ["danmaku"]
    assert captured[0]["subtitlesformat"] == "best"
    assert "embedsubtitles" not in captured[0]
    assert captured[0]["continuedl"] is True
    assert captured[0]["nopart"] is False
    assert captured[0]["overwrites"] is False


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
def test_bilibili_audio_encoding_presets_use_bounded_ffmpeg_outputs(
    tmp_path: Path,
    monkeypatch,
    preset: str,
    codec: str,
    quality: str | None,
) -> None:
    import yt_dlp

    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, *, download):
            assert download
            (tmp_path / f"clip.{codec}").write_bytes(b"audio")
            return {"id": "BVexample", "title": "Example"}

        def prepare_filename(self, _info):
            return str(tmp_path / "clip.webm")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["download"](
        {
            "url": "https://www.bilibili.com/video/BVexample",
            "output_dir": str(tmp_path),
            "output_filename": "",
            "format_preset": preset,
            "subtitle_mode": "none",
            "subtitle_languages": [],
            "timed_comment_mode": "none",
            "container_preset": "auto",
        }
    )

    postprocessor = captured[0]["postprocessors"][0]
    assert Path(result).suffix == f".{codec}"
    assert postprocessor["preferredcodec"] == codec
    if quality is None:
        assert "preferredquality" not in postprocessor
    else:
        assert postprocessor["preferredquality"] == quality


def test_bilibili_h264_preset_selects_avc1_and_aac_without_transcoding() -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    selector = namespace["_FORMAT_SELECTORS"]["video-h264-1080"]

    assert "vcodec^=avc1" in selector
    assert "acodec^=mp4a" in selector
    assert "video-h264-1080" not in namespace["_AUDIO_OUTPUTS"]


@pytest.mark.parametrize(
    ("preset", "height"),
    (("video-1440", 1440), ("video-2160", 2160)),
)
def test_bilibili_high_resolution_presets_are_height_bounded(
    preset: str, height: int
) -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    selector = namespace["_FORMAT_SELECTORS"][preset]
    assert f"height<={height}" in selector
    assert not selector.endswith("/b")


def test_bilibili_container_selectors_are_explicit_and_bounded() -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    mp4 = namespace["_container_format_selector"]("video-1080", "mp4")
    webm = namespace["_container_format_selector"]("video-1080", "webm")
    assert "height<=1080" in mp4 and "ext=mp4" in mp4
    assert "height<=1080" in webm and "ext=webm" in webm
    with pytest.raises(ValueError, match="incompatible"):
        namespace["_container_format_selector"]("video-h264-1080", "webm")


def test_bilibili_media_options_allow_video_container_without_danmaku() -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    request = {
        "format_preset": "video-1080",
        "subtitle_mode": "none",
        "subtitle_languages": [],
        "timed_comment_mode": "none",
        "container_preset": "mkv",
    }

    assert namespace["_media_options"](request)[-2] == "mkv"
    request.update(format_preset="audio-mp3")
    with pytest.raises(ValueError, match="container options"):
        namespace["_media_options"](request)


def test_bilibili_media_options_bound_network_retry_profile() -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    request = {
        "format_preset": "video-1080",
        "subtitle_mode": "none",
        "subtitle_languages": [],
        "timed_comment_mode": "none",
        "container_preset": "auto",
        "provider_options": {"network_retry": "resilient"},
    }

    assert namespace["_media_options"](request)[-1] == "resilient"
    request["provider_options"] = {"network_retry": "unbounded"}
    with pytest.raises(ValueError, match="retry mode"):
        namespace["_media_options"](request)


def test_bilibili_finds_danmaku_for_literal_bracketed_media_name(
    tmp_path: Path,
) -> None:
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    media = tmp_path / "Video [BVexample].mkv"
    media.write_bytes(b"media")
    xml = tmp_path / "Video [BVexample].danmaku.xml"
    xml.write_text("<i></i>", encoding="utf-8")
    (tmp_path / "unrelated.danmaku.xml").write_text("<i></i>", encoding="utf-8")

    assert namespace["_find_danmaku_xml"](tmp_path, media) == xml


def test_bilibili_download_converts_danmaku_to_ass_and_retains_xml(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import yt_dlp

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, *, download):
            assert download
            (tmp_path / "clip.mp4").write_bytes(b"video")
            (tmp_path / "clip.danmaku.xml").write_text(
                '<i><d p="0,1,25,16777215,0,0,user,id">測試彈幕</d></i>',
                encoding="utf-8",
            )
            return {"id": "BVexample", "title": "Example"}

        def prepare_filename(self, _info):
            return str(tmp_path / "clip.webm")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["download"](
        {
            "url": "https://www.bilibili.com/video/BVexample",
            "output_dir": str(tmp_path),
            "output_filename": "clip.mp4",
            "format_preset": "best",
            "subtitle_mode": "none",
            "subtitle_languages": [],
            "timed_comment_mode": "ass",
            "container_preset": "auto",
        }
    )

    assert Path(result) == tmp_path / "clip.mp4"
    assert (tmp_path / "clip.danmaku.xml").is_file()
    ass = tmp_path / "clip.danmaku.ass"
    assert ass.is_file()
    assert "測試彈幕" in ass.read_text(encoding="utf-8-sig")


def test_bilibili_segmented_ass_is_retimed_before_mkv_mux(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import yt_dlp

    captured: list[dict[str, object]] = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options
            captured.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, *, download):
            assert download
            (tmp_path / "clip.mp4").write_bytes(b"video")
            (tmp_path / "clip.danmaku.xml").write_text(
                "<i>"
                '<d p="9,1,25,16777215,0,0,user,1">before</d>'
                '<d p="12,1,25,16777215,0,0,user,2">inside</d>'
                '<d p="20,1,25,16777215,0,0,user,3">at-end</d>'
                "</i>",
                encoding="utf-8",
            )
            return {"id": "BVexample", "title": "Example"}

        def prepare_filename(self, _info):
            return str(tmp_path / "clip.webm")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    muxed_ass: list[str] = []

    def fake_mux(media: Path, ass_path: Path, _ffmpeg: object) -> Path:
        muxed_ass.append(ass_path.read_text(encoding="utf-8-sig"))
        return media

    namespace["download"].__globals__["_mux_ass_into_mkv"] = fake_mux

    result = namespace["download"](
        {
            "url": "https://www.bilibili.com/video/BVexample",
            "output_dir": str(tmp_path),
            "output_filename": "clip.mp4",
            "format_preset": "best",
            "subtitle_mode": "none",
            "subtitle_languages": [],
            "timed_comment_mode": "ass",
            "container_preset": "mkv",
            "start_time": 10.0,
            "end_time": 20.0,
        }
    )

    assert Path(result) == tmp_path / "clip.mp4"
    assert "download_ranges" in captured[0]
    assert captured[0]["force_keyframes_at_cuts"] is True
    assert "+ba" in captured[0]["format"]
    ass = (tmp_path / "clip.danmaku.ass").read_text(encoding="utf-8-sig")
    assert "before" not in ass
    assert "at-end" not in ass
    assert "0:00:02.00" in ass
    assert "inside" in ass
    assert muxed_ass == [ass]
    assert (tmp_path / "clip.danmaku.xml").is_file()


def test_mkv_mux_is_atomic_and_removes_intermediate_media(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    ass = tmp_path / "clip.danmaku.ass"
    ass.write_text("[Script Info]\n", encoding="utf-8")
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"executable")
    captured: list[list[str]] = []

    def fake_run(command, **_kwargs):
        captured.append(command)
        Path(command[-1]).write_bytes(b"mkv")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(namespace["subprocess"], "run", fake_run)

    result = namespace["_mux_ass_into_mkv"](media, ass, ffmpeg)

    assert result == tmp_path / "clip.mkv"
    assert result.read_bytes() == b"mkv"
    assert not media.exists()
    assert ass.exists()
    assert "-c" in captured[0]
    assert "copy" in captured[0]


def test_mkv_mux_with_bundled_ffmpeg_contains_ass_stream(tmp_path: Path) -> None:
    ffmpeg = Path(
        shutil.which("ffmpeg")
        or ROOT / "Version" / "1.6" / "tools" / "ffmpeg.exe"
    )
    ffprobe = Path(
        shutil.which("ffprobe")
        or ROOT / "Version" / "1.6" / "tools" / "ffprobe.exe"
    )
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("portable FFmpeg tools are unavailable")
    media = tmp_path / "clip.mp4"
    created = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=640x360:r=1:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(media),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert created.returncode == 0
    ass = tmp_path / "clip.danmaku.ass"
    ass.write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 640\nPlayResY: 360\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,24,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:00.80,Default,,0,0,0,,test\n",
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(PROVIDER_ROOT / "provider.py"))

    result = namespace["_mux_ass_into_mkv"](media, ass, ffmpeg)
    probed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nw=1:nk=1",
            str(result),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert probed.returncode == 0
    assert probed.stdout.strip() == "ass"
    assert result.suffix == ".mkv"
    assert ass.is_file()
