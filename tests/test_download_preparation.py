from pathlib import Path

from contracts.media_analysis_v1 import parse_media_formats
from core.downloads.models import DownloadRequest
from core.downloads.preflight import DownloadPreflight
from core.downloads.preparation import (
    advanced_format_summary,
    available_preset_ids,
    build_batch_preview,
    container_compatibility,
    download_option_lines,
    estimate_preset_bytes,
    format_preset_encoding_note,
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
        "audio-m4a-256",
        "audio-mp3",
        "audio-mp3-320",
        "audio-opus",
        "audio-flac",
        "audio-wav",
    )
    assert "720p" in format_detail_lines(formats)[0]


def test_h264_preset_requires_compatible_video_and_audio_streams() -> None:
    compatible = parse_media_formats(
        [
            {
                "format_id": "video",
                "extension": "mp4",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "video_codec": "avc1.640028",
                "audio_codec": "none",
                "estimated_bytes": 1000,
            },
            {
                "format_id": "audio",
                "extension": "m4a",
                "width": None,
                "height": None,
                "fps": None,
                "video_codec": "none",
                "audio_codec": "mp4a.40.2",
                "estimated_bytes": 200,
            },
        ]
    )
    incompatible = parse_media_formats(
        [
            {
                "format_id": "video",
                "extension": "webm",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "video_codec": "vp9",
                "audio_codec": "none",
                "estimated_bytes": 1000,
            },
            {
                "format_id": "audio",
                "extension": "webm",
                "width": None,
                "height": None,
                "fps": None,
                "video_codec": "none",
                "audio_codec": "opus",
                "estimated_bytes": 200,
            },
        ]
    )

    assert "video-h264-1080" in available_preset_ids(compatible)
    assert "video-h264-1080" not in available_preset_ids(incompatible)


def test_encoding_notes_disclose_compatibility_and_transcoding_limits() -> None:
    assert "2160p" in format_preset_encoding_note("video-2160")
    assert "1440p" in format_preset_encoding_note("video-1440")
    assert "H.264" in format_preset_encoding_note("video-h264-1080")
    assert "256 kbps" in format_preset_encoding_note("audio-m4a-256")
    assert "320 kbps" in format_preset_encoding_note("audio-mp3-320")
    assert "160 kbps" in format_preset_encoding_note("audio-opus")
    flac_note = format_preset_encoding_note("audio-flac")
    assert "FLAC" in flac_note
    assert "不會提升" in flac_note
    wav_note = format_preset_encoding_note("audio-wav")
    assert "WAV PCM" in wav_note
    assert "容量很大" in wav_note


def test_high_resolution_presets_follow_analyzed_source_height() -> None:
    formats = parse_media_formats(
        [
            {
                "format_id": "4k",
                "extension": "webm",
                "width": 3840,
                "height": 2160,
                "fps": 60,
                "video_codec": "av1",
                "audio_codec": "none",
                "estimated_bytes": 4000,
                "dynamic_range": "HDR10",
            },
            {
                "format_id": "audio",
                "extension": "webm",
                "width": None,
                "height": None,
                "fps": None,
                "video_codec": "none",
                "audio_codec": "opus",
                "estimated_bytes": 200,
            },
        ]
    )

    available = available_preset_ids(formats)
    assert "video-2160" in available
    assert "video-1440" in available
    assert estimate_preset_bytes(formats, "video-2160") == 4000
    summary = advanced_format_summary(formats, "video-2160")
    assert "3840×2160" in summary
    assert "60 FPS" in summary
    assert "HDR10" in summary


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


def test_high_quality_audio_presets_use_expected_extensions() -> None:
    assert suggest_output_filename("Track", "one", "audio-m4a-256").endswith(
        ".m4a"
    )
    assert suggest_output_filename("Track", "two", "audio-mp3-320").endswith(
        ".mp3"
    )
    assert suggest_output_filename("Track", "three", "audio-wav").endswith(
        ".wav"
    )
    assert suggest_output_filename(
        "Video", "four", "video-2160", "mkv"
    ).endswith(".mkv")
    assert suggest_output_filename(
        "Video", "five", "video-1440", "webm"
    ).endswith(".webm")


def test_container_compatibility_uses_reported_codecs_and_extensions() -> None:
    formats = parse_media_formats(
        [
            {
                "format_id": "mp4-video",
                "extension": "mp4",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "video_codec": "avc1.640028",
                "audio_codec": "none",
                "estimated_bytes": 1000,
                "dynamic_range": "SDR",
            },
            {
                "format_id": "m4a-audio",
                "extension": "m4a",
                "width": None,
                "height": None,
                "fps": None,
                "video_codec": "none",
                "audio_codec": "mp4a.40.2",
                "estimated_bytes": 200,
            },
            {
                "format_id": "webm-video",
                "extension": "webm",
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "video_codec": "vp9",
                "audio_codec": "none",
                "estimated_bytes": 1200,
                "dynamic_range": "HDR10",
            },
            {
                "format_id": "webm-audio",
                "extension": "webm",
                "width": None,
                "height": None,
                "fps": None,
                "video_codec": "none",
                "audio_codec": "opus",
                "estimated_bytes": 180,
            },
        ]
    )

    assert container_compatibility(formats, "video-1080", "mp4").compatible
    assert container_compatibility(formats, "video-1080", "webm").compatible
    assert container_compatibility(formats, "video-1080", "mkv").compatible
    h264_webm = container_compatibility(
        formats, "video-h264-1080", "webm"
    )
    assert not h264_webm.compatible
    assert h264_webm.recommended_container == "mp4"


def test_explicit_container_requires_analysis_but_mkv_is_safe_fallback() -> None:
    assert container_compatibility((), "video-720", "auto").compatible
    assert container_compatibility((), "video-720", "mkv").compatible
    assert not container_compatibility((), "video-720", "mp4").compatible
    assert not container_compatibility((), "video-720", "webm").compatible
    assert not container_compatibility((), "audio-mp3", "mkv").compatible


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
