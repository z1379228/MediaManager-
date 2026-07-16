from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.security.release_layout import (
    DEFAULT_RELEASE_FILES,
    PINNED_BUILTIN_RELEASE_FILES,
    SOURCE_RELEASE_FILES,
)
from tools import stage_version as stage_module
from tools.stage_version import stage_version, version_folder_name


def test_release_layout_includes_every_pinned_builtin_mod_file() -> None:
    release_mod_files = {
        path for path in SOURCE_RELEASE_FILES if path.startswith("mod/builtin/")
    }

    assert release_mod_files == set(PINNED_BUILTIN_RELEASE_FILES)


def _prepare_source(root: Path, version: str = "1.2.3") -> None:
    (root / "dist").mkdir()
    (root / "dist" / "MediaManager.exe").write_bytes(b"exe")
    (root / "dist-packages").mkdir()
    (root / "dist-packages" / f"mediamanager-{version}-py3-none-any.whl").write_bytes(
        b"wheel"
    )
    for name in SOURCE_RELEASE_FILES[1:]:
        path = root / Path(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode("utf-8"))


def test_version_folder_uses_major_minor() -> None:
    assert version_folder_name("1.0.0") == "1.0"
    assert version_folder_name("12.34.5") == "12.34"


def test_stage_version_creates_complete_version_folder(tmp_path: Path) -> None:
    _prepare_source(tmp_path)
    deno = tmp_path / "deno.exe"
    deno.write_bytes(b"deno")
    license_file = tmp_path / "DENO-LICENSE.md"
    license_file.write_text("license", encoding="utf-8")
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffprobe = tmp_path / "ffprobe.exe"
    ffmpeg_license = tmp_path / "FFMPEG-LICENSE.txt"
    ffmpeg_readme = tmp_path / "FFMPEG-README.txt"
    for path in (ffmpeg, ffprobe, ffmpeg_license, ffmpeg_readme):
        path.write_bytes(path.name.encode("ascii"))
    target = stage_version(
        tmp_path,
        version="1.2.3",
        channel="development",
        portable_tools={
            "deno.exe": deno,
            "DENO-LICENSE.md": license_file,
            "ffmpeg.exe": ffmpeg,
            "ffprobe.exe": ffprobe,
            "FFMPEG-LICENSE.txt": ffmpeg_license,
            "FFMPEG-README.txt": ffmpeg_readme,
        },
    )
    assert target == tmp_path / "Version" / "Development" / "1.2"
    assert (target / "MediaManager.exe").read_bytes() == b"exe"
    info = json.loads((target / "release-info.json").read_text("utf-8"))
    assert info["core_version"] == "1.2.3"
    assert info["schema_version"] == 3
    assert info["tool_schema_version"] == 3
    assert info["release_version"] == "1.2.3"
    assert info["build_channel"] == "development"
    assert info["release_track"] == "Development"
    assert info["version_folder"] == "1.2"
    assert len(info["source_fingerprint"]) == 64
    assert len(info["build_id"]) == 64
    assert info["source_revision"] == "unavailable" or len(info["source_revision"]) in {
        40,
        64,
    }
    assert info["portable_tools"] == [
        "DENO-LICENSE.md",
        "FFMPEG-LICENSE.txt",
        "FFMPEG-README.txt",
        "deno.exe",
        "ffmpeg.exe",
        "ffprobe.exe",
    ]
    assert (target / "tools" / "deno.exe").read_bytes() == b"deno"
    inventory = json.loads(
        (target / "dependency-inventory.json").read_text("utf-8")
    )
    sbom = json.loads((target / "sbom.cdx.json").read_text("utf-8"))
    assert inventory["core_version"] == "1.2.3"
    assert sbom["bomFormat"] == "CycloneDX"
    checksums = (target / "SHA256SUMS.txt").read_text("utf-8")
    expected = hashlib.sha256(b"exe").hexdigest()
    assert f"{expected}  MediaManager.exe" in checksums
    assert "安裝必備軟體.bat" in checksums
    for name in DEFAULT_RELEASE_FILES[1:]:
        assert (target / Path(*name.split("/"))).is_file()


def test_stage_version_rejects_unsafe_portable_tool_name(tmp_path: Path) -> None:
    _prepare_source(tmp_path)
    tool = tmp_path / "tool.exe"
    tool.write_bytes(b"tool")
    try:
        stage_version(
            tmp_path,
            version="1.2.3",
            channel="development",
            portable_tools={"../tool.exe": tool},
        )
    except ValueError as error:
        assert "unsafe portable tool name" in str(error)
    else:
        raise AssertionError("unsafe portable tool name was accepted")


def test_stage_version_refuses_to_replace_existing_version(tmp_path: Path) -> None:
    _prepare_source(tmp_path)
    target = stage_version(tmp_path, version="1.2.3", channel="development")
    (target / "stale.txt").write_text("old", encoding="utf-8")
    (tmp_path / "dist" / "MediaManager.exe").write_bytes(b"new")
    with pytest.raises(FileExistsError, match="increment the development minor"):
        stage_version(tmp_path, version="1.2.3", channel="development")
    assert (target / "MediaManager.exe").read_bytes() == b"exe"
    assert (target / "stale.txt").read_text(encoding="utf-8") == "old"


def test_stage_version_retries_short_permission_error(
    tmp_path: Path, monkeypatch
) -> None:
    _prepare_source(tmp_path)
    real_replace = Path.replace
    attempts = 0

    def locked_twice(source: Path, target: Path) -> Path:
        nonlocal attempts
        if source.name == ".1.2.staging":
            attempts += 1
            if attempts < 3:
                raise PermissionError("temporary scanner lock")
        return real_replace(source, target)

    monkeypatch.setattr(Path, "replace", locked_twice)
    monkeypatch.setattr(stage_module.time, "sleep", lambda _seconds: None)

    target = stage_version(tmp_path, version="1.2.3", channel="development")

    assert target.is_dir()
    assert attempts == 3


def test_stage_version_recovers_legacy_backup_without_overwriting_target(
    tmp_path: Path,
) -> None:
    _prepare_source(tmp_path)
    track = tmp_path / "Version" / "Development"
    track.mkdir(parents=True)
    backup = track / ".1.2.backup"
    backup.mkdir()
    (backup / "MediaManager.exe").write_bytes(b"old")

    with pytest.raises(FileExistsError, match="increment the development minor"):
        stage_version(tmp_path, version="1.2.3", channel="development")

    assert (track / "1.2" / "MediaManager.exe").read_bytes() == b"old"
    assert not backup.exists()


def test_stage_version_refuses_stable_without_explicit_confirmation(
    tmp_path: Path,
) -> None:
    _prepare_source(tmp_path)
    with pytest.raises(PermissionError, match="explicit user confirmation"):
        stage_version(tmp_path, version="1.2.3", channel="stable")

    target = stage_version(
        tmp_path,
        version="1.2.3",
        channel="stable",
        confirm_stable=True,
    )
    assert target == tmp_path / "Version" / "Stable" / "1.2"


def test_stage_version_separates_testing_and_core_versions(tmp_path: Path) -> None:
    _prepare_source(tmp_path, "11.0.0")

    target = stage_version(
        tmp_path,
        version="11.0.0",
        release_version="1.0.0",
        channel="testing",
    )

    assert target == tmp_path / "Version" / "Testing" / "1.0"
    info = json.loads((target / "release-info.json").read_text("utf-8"))
    assert info["core_version"] == "11.0.0"
    assert info["release_version"] == "1.0.0"
    assert info["build_channel"] == "testing"
    assert info["release_track"] == "Testing"
