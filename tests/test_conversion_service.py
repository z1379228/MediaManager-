from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from threading import Event, Thread
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.conversion import (
    ConversionCapabilities,
    ConversionRequest,
    ConversionService,
    ConversionTask,
    MediaAdTrimFeature,
)
from core.conversion.service import (
    DEFAULT_CONVERSION_FREE_SPACE_RESERVE,
    LOCAL_PROTOCOL_WHITELIST,
    MAX_CAPABILITY_OUTPUT_BYTES,
    MAX_FFPROBE_OUTPUT_BYTES,
    SUBPROCESS_CREATION_FLAGS,
    TOOL_PROBE_TIMEOUT_SECONDS,
)
from core.events.event_bus import EventBus
from core.features import FeatureModRegistry
from trusted_ui.conversion_panel import parse_removal_ranges


@pytest.fixture
def service(tmp_path: Path) -> ConversionService:
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffprobe = tmp_path / "ffprobe.exe"
    ffmpeg.write_bytes(b"test")
    ffprobe.write_bytes(b"test")
    presets = Path(__file__).parents[1] / "mod" / "builtin" / "media-convert" / "presets.json"
    instance = ConversionService(
        ffmpeg,
        presets,
        tmp_path / "temp",
        ffprobe=ffprobe,
    )
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
    assert ("-loglevel", "error") == (
        plan.command[plan.command.index("-loglevel") : plan.command.index("-loglevel") + 2]
    )
    assert ("-protocol_whitelist", LOCAL_PROTOCOL_WHITELIST) == (
        plan.command[
            plan.command.index("-protocol_whitelist") :
            plan.command.index("-protocol_whitelist") + 2
        ]
    )
    assert "http" not in LOCAL_PROTOCOL_WHITELIST
    assert "https" not in LOCAL_PROTOCOL_WHITELIST
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


@pytest.mark.parametrize(
    ("preset", "source_name", "output_name", "codec"),
    [
        ("image-png", "source.jpg", "output.png", "png"),
        ("image-jpeg", "source.png", "output.jpg", "mjpeg"),
        ("image-webp", "source.png", "output.webp", "libwebp"),
    ],
)
def test_still_image_presets_use_one_frame_and_reject_non_image_sources(
    service: ConversionService,
    tmp_path: Path,
    preset: str,
    source_name: str,
    output_name: str,
    codec: str,
) -> None:
    source = tmp_path / source_name
    source.write_bytes(b"image fixture")

    plan = service.preview(
        ConversionRequest((source,), tmp_path / output_name, preset)
    )

    assert plan.request.preset == preset
    assert ("-frames:v", "1") == tuple(
        plan.command[index : index + 2]
        for index, value in enumerate(plan.command)
        if value == "-frames:v"
    )[0]
    assert codec in plan.command
    assert "@OUTPUT@" in plan.command

    non_image = tmp_path / "source.mp4"
    non_image.write_bytes(b"video fixture")
    with pytest.raises(ValueError, match="source extension"):
        service.preview(
            ConversionRequest((non_image,), tmp_path / output_name, preset)
        )


