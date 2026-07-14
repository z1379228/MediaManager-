from pathlib import Path

import pytest

from tools import build_version
from tools.build_version import (
    configured_project_version,
    portable_release_tools,
    validate_build_version,
    version_build_paths,
    wheel_build_command,
)
from core.version import CORE_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_build_version_sources_match_and_override_is_rejected() -> None:
    assert configured_project_version(ROOT) == CORE_VERSION
    validate_build_version(ROOT, CORE_VERSION)
    with pytest.raises(ValueError, match="override is not allowed"):
        validate_build_version(ROOT, "5.0.1")


def test_version_build_paths_are_isolated_under_work(tmp_path: Path) -> None:
    paths = version_build_paths(tmp_path, "1.2.3")
    assert paths.work == tmp_path / ".work" / "Development" / "1.2"
    assert paths.temp == paths.work / "temp"
    assert paths.pyinstaller_work == paths.work / "pyinstaller"
    assert paths.executable_output == paths.work / "exe"
    assert paths.wheel_output == paths.work / "wheel"
    retry = version_build_paths(tmp_path, "1.2.3", attempt_id="a1b2c3d4")
    assert retry.work == (
        tmp_path / ".work" / "Development" / "1.2-attempt-a1b2c3d4"
    )
    with pytest.raises(ValueError, match="attempt id"):
        version_build_paths(tmp_path, "1.2.3", attempt_id="../unsafe")


def test_stable_build_path_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="explicit user confirmation"):
        build_version.build_version(
            tmp_path,
            CORE_VERSION,
            portable_runtime=False,
            channel="stable",
        )


def test_portable_release_tools_fail_fast_when_cache_is_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="portable Deno"):
        portable_release_tools(tmp_path, enabled=True)
    assert portable_release_tools(tmp_path, enabled=False) == {}


def test_portable_release_tools_include_runtime_and_license(
    tmp_path: Path, monkeypatch
) -> None:
    deno = tmp_path / "deno.exe"
    deno.write_bytes(b"deno")
    license_file = tmp_path / "third_party" / "deno" / "LICENSE.md"
    license_file.parent.mkdir(parents=True)
    license_file.write_text("license", encoding="utf-8")
    monkeypatch.setattr(build_version, "cached_runtime_path", lambda _root: deno)
    ffmpeg = {
        name: tmp_path / name
        for name in (
            "ffmpeg.exe",
            "ffprobe.exe",
            "FFMPEG-LICENSE.txt",
            "FFMPEG-README.txt",
        )
    }
    for path in ffmpeg.values():
        path.write_bytes(b"file")
    monkeypatch.setattr(build_version, "cached_ffmpeg_paths", lambda _root: ffmpeg)

    assert portable_release_tools(tmp_path, enabled=True) == {
        "deno.exe": deno,
        "DENO-LICENSE.md": license_file,
        **ffmpeg,
    }


def test_wheel_build_uses_existing_environment_without_dependencies(
    tmp_path: Path,
) -> None:
    command = wheel_build_command(Path("python.exe"), tmp_path / "wheel")
    assert "--no-deps" in command
    assert "--no-build-isolation" in command
    assert command[-2:] == ["--wheel-dir", str(tmp_path / "wheel")]
