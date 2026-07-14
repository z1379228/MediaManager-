from __future__ import annotations

import time
import hashlib
import json
from pathlib import Path

import pytest

from core.downloads.archive import DownloadArchive, DuplicateDownloadError
from core.downloads.models import DownloadRequest, DownloadState
from core.downloads.queue import DownloadQueue


class ImmediateBackend:
    def download(self, request, progress, cancel_event):
        progress(
            {
                "downloaded_bytes": 1,
                "total_bytes": 1,
                "info_dict": {"title": "Example"},
            }
        )
        return str(request.output_dir / "result.mp4")


def wait_for(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached")


def test_archive_canonicalizes_youtube_urls_and_keeps_segments_distinct(
    tmp_path: Path,
) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    watch = DownloadRequest(
        "https://www.youtube.com/watch?v=abc12345&utm_source=test",
        tmp_path,
    )
    short = DownloadRequest("https://youtu.be/abc12345?t=5", tmp_path)
    segment = DownloadRequest(
        "https://youtu.be/abc12345",
        tmp_path,
        start_time=5,
        end_time=10,
    )
    assert archive.request_key(watch) == archive.request_key(short)
    legacy_key = hashlib.sha256(
        b"youtube:abc12345|[null,null]"
    ).hexdigest()
    assert archive.request_key(watch) == legacy_key
    assert archive.request_key(watch) != archive.request_key(segment)
    audio = DownloadRequest(
        "https://www.youtube.com/watch?v=abc12345",
        tmp_path,
        audio_only=True,
    )
    assert archive.request_key(watch) != archive.request_key(audio)


def test_batch_duplicate_validation_is_atomic(tmp_path: Path) -> None:
    queue = DownloadQueue(ImmediateBackend(), archive_path=tmp_path / "archive.json")
    requests = [
        DownloadRequest("https://youtu.be/abc12345", tmp_path),
        DownloadRequest("https://www.youtube.com/watch?v=abc12345", tmp_path),
    ]
    with pytest.raises(DuplicateDownloadError):
        queue.add_batch(requests)
    assert queue.snapshots() == ()


def test_successful_download_remains_archived_after_history_clear_and_restart(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "archive.json"
    request = DownloadRequest("https://youtu.be/abc12345", tmp_path)
    queue = DownloadQueue(
        ImmediateBackend(),
        workers=1,
        state_path=tmp_path / "queue.json",
        archive_path=archive_path,
    )
    queue.add(request)
    queue.start()
    wait_for(lambda: queue.snapshots()[0].state is DownloadState.COMPLETED)
    assert queue.clear_finished() == 1
    with pytest.raises(DuplicateDownloadError):
        queue.add(request)
    queue.shutdown()

    restored = DownloadQueue(
        ImmediateBackend(),
        state_path=tmp_path / "queue-2.json",
        archive_path=archive_path,
    )
    with pytest.raises(DuplicateDownloadError):
        restored.add(request)


def test_different_segments_of_same_video_can_be_queued(tmp_path: Path) -> None:
    queue = DownloadQueue(ImmediateBackend(), archive_path=tmp_path / "archive.json")
    ids = queue.add_batch(
        [
            DownloadRequest(
                "https://youtu.be/abc12345",
                tmp_path,
                start_time=0,
                end_time=10,
            ),
            DownloadRequest(
                "https://youtu.be/abc12345",
                tmp_path,
                start_time=10,
                end_time=20,
            ),
        ]
    )
    assert len(ids) == 2


def test_archive_export_preview_and_atomic_merge(tmp_path: Path) -> None:
    source = DownloadArchive(tmp_path / "source.json")
    first = DownloadRequest("https://youtu.be/abc12345", tmp_path)
    second = DownloadRequest("https://youtu.be/def67890", tmp_path)
    assert source.record(first)
    assert source.record(second)

    portable = tmp_path / "portable.json"
    assert source.export_file(portable) == 2
    raw = json.loads(portable.read_text(encoding="utf-8"))
    assert raw["kind"] == "mediamanager-download-archive"

    destination = DownloadArchive(tmp_path / "destination.json")
    assert destination.record(first)
    preview = destination.preview_import(portable)
    assert preview.incoming_count == 2
    assert preview.new_count == 1
    assert preview.duplicate_count == 1
    assert destination.apply_import(preview) == 1
    assert destination.count == 2
    assert destination.apply_import(preview) == 0


def test_archive_import_rejects_duplicate_or_unbounded_keys(tmp_path: Path) -> None:
    key = "a" * 64
    source = tmp_path / "invalid.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "mediamanager-download-archive",
                "keys": [key, key],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="keys"):
        DownloadArchive(tmp_path / "archive.json").preview_import(source)
