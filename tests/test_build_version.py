import json
import subprocess
from pathlib import Path

import pytest

from tools import build_version
from tools.build_version import (
    configured_project_version,
    portable_release_tools,
    validate_clean_source,
    validate_build_version,
    wheel_build_environment,
    version_build_paths,
    wheel_build_command,
)
from core.version import CORE_VERSION


ROOT = Path(__file__).resolve().parents[1]


def _write_receipt_bound_work(
    root: Path,
    *,
    revision: str = "a" * 40,
    channel: str = "stable",
) -> tuple[Path, Path, Path]:
    public_version = build_version.release_identity_version(channel)
    paths = version_build_paths(
        root,
        CORE_VERSION,
        channel=channel,
        release_version=public_version,
        attempt_id="signed",
    )
    paths.executable_output.mkdir(parents=True)
    paths.wheel_output.mkdir(parents=True)
    executable = paths.executable_output / "MediaManager.exe"
    wheel = paths.wheel_output / f"mediamanager-{CORE_VERSION}-py3-none-any.whl"
    executable.write_bytes(b"signed executable")
    wheel.write_bytes(b"wheel")
    build_version.write_build_receipt(
        paths,
        version=CORE_VERSION,
        release_version=public_version,
        channel=channel,
        source_revision=revision,
    )
    return paths.work, executable, wheel


def test_build_version_sources_match_and_override_is_rejected() -> None:
    assert configured_project_version(ROOT) == CORE_VERSION
    validate_build_version(ROOT, CORE_VERSION)
    with pytest.raises(ValueError, match="override is not allowed"):
        validate_build_version(ROOT, "5.0.1")


def test_clean_release_source_returns_exact_revision(monkeypatch) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="a" * 40 + "\n", stderr=""),
        )
    )
    monkeypatch.setattr(build_version.shutil, "which", lambda _name: "git.exe")
    monkeypatch.setattr(
        build_version.subprocess,
        "run",
        lambda *_args, **_kwargs: next(responses),
    )

    assert validate_clean_source(ROOT) == "a" * 40


def test_dirty_release_source_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(build_version.shutil, "which", lambda _name: "git.exe")
    monkeypatch.setattr(
        build_version.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, stdout=" M core/version.py\n", stderr=""
        ),
    )

    with pytest.raises(RuntimeError, match="source is dirty"):
        validate_clean_source(ROOT)


def test_release_source_with_git_status_warning_is_rejected(monkeypatch) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess(
                [],
                0,
                stdout="",
                stderr=(
                    "warning: could not open directory "
                    "'SENSITIVE_SOURCE_PATH': Permission denied\n"
                ),
            ),
            subprocess.CompletedProcess(
                [], 0, stdout="a" * 40 + "\n", stderr=""
            ),
        )
    )
    monkeypatch.setattr(build_version.shutil, "which", lambda _name: "git.exe")
    monkeypatch.setattr(
        build_version.subprocess,
        "run",
        lambda *_args, **_kwargs: next(responses),
    )

    with pytest.raises(RuntimeError, match="source inspection is incomplete") as error:
        validate_clean_source(ROOT)

    assert "SENSITIVE_SOURCE_PATH" not in str(error.value)


def test_version_build_paths_are_isolated_under_work(tmp_path: Path) -> None:
    paths = version_build_paths(
        tmp_path,
        "11.0.0",
        channel="testing",
        release_version="1.0.0",
    )
    assert paths.work == tmp_path / ".work" / "Testing" / "1.0"
    assert paths.temp == paths.work / "temp"
    assert paths.pyinstaller_work == paths.work / "pyinstaller"
    assert paths.executable_output == paths.work / "exe"
    assert paths.wheel_output == paths.work / "wheel"
    retry = version_build_paths(
        tmp_path,
        "1.2.3",
        channel="development",
        attempt_id="a1b2c3d4",
    )
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


