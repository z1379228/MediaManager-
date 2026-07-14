from pathlib import Path

import pytest

from tools import build_version
from tools.build_version import (
    portable_release_tools,
    version_build_paths,
    wheel_build_command,
)


def test_version_build_paths_are_isolated_under_work(tmp_path: Path) -> None:
    paths = version_build_paths(tmp_path, "1.2.3")
    assert paths.work == tmp_path / ".work" / "1.2"
    assert paths.temp == paths.work / "temp"
    assert paths.pyinstaller_work == paths.work / "pyinstaller"
    assert paths.executable_output == paths.work / "exe"
    assert paths.wheel_output == paths.work / "wheel"


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
