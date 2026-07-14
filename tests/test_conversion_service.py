from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from threading import Event
import time

import pytest

from core.conversion import ConversionRequest, ConversionService, ConversionTask


@pytest.fixture
def service(tmp_path: Path) -> ConversionService:
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"test")
    presets = Path(__file__).parents[1] / "mod" / "builtin" / "media-convert" / "presets.json"
    instance = ConversionService(ffmpeg, presets, tmp_path / "temp")
    yield instance
    instance.close()


def test_preview_prefers_stream_copy_and_refuses_overwrite(
    service: ConversionService, tmp_path: Path
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mkv"
    plan = service.preview(ConversionRequest((source,), output, "remux-copy"))
    assert plan.strategy.startswith("串流複製")
    assert "copy" in plan.command
    assert plan.estimated_bytes >= source.stat().st_size
    output.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        service.preview(ConversionRequest((source,), output, "remux-copy"))


def test_join_requires_same_type_and_preserves_output_extension(
    service: ConversionService, tmp_path: Path
) -> None:
    first = tmp_path / "one.mp4"
    second = tmp_path / "two.mkv"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    with pytest.raises(ValueError, match="same type"):
        service.preview(
            ConversionRequest((first, second), tmp_path / "joined.mp4", "join-copy")
        )


def test_gpu_failure_falls_back_to_cpu_and_commits_without_overwrite(
    service: ConversionService, tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mp4"
    request = ConversionRequest(
        (source,), output, "video-h264", hardware_acceleration=True
    )
    plan = service.preview(request)
    task = ConversionTask("task", plan.request)
    calls = []

    def fake_run(command, _cancel_event):
        calls.append(command)
        if len(calls) == 2:
            Path(command[-1]).write_bytes(b"converted")
            return 0
        return 1

    monkeypatch.setattr(service, "_run", fake_run)
    assert service._execute(task, plan) == output
    assert output.read_bytes() == b"converted"
    assert len(calls) == 2
    assert not list(tmp_path.glob("*.part.mp4"))


def test_cancelled_conversion_removes_partial_output(
    service: ConversionService, tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mkv"
    plan = service.preview(ConversionRequest((source,), output, "remux-copy"))
    task = ConversionTask("cancel", plan.request)

    def fake_run(command, cancel_event: Event):
        Path(command[-1]).write_bytes(b"partial")
        cancel_event.set()
        return 1

    monkeypatch.setattr(service, "_run", fake_run)
    with pytest.raises(RuntimeError, match="cancelled"):
        service._execute(task, plan)
    assert not output.exists()
    assert not list(tmp_path.glob("*.part.mkv"))


def test_service_is_disabled_by_default(service: ConversionService, tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    with pytest.raises(RuntimeError, match="disabled"):
        service.submit(ConversionRequest((source,), tmp_path / "output.mkv", "remux-copy"))


def test_local_ffmpeg_conversion_smoke(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("local FFmpeg is not installed")
    source = tmp_path / "tone.wav"
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=0.1",
            str(source),
        ],
        check=True,
        timeout=10,
    )
    presets = Path(__file__).parents[1] / "mod" / "builtin" / "media-convert" / "presets.json"
    service = ConversionService(Path(ffmpeg), presets, tmp_path / "temp")
    try:
        service.set_enabled(True)
        output = tmp_path / "tone.mp3"
        task_id = service.submit(
            ConversionRequest((source,), output, "audio-mp3")
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            task = next(task for task in service.snapshots() if task.task_id == task_id)
            if task.state.name in {"COMPLETED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.05)
        assert task.state.name == "COMPLETED", task.error
        assert output.is_file() and output.stat().st_size > 0
    finally:
        service.close()
