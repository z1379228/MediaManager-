from __future__ import annotations

from pathlib import Path

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.recovery_v1 import RecoveryCandidateV1
from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.downloads.queue import DownloadQueue
from trusted_ui.download_panel import discovery_item_for_task
from trusted_ui.recovery_dialog import build_replacement_request


class UnusedBackend:
    pass


def source_request(tmp_path: Path) -> DownloadRequest:
    return DownloadRequest(
        "https://www.youtube.com/watch?v=old12345",
        tmp_path,
        priority=5,
        start_time=10,
        end_time=30,
        source_video_id="old12345",
        source_title="原始歌曲",
        source_artist="原始歌手",
        source_language="zh-TW",
        source_category="music",
        output_filename="old-track.m4a",
        audio_only=True,
        format_preset="audio-mp3",
        subtitle_mode="selected",
        subtitle_languages=("zh-TW",),
    )


def replacement() -> RecoveryCandidateV1:
    item = DiscoveryItemV1.from_dict(
        {
            "video_id": "new12345",
            "url": "https://www.youtube.com/watch?v=new12345",
            "title": "替代歌曲",
            "artist": "替代歌手",
            "duration": 180,
            "language": "zh-TW",
            "category": "music",
            "thumbnail_url": "",
        }
    )
    return RecoveryCandidateV1(item, 80, ("title", "artist"))


def test_download_request_rejects_oversized_source_metadata(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="source_title"):
        DownloadRequest(
            "https://youtu.be/old12345",
            tmp_path,
            source_title="x" * 301,
        )


def test_queue_persists_source_metadata_for_recovery(tmp_path: Path) -> None:
    state = tmp_path / "queue.json"
    original = source_request(tmp_path)
    queue = DownloadQueue(UnusedBackend(), state_path=state)
    queue.add(original)
    restored = DownloadQueue(UnusedBackend(), state_path=state)
    request = restored.snapshots()[0].request
    assert request.source_video_id == "old12345"
    assert request.source_title == "原始歌曲"
    assert request.source_artist == "原始歌手"
    assert request.source_language == "zh-TW"
    assert request.source_category == "music"
    assert request.output_filename == "old-track.m4a"
    assert request.audio_only
    assert request.format_preset == "audio-mp3"
    assert request.subtitle_mode == "selected"
    assert request.subtitle_languages == ("zh-TW",)


def test_failed_task_converts_to_recovery_item(tmp_path: Path) -> None:
    task = DownloadTask(
        "task",
        source_request(tmp_path),
        state=DownloadState.FAILED,
        error="unavailable",
    )
    item = discovery_item_for_task(task)
    assert item is not None
    assert item.video_id == "old12345"
    assert item.title == "原始歌曲"
    assert item.artist == "原始歌手"


def test_manual_failed_task_without_title_cannot_guess_recovery(
    tmp_path: Path,
) -> None:
    task = DownloadTask(
        "task",
        DownloadRequest("https://youtu.be/old12345", tmp_path),
        state=DownloadState.FAILED,
    )
    assert discovery_item_for_task(task) is None


def test_replacement_request_preserves_queue_options_and_uses_new_metadata(
    tmp_path: Path,
) -> None:
    request = build_replacement_request(source_request(tmp_path), replacement())
    assert request.url.endswith("new12345")
    assert request.priority == 5
    assert request.start_time == 10
    assert request.end_time == 30
    assert request.source_video_id == "new12345"
    assert request.source_title == "替代歌曲"
    assert request.source_artist == "替代歌手"
    assert request.output_filename == "old-track.m4a"
    assert request.audio_only
    assert request.format_preset == "audio-mp3"
    assert request.subtitle_mode == "selected"
    assert request.subtitle_languages == ("zh-TW",)
