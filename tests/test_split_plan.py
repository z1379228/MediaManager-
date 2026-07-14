import importlib.util
import subprocess
from pathlib import Path

import pytest

from contracts.split_plan_v1 import SplitPlanContractError, SplitPlanV1
from core.downloads.subprocess_provider import (
    ProviderProtocolError,
    SubprocessDownloadProvider,
)


def valid_plan() -> dict[str, object]:
    evidence = {
        "source": "chapters",
        "confidence": 0.95,
        "detail": "source chapter",
    }
    return {
        "source_url": "https://www.youtube.com/watch?v=example",
        "source_title": "作業用 BGM",
        "duration": 300,
        "composite_likely": True,
        "segments": [
            {
                "index": 1,
                "start": 0,
                "end": 120,
                "title": "Track 1",
                "evidence": [evidence],
            },
            {
                "index": 2,
                "start": 120,
                "end": 300,
                "title": "Track 2",
                "evidence": [evidence],
            },
        ],
        "warnings": [],
    }


def split_provider() -> SubprocessDownloadProvider:
    root = Path(__file__).parents[1]
    return SubprocessDownloadProvider(
        root / "mod" / "builtin" / "youtube-auto-split",
        application_root=root,
    )


def split_provider_module():
    path = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "youtube-auto-split"
        / "provider.py"
    )
    spec = importlib.util.spec_from_file_location("test_auto_split_provider", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_split_plan_contract_accepts_ordered_segments() -> None:
    plan = SplitPlanV1.from_dict(valid_plan())
    assert plan.composite_likely
    assert plan.segments[1].start == 120
    assert plan.segments[0].evidence[0].source == "chapters"


def test_split_plan_contract_rejects_overlap() -> None:
    raw = valid_plan()
    raw["segments"][1]["start"] = 100  # type: ignore[index]
    with pytest.raises(SplitPlanContractError, match="order"):
        SplitPlanV1.from_dict(raw)


def test_split_plan_contract_requires_two_likely_segments() -> None:
    raw = valid_plan()
    raw["segments"] = raw["segments"][:1]  # type: ignore[index]
    with pytest.raises(SplitPlanContractError, match="at least two"):
        SplitPlanV1.from_dict(raw)


def test_split_filename_is_safe_stable_and_bounded() -> None:
    provider = split_provider()
    try:
        filename = provider.split_filename(
            source_title="作業用:BGM",
            index=1,
            track_title="歌/曲",
            start=62,
            duration=222,
            extension="M4A",
        )
        assert filename == "作業用_BGM-01-歌_曲-01m02s-03m42s.m4a"
        bounded = provider.split_filename(
            source_title="a" * 500,
            index=999,
            track_title="unnamed",
            start=0,
            duration=1,
            extension="mp4",
        )
        assert len(bounded) <= 180
    finally:
        provider.close()


def test_split_plan_prefers_source_chapters() -> None:
    provider = split_provider()
    try:
        plan = provider.split_plan(
            source_url="https://www.youtube.com/watch?v=example",
            source_title="Study mix",
            duration=300,
            chapters=[
                {"start_time": 0, "end_time": 120, "title": "Chapter A"},
                {"start_time": 120, "end_time": 300, "title": "Chapter B"},
            ],
            description="0:00 Wrong A\n1:00 Wrong B",
        )
        assert plan.composite_likely
        assert [segment.title for segment in plan.segments] == [
            "Chapter A",
            "Chapter B",
        ]
        assert plan.segments[0].evidence[0].source == "chapters"
        assert plan.warnings == ()
    finally:
        provider.close()


def test_split_plan_falls_back_to_description_timestamps() -> None:
    provider = split_provider()
    try:
        plan = provider.split_plan(
            source_url="https://youtu.be/example",
            source_title="Work BGM",
            duration=600,
            chapters=[],
            description="Track list\n00:00 First Song\n03:42 - Second Song\n7:30 Third Song",
        )
        assert [(item.start, item.end, item.title) for item in plan.segments] == [
            (0.0, 222.0, "First Song"),
            (222.0, 450.0, "Second Song"),
            (450.0, 600.0, "Third Song"),
        ]
        assert plan.segments[0].evidence[0].source == "description"
        assert plan.warnings
    finally:
        provider.close()


def test_split_plan_does_not_guess_without_multiple_boundaries() -> None:
    provider = split_provider()
    try:
        plan = provider.split_plan(
            source_url="https://www.youtube.com/watch?v=example",
            source_title="Continuous live mix",
            duration=3600,
            chapters=[],
            description="No track list is available.",
        )
        assert not plan.composite_likely
        assert plan.segments == ()
        assert plan.warnings == (
            "No reliable chapter or description split evidence was found.",
        )
    finally:
        provider.close()


def test_audio_silence_plan_is_bounded_and_low_confidence(
    tmp_path: Path, monkeypatch
) -> None:
    module = split_provider_module()
    source = tmp_path / "preview.wav"
    ffmpeg = tmp_path / "ffmpeg.exe"
    source.write_bytes(b"audio")
    ffmpeg.write_bytes(b"executable")
    stderr = "\n".join(
        (
            "[silencedetect] silence_start: 20.0",
            "[silencedetect] silence_end: 22.0 | silence_duration: 2.0",
        )
    )
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", stderr)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    plan = SplitPlanV1.from_dict(
        module.audio_split_plan(
            {
                "source_url": "https://youtu.be/example",
                "source_title": "Long mix",
                "duration": 10_000,
                "input_path": str(source),
                "ffmpeg_location": str(ffmpeg),
                "threshold_db": -35,
                "min_silence": 1.2,
            }
        )
    )
    assert not plan.composite_likely
    assert len(plan.segments) == 2
    assert plan.segments[0].end == 21
    assert plan.segments[0].evidence[0].source == "silence"
    assert plan.segments[0].evidence[0].confidence == 0.65
    assert "first two hours" in plan.warnings[1]
    command = commands[0]
    assert command[command.index("-threads") + 1] == "1"
    assert command[command.index("-ar") + 1] == "8000"
    assert command[command.index("-t") + 1] == "7200.000"


def test_audio_analysis_rejects_input_outside_temporary_root(tmp_path: Path) -> None:
    analysis_root = tmp_path / "analysis"
    analysis_root.mkdir()
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"audio")
    provider = SubprocessDownloadProvider(
        Path(__file__).parents[1] / "mod" / "builtin" / "youtube-auto-split",
        application_root=tmp_path,
        ffmpeg_location=str(tmp_path / "ffmpeg.exe"),
        analysis_root=analysis_root,
    )
    try:
        with pytest.raises(ProviderProtocolError, match="outside the temporary root"):
            provider.split_audio_plan(
                source_url="https://youtu.be/example",
                source_title="Mix",
                duration=60,
                input_path=outside,
            )
    finally:
        provider.close()
