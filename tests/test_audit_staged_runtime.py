from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tools import audit_staged_runtime
from tools.audit_staged_runtime import audit_staged_runtime as run_audit


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_runtime_fixture(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, bytes]]:
    source_root = root / "source"
    staged_root = root / "staged"
    source_license = source_root / "third_party/deno/LICENSE.md"
    source_license.parent.mkdir(parents=True)
    source_license.write_bytes(b"canonical deno license")
    files = {
        "deno.exe": b"deno runtime",
        "DENO-LICENSE.md": source_license.read_bytes(),
        "ffmpeg.exe": b"ffmpeg runtime",
        "ffprobe.exe": b"ffprobe runtime",
        "FFMPEG-LICENSE.txt": b"ffmpeg license",
        "FFMPEG-README.txt": b"ffmpeg readme",
    }
    tools_root = staged_root / "tools"
    tools_root.mkdir(parents=True)
    for name, content in files.items():
        (tools_root / name).write_bytes(content)
    (staged_root / "release-info.json").write_text(
        json.dumps({"portable_tools": sorted(files)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        audit_staged_runtime,
        "DENO_EXECUTABLE_SHA256",
        _sha256(files["deno.exe"]),
    )
    monkeypatch.setattr(
        audit_staged_runtime,
        "FFMPEG_PORTABLE_SHA256",
        {
            name: _sha256(files[name])
            for name in (
                "ffmpeg.exe",
                "ffprobe.exe",
                "FFMPEG-LICENSE.txt",
                "FFMPEG-README.txt",
            )
        },
    )
    return source_root, staged_root, files


def test_staged_runtime_policy_accepts_complete_offline_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )

    report = run_audit(staged_root, source_root=source_root)

    assert report.valid, report.errors
    assert report.checked == 6
    assert report.deno_license_source == "third_party/deno/LICENSE.md"
    assert report.deno_license_sha256 == _sha256(b"canonical deno license")


def test_staged_runtime_policy_rejects_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "tools/ffprobe.exe").unlink()

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.checked == 5
    assert report.errors == (
        "staged runtime file is missing or unsafe: tools/ffprobe.exe",
    )


@pytest.mark.parametrize(
    "name",
    [
        "deno.exe",
        "ffmpeg.exe",
        "ffprobe.exe",
        "FFMPEG-LICENSE.txt",
        "FFMPEG-README.txt",
    ],
)
def test_staged_runtime_policy_rejects_tampered_pinned_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "tools" / name).write_bytes(b"tampered")

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        f"staged runtime hash mismatch: tools/{name}",
    )


def test_staged_runtime_policy_rejects_license_not_from_canonical_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "tools/DENO-LICENSE.md").write_bytes(b"other license")

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "staged Deno license does not match canonical source",
    )


def test_staged_runtime_policy_rejects_symlinked_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    target = staged_root / "tools/ffmpeg.exe"
    external = tmp_path / "external-ffmpeg.exe"
    external.write_bytes(target.read_bytes())
    target.unlink()
    try:
        os.symlink(external, target)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert (
        "staged runtime file is missing or unsafe: tools/ffmpeg.exe"
        in report.errors
    )


def test_staged_runtime_policy_rejects_unexpected_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "tools/other.exe").write_bytes(b"unexpected")

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "unexpected staged runtime entry: tools/other.exe",
    )


def test_staged_runtime_policy_does_not_traverse_unsafe_tools_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    original = audit_staged_runtime._is_unsafe_link
    unsafe_tools = staged_root / "tools"
    monkeypatch.setattr(
        audit_staged_runtime,
        "_is_unsafe_link",
        lambda path: path == unsafe_tools or original(path),
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.checked == 0
    assert report.errors == (
        "staged tools directory is missing or unsafe",
    )


def test_staged_runtime_policy_rejects_unsafe_license_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    original = audit_staged_runtime._is_unsafe_link
    unsafe_ancestor = source_root / "third_party"
    monkeypatch.setattr(
        audit_staged_runtime,
        "_is_unsafe_link",
        lambda path: path == unsafe_ancestor or original(path),
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "canonical Deno license source is missing or unsafe",
    )


@pytest.mark.parametrize(
    "portable_tools",
    [
        [
            "DENO-LICENSE.md",
            "FFMPEG-LICENSE.txt",
            "FFMPEG-README.txt",
            "deno.exe",
            "ffmpeg.exe",
        ],
        [
            "DENO-LICENSE.md",
            "FFMPEG-LICENSE.txt",
            "FFMPEG-README.txt",
            "deno.exe",
            "ffmpeg.exe",
            "ffprobe.exe",
            "ffprobe.exe",
        ],
        [
            "DENO-LICENSE.md",
            "FFMPEG-LICENSE.txt",
            "FFMPEG-README.txt",
            "deno.exe",
            "ffmpeg.exe",
            "ffprobe.exe",
            "other.exe",
        ],
    ],
)
def test_staged_runtime_policy_rejects_metadata_divergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    portable_tools: list[str],
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "release-info.json").write_text(
        json.dumps({"portable_tools": portable_tools}),
        encoding="utf-8",
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "release-info.json portable_tools does not match runtime policy",
    )


def test_staged_runtime_policy_rejects_oversized_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "release-info.json").write_bytes(b" " * (64 * 1024 + 1))

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "release-info.json cannot provide portable_tools",
    )


def test_staged_runtime_policy_rejects_duplicate_metadata_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    expected = json.dumps(sorted(files))
    (staged_root / "release-info.json").write_text(
        '{"portable_tools": [], "portable_tools": ' + expected + "}",
        encoding="utf-8",
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "release-info.json cannot provide portable_tools",
    )


def test_staged_runtime_policy_reports_deep_metadata_as_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    (staged_root / "release-info.json").write_text(
        "[" * 2000 + "]" * 2000,
        encoding="utf-8",
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert report.errors == (
        "release-info.json cannot provide portable_tools",
    )


def test_staged_runtime_policy_rejects_release_layout_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root, staged_root, _files = _write_runtime_fixture(
        tmp_path,
        monkeypatch,
    )
    monkeypatch.setattr(
        audit_staged_runtime,
        "PORTABLE_RUNTIME_FILES",
        audit_staged_runtime.PORTABLE_RUNTIME_FILES[:-1],
    )

    report = run_audit(staged_root, source_root=source_root)

    assert not report.valid
    assert "portable runtime release layout does not match policy" in report.errors


def test_staged_runtime_policy_cli_fails_closed_for_missing_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = audit_staged_runtime.main(
        ["--root", str(tmp_path / "missing"), "--source-root", str(tmp_path)]
    )

    assert result == 1
    assert '"valid": false' in capsys.readouterr().out
