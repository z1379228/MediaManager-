from __future__ import annotations

from pathlib import Path

from core import dependency_health as health


def test_version_comparison_handles_semver_and_quickjs_dates() -> None:
    assert health._at_least("deno 2.3.0", (2, 3, 0))
    assert not health._at_least("v21.9.0", (22, 0, 0))
    assert health._at_least("QuickJS version 2024-01-13", (2023, 12, 9))
    assert not health._at_least("unknown", (1, 0))


def test_package_version_uses_ejs_module_fallback_when_metadata_is_absent(
    monkeypatch,
) -> None:
    from yt_dlp_ejs import version

    def missing_metadata(_distribution: str) -> str:
        raise health.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(health.importlib.metadata, "version", missing_metadata)

    assert health._package_version("yt-dlp-ejs") == version


def test_find_executable_prefers_application_tools(
    tmp_path: Path, monkeypatch
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    executable = tools / "helper.exe"
    executable.write_bytes(b"test")
    monkeypatch.setattr(health.os, "name", "nt")
    monkeypatch.setattr(health.shutil, "which", lambda _name: "PATH-version")

    assert health.find_executable(tmp_path, "helper") == str(executable.resolve())


def test_find_executable_accepts_official_windows_megacmd_batch_client(
    tmp_path: Path, monkeypatch
) -> None:
    client = tmp_path / "tools" / "mega-get.bat"
    client.parent.mkdir()
    client.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(health.os, "name", "nt")
    monkeypatch.setattr(health.shutil, "which", lambda _name: None)

    assert health.find_executable(tmp_path, "mega-get") == str(client.resolve())


def test_dependency_report_marks_full_support_ready(
    tmp_path: Path, monkeypatch
) -> None:
    versions = {"yt-dlp": "2026.7.4", "yt-dlp-ejs": "0.8.0"}
    paths = {
        name: str(tmp_path / name)
        for name in ("ffmpeg", "ffprobe", "deno")
    }
    monkeypatch.setattr(health, "_package_version", versions.get)
    monkeypatch.setattr(
        health,
        "find_executable",
        lambda _root, name: paths.get(name),
    )

    def runner(command: tuple[str, ...]) -> tuple[int, str]:
        if command[0].endswith("deno"):
            return 0, "deno 2.3.1"
        return 0, "ffmpeg version 8.1"

    report = health.check_dependencies(tmp_path, runner=runner)

    assert report.youtube_ready
    assert report.ready_count == 4
    assert report.total_count == 7
    assert report.issue_count == 3


def test_dependency_report_rejects_old_or_incomplete_python_components(
    tmp_path: Path, monkeypatch
) -> None:
    versions = {"yt-dlp": "2025.1.1", "yt-dlp-ejs": "0.7.0"}
    monkeypatch.setattr(health, "_package_version", versions.get)
    monkeypatch.setattr(health, "_ejs_solver_ready", lambda: False)
    monkeypatch.setattr(health, "find_executable", lambda _root, _name: None)

    report = health.check_dependencies(tmp_path)
    statuses = {status.dependency_id: status for status in report.statuses}

    assert not statuses["yt-dlp"].available
    assert not statuses["yt-dlp-ejs"].available
    assert "過舊" in statuses["yt-dlp"].detail
    assert "不完整" in statuses["yt-dlp-ejs"].detail


def test_dependency_report_explains_missing_media_and_js(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        health,
        "_package_version",
        lambda name: "2026.7.4" if name == "yt-dlp" else "",
    )
    monkeypatch.setattr(health, "find_executable", lambda _root, _name: None)

    report = health.check_dependencies(tmp_path)

    assert not report.youtube_ready
    assert report.ready_count == 1
    assert report.issue_count == 6
    details = {status.dependency_id: status.detail for status in report.statuses}
    assert "分段" in details["ffmpeg"]
    assert "Deno" in details["javascript-runtime"]
    assert "mega-get" in details["mega-get"]
    assert "whisper-cli" in details["whisper-cli"]


def test_find_javascript_runtime_returns_yt_dlp_key_and_path(
    tmp_path: Path, monkeypatch
) -> None:
    quickjs = tmp_path / "qjs.exe"
    quickjs.write_bytes(b"runtime")
    monkeypatch.setattr(
        health,
        "find_executable",
        lambda _root, name: str(quickjs) if name == "qjs" else None,
    )

    selected = health.find_javascript_runtime(
        tmp_path,
        runner=lambda _command: (0, "QuickJS version 2024-01-13"),
    )

    assert selected == ("quickjs", str(quickjs))


def test_tampered_bundled_deno_is_not_selected(
    tmp_path: Path, monkeypatch
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "deno.exe").write_bytes(b"tampered")
    monkeypatch.setattr(health.shutil, "which", lambda _name: None)

    assert health.find_executable(tmp_path, "deno") is None


def test_tampered_bundled_ffmpeg_is_not_selected(
    tmp_path: Path, monkeypatch
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "ffmpeg.exe").write_bytes(b"tampered")
    monkeypatch.setattr(health.shutil, "which", lambda _name: None)

    assert health.find_executable(tmp_path, "ffmpeg") is None