def test_wheel_build_environment_is_confined_to_build_attempt(
    tmp_path: Path,
) -> None:
    temp_root = tmp_path / ".work" / "Development" / "14.1-attempt-test" / "temp"
    environment = wheel_build_environment({"PATH": "example"}, temp_root)

    assert environment["PATH"] == "example"
    assert environment["TEMP"] == str(temp_root)
    assert environment["TMP"] == str(temp_root)
    assert environment["PIP_BUILD_TRACKER"] == str(temp_root / "build-tracker")
    assert environment["PIP_CACHE_DIR"] == str(temp_root / "cache")
    assert environment["PIP_NO_INDEX"] == "1"
    assert (temp_root / "build-tracker").is_dir()
    assert (temp_root / "cache").is_dir()


def test_failed_build_removes_only_its_attempt_directory(
    tmp_path: Path, monkeypatch
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"python")
    python.with_name("pyinstaller.exe").write_bytes(b"pyinstaller")
    preserved = tmp_path / ".work" / "Development" / "previous"
    preserved.mkdir(parents=True)
    (preserved / "keep.txt").write_text("keep", encoding="utf-8")

    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "failed")
    monkeypatch.setattr(build_version.sys, "executable", str(python))

    def fail_build(*_args, **_kwargs) -> None:
        raise subprocess.CalledProcessError(1, "pyinstaller")

    monkeypatch.setattr(build_version.subprocess, "run", fail_build)

    with pytest.raises(subprocess.CalledProcessError):
        build_version.build_version(tmp_path, CORE_VERSION, portable_runtime=False)

    attempt = version_build_paths(
        tmp_path,
        CORE_VERSION,
        channel="development",
        release_version=build_version.release_identity_version("development"),
        attempt_id="failed",
    )
    assert not attempt.work.exists()
    assert (preserved / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_build_rejects_preexisting_generated_paths_without_deleting_them(
    tmp_path: Path, monkeypatch
) -> None:
    build_sentinel = tmp_path / "build" / "keep.txt"
    egg_sentinel = tmp_path / "mediamanager.egg-info" / "keep.txt"
    for sentinel in (build_sentinel, egg_sentinel):
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)

    with pytest.raises(FileExistsError, match="pre-existing generated paths"):
        build_version.build_version(tmp_path, CORE_VERSION, portable_runtime=False)

    assert build_sentinel.read_text(encoding="utf-8") == "keep"
    assert egg_sentinel.read_text(encoding="utf-8") == "keep"


def test_failed_build_preserves_generated_paths_created_after_preflight(
    tmp_path: Path, monkeypatch
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"python")
    python.with_name("pyinstaller.exe").write_bytes(b"pyinstaller")

    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "raced")
    monkeypatch.setattr(build_version.sys, "executable", str(python))

    build_sentinel = tmp_path / "build" / "other-owner.txt"
    egg_sentinel = tmp_path / "mediamanager.egg-info" / "other-owner.txt"

    def fail_after_external_generation(*_args, **_kwargs) -> None:
        for sentinel in (build_sentinel, egg_sentinel):
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("keep", encoding="utf-8")
        raise subprocess.CalledProcessError(1, "pyinstaller")

    monkeypatch.setattr(
        build_version.subprocess,
        "run",
        fail_after_external_generation,
    )

    with pytest.raises(subprocess.CalledProcessError):
        build_version.build_version(tmp_path, CORE_VERSION, portable_runtime=False)

    assert build_sentinel.read_text(encoding="utf-8") == "keep"
    assert egg_sentinel.read_text(encoding="utf-8") == "keep"


