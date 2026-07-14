from __future__ import annotations

from pathlib import Path

from core.security.release_layout import SOURCE_RELEASE_FILES


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = "安裝必備軟體.bat"


def test_windows_dependency_installer_is_safe_and_part_of_release() -> None:
    text = (ROOT / INSTALLER).read_text(encoding="utf-8")
    assert INSTALLER in SOURCE_RELEASE_FILES
    for package_id in ("Gyan.FFmpeg", "DenoLand.Deno"):
        assert package_id in text
    assert "set /p" not in text
    assert "--exact --source winget" in text
    assert "call :install_if_missing" in text
    assert "call :install_media_if_missing" in text
    assert "where ffprobe" in text
    assert 'if "%NEED_WINGET%"=="0" goto complete' in text
    for development_package in ("Git.Git", "GitHub.cli", "Python.Python"):
        assert development_package not in text
    lowered = text.casefold()
    for unsafe in (
        "curl ",
        "invoke-webrequest",
        "executionpolicy bypass",
        "powershell -",
        "http://",
        "https://",
        "--silent",
    ):
        assert unsafe not in lowered


def test_windows_dependency_installer_explains_portable_and_optional_limits() -> None:
    text = (ROOT / INSTALLER).read_text(encoding="utf-8")
    assert "Bundled Portable tools" in text
    assert "whisper-cli plus a local model" in text
    assert "not required to start MediaManager" in text
    assert 'Update "App Installer" in Microsoft Store' in text
