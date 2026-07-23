from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
CLEANUP_SCRIPT = ROOT / "暫存檔清除.bat"


def test_cleanup_script_preserves_portable_user_data() -> None:
    text = CLEANUP_SCRIPT.read_text(encoding="utf-8")

    assert 'call :clean_dist "%ROOT%dist"' in text
    assert 'call :remove_dir "%ROOT%dist" "dist"' not in text
    assert 'if /I "%%~nxD"=="UserData"' in text
    assert 'if exist "%~1\\UserData" exit /b 0' in text


def test_cleanup_script_preserves_work_handoffs_and_evidence() -> None:
    text = CLEANUP_SCRIPT.read_text(encoding="utf-8")

    assert 'call :remove_dir "%ROOT%.work" ".work"' not in text
    assert "echo [KEEP] %ROOT%.work" in text