def test_build_attempt_collision_preserves_existing_directory(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "collision")

    paths = version_build_paths(
        tmp_path,
        CORE_VERSION,
        channel="development",
        release_version=build_version.release_identity_version("development"),
        attempt_id="collision",
    )
    paths.work.mkdir(parents=True)
    sentinel = paths.work / "other-owner.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        build_version.build_version(tmp_path, CORE_VERSION, portable_runtime=False)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_external_temp_root_is_isolated_and_cleaned_after_failed_build(
    tmp_path: Path, monkeypatch
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"python")
    python.with_name("pyinstaller.exe").write_bytes(b"pyinstaller")
    selected_temp_root = tmp_path / "user-local-temp"
    preserved_sibling = selected_temp_root / "preserved-sibling"
    preserved_sibling.mkdir(parents=True)
    (preserved_sibling / "keep.txt").write_text("keep", encoding="utf-8")
    captured_environment: dict[str, str] = {}

    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "external")
    monkeypatch.setattr(build_version.sys, "executable", str(python))

    def fail_build(*_args, **kwargs) -> None:
        captured_environment.update(kwargs["env"])
        raise subprocess.CalledProcessError(1, "pyinstaller")

    monkeypatch.setattr(build_version.subprocess, "run", fail_build)

    with pytest.raises(subprocess.CalledProcessError):
        build_version.build_version(
            tmp_path,
            CORE_VERSION,
            portable_runtime=False,
            temp_root=selected_temp_root,
        )

    isolated_temp = selected_temp_root / "mediamanager-build-external"
    assert captured_environment["TEMP"] == str(isolated_temp)
    assert captured_environment["TMP"] == str(isolated_temp)
    assert selected_temp_root.is_dir()
    assert not isolated_temp.exists()
    assert (preserved_sibling / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_build_only_preserves_receipt_bound_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"python")
    python.with_name("pyinstaller.exe").write_bytes(b"pyinstaller")
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(
        build_version, "validate_clean_source", lambda *_args: "a" * 40
    )
    monkeypatch.setattr(
        build_version, "portable_release_tools", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "buildonly")
    monkeypatch.setattr(build_version.sys, "executable", str(python))
    paths = version_build_paths(
        tmp_path,
        CORE_VERSION,
        channel="stable",
        release_version="1.0.0",
        attempt_id="buildonly",
    )

    def fake_run(command, **_kwargs):
        if Path(command[0]).name.lower() == "pyinstaller.exe":
            paths.executable_output.mkdir(parents=True, exist_ok=True)
            (paths.executable_output / "MediaManager.exe").write_bytes(b"unsigned")
        else:
            paths.wheel_output.mkdir(parents=True, exist_ok=True)
            (
                paths.wheel_output
                / f"mediamanager-{CORE_VERSION}-py3-none-any.whl"
            ).write_bytes(b"wheel")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_version.subprocess, "run", fake_run)
    monkeypatch.setattr(
        build_version,
        "stage_version",
        lambda *_args, **_kwargs: pytest.fail("build-only must not stage"),
    )

    result = build_version.build_version(
        tmp_path,
        CORE_VERSION,
        portable_runtime=False,
        channel="stable",
        confirm_stable=True,
        stage_output=False,
    )

    assert result == paths.work
    assert paths.work.is_dir()
    receipt = json.loads((paths.work / "build-receipt.json").read_text("utf-8"))
    assert receipt["release_version"] == "1.0.0"
    assert receipt["source_revision"] == "a" * 40


def test_stage_built_stable_requires_valid_authenticode(
    tmp_path: Path, monkeypatch
) -> None:
    work, _, _ = _write_receipt_bound_work(tmp_path)
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(
        build_version, "validate_clean_source", lambda *_args: "a" * 40
    )

    with pytest.raises(PermissionError, match="NotSigned"):
        build_version.stage_built_version(
            tmp_path,
            work,
            channel="stable",
            confirm_stable=True,
            portable_runtime=False,
            authenticode_checker=lambda _path: "NotSigned",
        )


def test_stage_built_stable_uses_1_0_identity_and_exact_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    work, executable, wheel = _write_receipt_bound_work(tmp_path)
    captured: dict[str, object] = {}
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(
        build_version, "validate_clean_source", lambda *_args: "a" * 40
    )
    monkeypatch.setattr(
        build_version, "portable_release_tools", lambda *_args, **_kwargs: {}
    )

    def fake_stage(root: Path, **kwargs) -> Path:
        captured.update({"root": root, **kwargs})
        return tmp_path / "Version" / "Stable" / "1.0"

    monkeypatch.setattr(build_version, "stage_version", fake_stage)

    result = build_version.stage_built_version(
        tmp_path,
        work,
        channel="stable",
        confirm_stable=True,
        portable_runtime=False,
        authenticode_checker=lambda _path: "Valid",
    )

    assert result == tmp_path / "Version" / "Stable" / "1.0"
    assert captured["release_version"] == "1.0.0"
    assert captured["executable"] == executable
    assert captured["wheel"] == wheel
    assert captured["channel"] == "stable"