def test_capability_probe_reports_only_observed_local_features(
    service: ConversionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outputs = {
        "-version": "ffmpeg version 8.1.2 Copyright FFmpeg developers",
        "-buildconf": "configuration:\n  --enable-gpl\n  --enable-libwebp",
        "-formats": " DE matroska        Matroska\n DE image2          image2 sequence",
        "-encoders": " V....D h264_nvenc  NVIDIA NVENC H.264\n V..... libx264     H.264",
        "-filters": " ... overlay         Overlay a video source\n ... scale           Scale video",
        "-hwaccels": "Hardware acceleration methods:\ncuda\nd3d11va\n",
    }

    monkeypatch.setattr(
        service,
        "_probe_text",
        lambda flag: (outputs[flag], ""),
    )

    capabilities = service.capabilities(refresh=True)

    assert isinstance(capabilities, ConversionCapabilities)
    assert capabilities.ffmpeg_version == "ffmpeg version 8.1.2 Copyright FFmpeg developers"
    assert "--enable-libwebp" in capabilities.build_configuration
    assert capabilities.formats == frozenset({"matroska", "image2"})
    assert capabilities.encoders == frozenset({"h264_nvenc", "libx264"})
    assert capabilities.filters == frozenset({"overlay", "scale"})
    assert capabilities.hwaccels == frozenset({"cuda", "d3d11va"})
    assert capabilities.supports_h264_nvenc
    assert capabilities.errors == ()


def test_capability_probe_does_not_invent_features_after_probe_failure(
    service: ConversionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service,
        "_probe_text",
        lambda flag: ("", f"{flag} probe unavailable"),
    )

    capabilities = service.capabilities(refresh=True)

    assert not capabilities.supports_h264_nvenc
    assert capabilities.encoders == frozenset()
    assert len(capabilities.errors) == 6


def test_capability_probe_invocation_is_local_bounded_and_hidden(
    service: ConversionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = tuple(command)
        captured.update(kwargs)
        return 0, b"ffmpeg version 8.1.2\n", b"", False, False

    monkeypatch.setattr(service, "_run_bounded_capture", fake_run)

    output, error = service._probe_text("-version")

    assert error == ""
    assert output == "ffmpeg version 8.1.2"
    assert captured["command"] == (
        str(service.ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-version",
    )
    assert captured["timeout"] == TOOL_PROBE_TIMEOUT_SECONDS
    assert captured["stdout_limit"] == MAX_CAPABILITY_OUTPUT_BYTES


def test_submit_rejects_obviously_insufficient_output_disk_before_queueing(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    service.set_enabled(True)
    monkeypatch.setattr(
        "core.conversion.service.shutil.disk_usage",
        lambda _path: SimpleNamespace(
            free=DEFAULT_CONVERSION_FREE_SPACE_RESERVE
        ),
    )

    with pytest.raises(RuntimeError, match="disk space"):
        service.submit(
            ConversionRequest(
                (source,),
                tmp_path / "output.mkv",
                "remux-copy",
            )
        )

    assert service.snapshots() == ()


def test_ffprobe_failure_discards_partial_output_before_atomic_commit(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mkv"
    plan = service.preview(ConversionRequest((source,), output, "remux-copy"))
    task = ConversionTask("probe-failure", plan.request)

    def fake_run(command, _cancel_event):
        Path(command[-1]).write_bytes(b"invalid media")
        return 0, ""

    monkeypatch.setattr(service, "_run", fake_run)
    monkeypatch.setattr(
        service,
        "_run_ffprobe",
        lambda _path: (1, b"", "Invalid data found when processing input"),
    )

    with pytest.raises(RuntimeError, match="ffprobe"):
        service._execute(task, plan)

    assert not output.exists()
    assert not list(tmp_path.glob("*.part.mkv"))


def test_ffprobe_accepts_bounded_json_with_at_least_one_stream(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "verified.part.mp4"
    output.write_bytes(b"verified media")
    payload = b'{"streams":[{"index":0,"codec_type":"video","codec_name":"h264"}],"format":{"size":"14"}}'
    monkeypatch.setattr(
        service,
        "_run_ffprobe",
        lambda _path: (0, payload, ""),
    )

    service._verify_output(output)


def test_ffprobe_invocation_is_local_bounded_and_hidden(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "output.part.mkv"
    output.write_bytes(b"media")
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = tuple(command)
        captured.update(kwargs)
        return 0, b'{"streams":[{"codec_type":"video"}]}', b"", False, False

    monkeypatch.setattr(service, "_run_bounded_capture", fake_run)

    return_code, document, diagnostic = service._run_ffprobe(output)

    assert return_code == 0
    assert document.startswith(b'{"streams"')
    assert diagnostic == ""
    command = captured["command"]
    assert command[0] == str(service.ffprobe)
    assert ("-protocol_whitelist", LOCAL_PROTOCOL_WHITELIST) == command[
        command.index("-protocol_whitelist") :
        command.index("-protocol_whitelist") + 2
    ]
    assert "http" not in command
    assert "https" not in command
    assert captured["stdout_limit"] == MAX_FFPROBE_OUTPUT_BYTES


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b'{"streams":[]}',
        b'{"streams":["not-an-object"]}',
    ],
)
def test_ffprobe_rejects_invalid_or_streamless_documents(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    output = tmp_path / "invalid.part.mkv"
    output.write_bytes(b"invalid")
    monkeypatch.setattr(
        service,
        "_run_ffprobe",
        lambda _path: (0, payload, ""),
    )

    with pytest.raises(RuntimeError, match="ffprobe"):
        service._verify_output(output)


def test_ffprobe_rejects_oversized_json_before_parsing(
    service: ConversionService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "oversized.part.mkv"
    output.write_bytes(b"media")
    monkeypatch.setattr(
        service,
        "_run_bounded_capture",
        lambda *_args, **_kwargs: (
            0,
            b"x" * MAX_FFPROBE_OUTPUT_BYTES,
            b"",
            True,
            False,
        ),
    )

    return_code, document, diagnostic = service._run_ffprobe(output)

    assert return_code == 1
    assert document == b""
    assert diagnostic == "ffprobe output exceeded the size limit"


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
            return 0, ""
        return 1, "GPU encoder unavailable"

    monkeypatch.setattr(service, "_run", fake_run)
    monkeypatch.setattr(service, "_verify_output", lambda _path: None)
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
        return 1, "cancelled"

    monkeypatch.setattr(service, "_run", fake_run)
    with pytest.raises(RuntimeError, match="cancelled"):
        service._execute(task, plan)
    assert not output.exists()
    assert not list(tmp_path.glob("*.part.mkv"))


def test_ffmpeg_failure_diagnostic_is_bounded_redacted_and_drained(
    service: ConversionService,
) -> None:
    script = (
        "import sys\n"
        "sys.stderr.write('x' * (1024 * 1024))\n"
        "sys.stderr.write('\\nCookie: secret-cookie\\n')\n"
        "sys.stderr.flush()\n"
        "raise SystemExit(7)\n"
    )

    return_code, diagnostic = service._run(
        (sys.executable, "-c", script), Event()
    )

    assert return_code == 7
    assert "secret-cookie" not in diagnostic
    assert "[REDACTED]" in diagnostic
    assert len(diagnostic.encode("utf-8")) <= 64 * 1024
    assert "truncated" in diagnostic


def test_ffmpeg_failure_discards_truncated_secret_line_without_header(
    service: ConversionService,
) -> None:
    script = (
        "import sys\n"
        "sys.stderr.write('Cookie: ' + 'secret-tail-' * (128 * 1024))\n"
        "sys.stderr.flush()\n"
        "raise SystemExit(9)\n"
    )

    return_code, diagnostic = service._run(
        (sys.executable, "-c", script), Event()
    )

    assert return_code == 9
    assert "secret-tail" not in diagnostic
    assert diagnostic == "[FFmpeg stderr truncated]"


def test_ffmpeg_process_uses_platform_safe_creation_flags(
    service: ConversionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int] = {}

    class FakeProcess:
        returncode = 0

        def __init__(self) -> None:
            from io import BytesIO

            self.stderr = BytesIO(b"")

        def poll(self) -> int:
            return 0

    def fake_popen(_command, **kwargs):
        captured["creationflags"] = int(kwargs["creationflags"])
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    assert service._run(("ffmpeg",), Event()) == (0, "")
    assert captured["creationflags"] == SUBPROCESS_CREATION_FLAGS


def test_ffmpeg_stderr_reader_timeout_does_not_block_worker(
    service: ConversionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_reader = Event()

    class BlockingStderr:
        def read(self, _size: int) -> bytes:
            release_reader.wait(timeout=1)
            return b""

    class FakeProcess:
        returncode = 3
        stderr = BlockingStderr()

        def poll(self) -> int:
            return 3

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(
        "core.conversion.service.STDERR_READER_JOIN_SECONDS", 0.01
    )

    result: list[tuple[int, str]] = []
    worker = Thread(
        target=lambda: result.append(service._run(("ffmpeg",), Event()))
    )
    worker.start()
    worker.join(timeout=0.5)
    release_reader.set()
    worker.join(timeout=0.5)

    assert not worker.is_alive()
    assert result == [(3, "[FFmpeg stderr reader incomplete]")]


def test_service_is_disabled_by_default(service: ConversionService, tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    with pytest.raises(RuntimeError, match="disabled"):
        service.submit(ConversionRequest((source,), tmp_path / "output.mkv", "remux-copy"))


def test_service_requires_both_ffmpeg_and_ffprobe(
    tmp_path: Path,
) -> None:
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"test")
    presets = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "media-convert"
        / "presets.json"
    )
    service = ConversionService(ffmpeg, presets, tmp_path / "temp")
    try:
        assert not service.available
        with pytest.raises(RuntimeError, match="FFmpeg"):
            service.set_enabled(True)
    finally:
        service.close()


def test_conversion_rejects_symlink_source_and_output_folder(
    service: ConversionService,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    source_link = tmp_path / "source-link.mp4"
    output_folder = tmp_path / "output"
    output_folder.mkdir()
    output_link = tmp_path / "output-link"
    try:
        source_link.symlink_to(source)
        output_link.symlink_to(output_folder, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")

    with pytest.raises(ValueError, match="regular file"):
        service.preview(
            ConversionRequest(
                (source_link,), tmp_path / "linked-source.mkv", "remux-copy"
            )
        )
    with pytest.raises(ValueError, match="output folder"):
        service.preview(
            ConversionRequest(
                (source,), output_link / "linked-output.mkv", "remux-copy"
            )
        )


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
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("local FFmpeg / ffprobe is not installed")
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
    service = ConversionService(
        Path(ffmpeg),
        presets,
        tmp_path / "temp",
        ffprobe=Path(ffprobe),
    )
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


def test_local_ffmpeg_capability_probe_smoke(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("local FFmpeg / ffprobe is not installed")
    presets = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "media-convert"
        / "presets.json"
    )
    service = ConversionService(
        Path(ffmpeg),
        presets,
        tmp_path / "temp",
        ffprobe=Path(ffprobe),
    )
    try:
        capabilities = service.capabilities(refresh=True)
        assert capabilities.ffmpeg_version.casefold().startswith("ffmpeg version ")
        assert capabilities.formats
        assert capabilities.encoders
        assert capabilities.filters
        assert capabilities.errors == ()
    finally:
        service.close()


def test_local_ffmpeg_still_image_conversion_smoke(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("local FFmpeg / ffprobe is not installed")
    source = tmp_path / "source.bmp"
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
            "color=c=blue:s=16x16:d=0.04",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(source),
        ],
        check=True,
        timeout=10,
    )
    presets = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "media-convert"
        / "presets.json"
    )
    service = ConversionService(
        Path(ffmpeg),
        presets,
        tmp_path / "temp",
        ffprobe=Path(ffprobe),
    )
    try:
        service.set_enabled(True)
        output = tmp_path / "output.png"
        task_id = service.submit(
            ConversionRequest((source,), output, "image-png")
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            task = next(
                task
                for task in service.snapshots()
                if task.task_id == task_id
            )
            if task.state.name in {"COMPLETED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.05)
        assert task.state.name == "COMPLETED", task.error
        assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        service.close()
