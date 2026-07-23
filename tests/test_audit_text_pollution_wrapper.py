from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
WRAPPER = ROOT / "tools" / "audit_text_pollution.ps1"


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh")
    if executable is None:
        pytest.skip("PowerShell is unavailable")
    return executable


def test_wrapper_uses_trusted_audit_and_propagates_exit_code(
    tmp_path: Path,
) -> None:
    untrusted_root = tmp_path / "untrusted"
    untrusted_tools = untrusted_root / "tools"
    untrusted_tools.mkdir(parents=True)
    marker = "UNTRUSTED_AUDIT_EXECUTED"
    (untrusted_tools / "quality_audit.py").write_text(
        f"print({marker!r})\nraise SystemExit(0)\n",
        encoding="utf-8",
    )
    (untrusted_root / "sitecustomize.py").write_text(
        f"print({marker!r})\nraise SystemExit(0)\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        (
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WRAPPER),
            "-Root",
            str(untrusted_root),
        ),
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert marker not in output
    assert "QUALITY_SCOPE=FAIL" in output