def test_stage_built_rejects_source_revision_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    work, _, _ = _write_receipt_bound_work(tmp_path, revision="a" * 40)
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(
        build_version, "validate_clean_source", lambda *_args: "b" * 40
    )

    with pytest.raises(ValueError, match="does not match"):
        build_version.stage_built_version(
            tmp_path,
            work,
            channel="stable",
            confirm_stable=True,
            portable_runtime=False,
            authenticode_checker=lambda _path: "Valid",
        )


def test_stage_built_rejects_wheel_changed_after_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    work, _, wheel = _write_receipt_bound_work(tmp_path)
    wheel.write_bytes(b"tampered wheel")
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(
        build_version, "validate_clean_source", lambda *_args: "a" * 40
    )

    with pytest.raises(ValueError, match="does not match the build receipt"):
        build_version.stage_built_version(
            tmp_path,
            work,
            channel="stable",
            confirm_stable=True,
            portable_runtime=False,
            authenticode_checker=lambda _path: "Valid",
        )


def test_external_temp_collision_preserves_existing_directory(
    tmp_path: Path, monkeypatch
) -> None:
    selected_temp_root = tmp_path / "user-local-temp"
    existing_temp = selected_temp_root / "mediamanager-build-existing"
    existing_temp.mkdir(parents=True)
    sentinel = existing_temp / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "existing")

    with pytest.raises(FileExistsError):
        build_version.build_version(
            tmp_path,
            CORE_VERSION,
            portable_runtime=False,
            temp_root=selected_temp_root,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_keep_work_preserves_failed_build_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"python")
    python.with_name("pyinstaller.exe").write_bytes(b"pyinstaller")
    monkeypatch.setattr(build_version, "validate_build_version", lambda *_args: None)
    monkeypatch.setattr(build_version, "validate_clean_source", lambda *_args: "a" * 40)
    monkeypatch.setattr(build_version, "portable_release_tools", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(build_version.secrets, "token_hex", lambda _size: "kept")
    monkeypatch.setattr(build_version.sys, "executable", str(python))
    selected_temp_root = tmp_path / "user-local-temp"

    def fail_build(*_args, **_kwargs) -> None:
        raise subprocess.CalledProcessError(1, "pyinstaller")

    monkeypatch.setattr(build_version.subprocess, "run", fail_build)

    with pytest.raises(subprocess.CalledProcessError):
        build_version.build_version(
            tmp_path,
            CORE_VERSION,
            portable_runtime=False,
            keep_work=True,
            temp_root=selected_temp_root,
        )

    attempt = version_build_paths(
        tmp_path,
        CORE_VERSION,
        channel="development",
        release_version=build_version.release_identity_version("development"),
        attempt_id="kept",
    )
    assert attempt.work.is_dir()
    assert (selected_temp_root / "mediamanager-build-kept").is_dir()


def test_main_forwards_selected_temp_root(tmp_path: Path, monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_build(root: Path, version: str, **kwargs) -> Path:
        captured.update({"root": root, "version": version, **kwargs})
        return tmp_path / "artifact"

    monkeypatch.setattr(build_version, "build_version", fake_build)
    monkeypatch.setattr(
        build_version.sys,
        "argv",
        ["build_version", "--temp-root", str(tmp_path)],
    )

    assert build_version.main() == 0
    assert captured["temp_root"] == tmp_path
    assert captured["stage_output"] is True
    assert "artifact" in capsys.readouterr().out


def test_main_build_only_retains_signing_handoff(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    captured: dict[str, object] = {}

    def fake_build(root: Path, version: str, **kwargs) -> Path:
        captured.update({"root": root, "version": version, **kwargs})
        return tmp_path / "build-only"

    monkeypatch.setattr(build_version, "build_version", fake_build)
    monkeypatch.setattr(
        build_version.sys,
        "argv",
        ["build_version", "--build-only", "--channel", "stable", "--confirm-stable"],
    )

    assert build_version.main() == 0
    assert captured["stage_output"] is False
    assert captured["channel"] == "stable"
    assert "build-only" in capsys.readouterr().out
