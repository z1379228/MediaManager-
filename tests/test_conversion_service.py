from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from threading import Event
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.conversion import (
    ConversionRequest,
    ConversionService,
    ConversionTask,
    MediaAdTrimFeature,
)
from core.events.event_bus import EventBus
from core.features import FeatureModRegistry
from trusted_ui.conversion_panel import parse_removal_ranges


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


def test_ad_trim_builds_bounded_filters_and_never_replaces_source(
    service: ConversionService, tmp_path: Path
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "trimmed.mp4"

    plan = service.preview(
        ConversionRequest(
            (source,),
            output,
            "ad-trim-h264",
            remove_ranges=((30, 45), (90.5, 105)),
        )
    )

    assert plan.request.remove_ranges == ((30.0, 45.0), (90.5, 105.0))
    assert any(value.startswith("select=not(") for value in plan.command)
    assert any(value.startswith("aselect=not(") for value in plan.command)
    assert str(source.resolve()) in plan.command
    assert str(output.resolve()) not in plan.command
    assert "@OUTPUT@" in plan.command


@pytest.mark.parametrize(
    ("ranges", "start_time"),
    [
        ((), None),
        (((10.0, 20.0), (19.0, 30.0)), None),
        (((-1.0, 2.0),), None),
        (((1.0, 2.0),), 1.0),
    ],
)
def test_ad_trim_rejects_empty_overlapping_or_clipped_requests(
    service: ConversionService,
    tmp_path: Path,
    ranges: tuple[tuple[float, float], ...],
    start_time: float | None,
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    with pytest.raises(ValueError, match="ad trim|removal ranges|ordered"):
        service.preview(
            ConversionRequest(
                (source,),
                tmp_path / "trimmed.mp4",
                "ad-trim-h264",
                start_time=start_time,
                remove_ranges=ranges,
            )
        )


def test_ad_trim_parser_and_child_feature_are_independently_disabled(
    service: ConversionService,
) -> None:
    assert parse_removal_ranges("30-45; 01:30-01:45") == (
        (30.0, 45.0),
        (90.0, 105.0),
    )
    with pytest.raises(ValueError, match="分與秒"):
        parse_removal_ranges("00:70-80")

    feature = MediaAdTrimFeature(service)
    service.cancel_preset = Mock(return_value=2)
    feature._enabled = True
    assert feature.set_enabled(False) == 2
    service.cancel_preset.assert_called_once_with("ad-trim-h264")


def test_conversion_panel_exposes_ad_trim_only_when_child_is_enabled(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    features = FeatureModRegistry(tmp_path / "features.json")
    features.register(service, enabled=True)
    features.register(MediaAdTrimFeature(service), enabled=False)
    context = SimpleNamespace(
        conversion=service,
        features=features,
        download_providers=Mock(),
        discovery=Mock(),
        audit=Mock(),
        events=EventBus(),
    )
    from trusted_ui.conversion_panel import create_conversion_panel

    panel = create_conversion_panel(context)
    try:
        index = panel.preset.findData("ad-trim-h264")
        panel.preset.setCurrentIndex(index)
        app.processEvents()
        assert panel.trim_card.isVisibleTo(panel)
        assert not panel.submit.isEnabled()

        panel.ad_trim_enabled.click()
        app.processEvents()
        assert features.is_enabled("media-ad-trim")
        assert panel.ad_ranges.isEnabled()
        assert panel.submit.isEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()


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
