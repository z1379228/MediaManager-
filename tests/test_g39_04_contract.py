from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.builtin_mod_catalog import BUILTIN_MOD_CATALOG
from core.conversion import ConversionRequest, ConversionService
from trusted_ui.conversion_panel import CONVERSION_WORKSPACE_LABEL


ROOT = Path(__file__).parents[1]


def test_only_automation_and_speech_to_text_are_disabled_for_new_profiles() -> None:
    disabled = {
        item.provider_id for item in BUILTIN_MOD_CATALOG if not item.default_enabled
    }
    assert disabled == {"automation", "speech-to-text"}


def test_speech_runtime_dependencies_are_explicitly_optional() -> None:
    speech = next(
        item for item in BUILTIN_MOD_CATALOG if item.provider_id == "speech-to-text"
    )
    assert speech.dependency_ids == ()
    assert speech.optional_dependency_ids == ("whisper-cli", "speech-model")


def test_format_factory_has_consistent_name_and_expanded_format_types() -> None:
    assert CONVERSION_WORKSPACE_LABEL == "格式工廠"
    document = json.loads(
        (ROOT / "mod" / "builtin" / "media-convert" / "presets.json").read_text(
            encoding="utf-8"
        )
    )
    assert {
        "video-vp9-webm",
        "video-mpeg4-avi",
        "audio-aac",
        "audio-opus",
        "audio-wav",
        "image-bmp",
        "image-tiff",
    }.issubset(document["presets"])


@pytest.mark.parametrize(
    ("preset", "source_name", "output_name", "codec"),
    (
        ("video-vp9-webm", "source.mp4", "output.webm", "libvpx-vp9"),
        ("video-mpeg4-avi", "source.mkv", "output.avi", "mpeg4"),
        ("audio-aac", "source.wav", "output.m4a", "aac"),
        ("audio-opus", "source.wav", "output.opus", "libopus"),
        ("audio-wav", "source.mp3", "output.wav", "pcm_s16le"),
        ("image-bmp", "source.png", "output.bmp", "bmp"),
        ("image-tiff", "source.jpg", "output.tiff", "tiff"),
    ),
)
def test_expanded_format_presets_build_fixed_local_commands(
    tmp_path: Path,
    preset: str,
    source_name: str,
    output_name: str,
    codec: str,
) -> None:
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffprobe = tmp_path / "ffprobe.exe"
    ffmpeg.write_bytes(b"test")
    ffprobe.write_bytes(b"test")
    service = ConversionService(
        ffmpeg,
        ROOT / "mod" / "builtin" / "media-convert" / "presets.json",
        tmp_path / "temp",
        ffprobe=ffprobe,
    )
    source = tmp_path / source_name
    source.write_bytes(b"fixture")
    try:
        plan = service.preview(
            ConversionRequest((source,), tmp_path / output_name, preset)
        )
        assert codec in plan.command
        assert "http" not in plan.command
        assert "https" not in plan.command
    finally:
        service.close()


def test_feature_manifests_match_new_profile_defaults() -> None:
    for name in (
        "media-convert",
        "media-ad-trim",
        "gopeed-transfer",
        "p2p-transfer",
    ):
        document = json.loads(
            (ROOT / "mod" / "builtin" / name / "feature.json").read_text(
                encoding="utf-8"
            )
        )
        assert document["default_enabled"] is True
    for name in ("speech-to-text", "automation"):
        document = json.loads(
            (ROOT / "mod" / "builtin" / name / "feature.json").read_text(
                encoding="utf-8"
            )
        )
        assert document["default_enabled"] is False


def test_transfer_workspace_uses_minimum_size_scroll_contract() -> None:
    source = (ROOT / "trusted_ui" / "transfer_panel.py").read_text(
        encoding="utf-8"
    )
    assert 'scroll.setObjectName("workspaceScroll")' in source
    assert "scroll.setWidgetResizable(True)" in source
    assert "Qt.ScrollBarPolicy.ScrollBarAlwaysOff" in source
    assert "page.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)" in source
    assert "shell.addWidget(scroll)" in source
