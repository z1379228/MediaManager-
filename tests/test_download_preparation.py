from pathlib import Path

from contracts.media_analysis_v1 import parse_media_formats
from core.downloads.models import DownloadRequest
from core.downloads.preflight import DownloadPreflight
from core.downloads.preparation import (
    available_preset_ids,
    build_batch_preview,
    download_option_lines,
    estimate_preset_bytes,
    format_detail_lines,
    human_bytes,
    suggest_output_filename,
)


def test_media_formats_are_bounded_and_preset_size_is_estimated() -> None:
    raw = [
        {
            "format_id": "720p",
            "extension": "mp4",
            "width": 1280,
            "height": 720,
            "fps": 30,
            "video_codec": "h264",
            "audio_codec": "aac",
            "estimated_bytes": 1000,
        },
        {
            "format_id": "audio",
            "extension": "m4a",
            "width": None,
            "height": None,
            "fps": None,
            "video_codec": "none",
            "audio_codec": "aac",
            "estimated_bytes": 200,
        },
    ]
    formats = parse_media_formats(raw)

    assert estimate_preset_bytes(formats, "video-720") == 1000
    assert estimate_preset_bytes(formats, "audio-m4a") == 200
    assert human_bytes(1024) == "1.0 KiB"
    assert available_preset_ids(formats) == (
        "best",
        "video-720",
        "video-480",
        "audio-m4a",
        "audio-mp3",
    )
    assert "720p" in format_detail_lines(formats)[0]


def test_filename_and_batch_preview_are_safe_and_explicit(tmp_path: Path) -> None:
    filename = suggest_output_filename('A: Track?  ', "abc", "audio-m4a")
    request = DownloadRequest(
        "https://example.test/watch?v=abc",
        tmp_path,
        output_filename=filename,
        format_preset="audio-m4a",
    )
    preflight = DownloadPreflight((tmp_path,), 0, 4096)

    preview = build_batch_preview((request,), preflight, estimated_bytes=1024)

    assert filename == "A_ Track_ [abc].m4a"
    assert preview.item_count == 1
    assert preview.filename == filename
    assert preview.estimated_bytes == 1024


def test_confirmation_options_include_bilibili_segment_and_danmaku() -> None:
    request = DownloadRequest(
        "https://www.bilibili.com/video/BV1example123",
        Path("Downloads"),
        start_time=10,
        end_time=20,
        subtitle_mode="selected",
        subtitle_languages=("zh-TW", "en"),
        timed_comment_mode="ass",
        container_preset="mkv",
    )

    assert download_option_lines(request) == (
        "區段：10 秒 → 20 秒",
        "字幕：指定語言：zh-TW、en",
        "彈幕：保留 XML 並轉為 ASS",
        "封裝：MKV（嵌入 ASS）",
    )
