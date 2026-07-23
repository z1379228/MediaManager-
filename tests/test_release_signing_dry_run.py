from __future__ import annotations

import pytest

from tools.release_signing_dry_run import run_dry_run


def test_disposable_release_signing_dry_run_detects_tampering(tmp_path) -> None:
    (tmp_path / "MediaManager.exe").write_bytes(b"development artifact")
    result = run_dry_run(tmp_path, files=("MediaManager.exe",))
    assert result == {
        "status": "PASS",
        "checked_files": 1,
        "tamper_detected": True,
        "key_persisted": False,
    }
    assert not (tmp_path / "security").exists()


def test_disposable_release_signing_dry_run_accepts_explicit_temp_root(
    tmp_path,
) -> None:
    (tmp_path / "MediaManager.exe").write_bytes(b"development artifact")
    temp_root = tmp_path / "user-temp"
    temp_root.mkdir()

    result = run_dry_run(
        tmp_path,
        files=("MediaManager.exe",),
        temp_root=temp_root,
    )

    assert result["status"] == "PASS"
    assert tuple(temp_root.iterdir()) == ()


def test_disposable_release_signing_dry_run_rejects_missing_files(
    tmp_path,
) -> None:
    with pytest.raises(ValueError, match="missing or unsafe"):
        run_dry_run(tmp_path, files=("missing.exe",))
