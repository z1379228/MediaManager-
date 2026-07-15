from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from tools.audit_versions import audit_version, audit_versions


def _write_release(root: Path, version: str) -> Path:
    major, minor, _patch = version.split(".")
    release = root / f"{major}.{minor}"
    release.mkdir(parents=True)
    (release / "MediaManager.exe").write_bytes(b"test executable")
    tools = release / "tools"
    tools.mkdir()
    (tools / "deno.exe").write_bytes(b"test deno")
    wheel = release / f"mediamanager-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"mediamanager-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: mediamanager\nVersion: {version}\n",
        )
    (release / "release-info.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "core_version": version,
                "version_folder": f"{major}.{minor}",
                "portable_tools": ["deno.exe"],
            }
        ),
        encoding="utf-8",
    )
    files = sorted(path for path in release.rglob("*") if path.is_file())
    (release / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(release).as_posix()}\n"
            for path in files
        ),
        encoding="ascii",
    )
    return release


def _write_tracked_release(root: Path, version: str, track: str) -> Path:
    release = _write_release(root / track, version)
    info_path = release / "release-info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    info["release_track"] = track
    info_path.write_text(json.dumps(info), encoding="utf-8")
    files = sorted(
        path
        for path in release.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (release / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(release).as_posix()}\n"
            for path in files
        ),
        encoding="ascii",
    )
    return release


def test_audit_versions_accepts_complete_version_history(tmp_path: Path) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "1.0.0")
    _write_release(version_root, "1.2.3")

    report = audit_versions(version_root)

    assert report.valid
    assert tuple(version.folder for version in report.versions) == ("1.0", "1.2")
    assert all(version.checked == 4 for version in report.versions)


def test_daily_audit_keeps_only_current_and_previous(tmp_path: Path) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "1.0.0")
    _write_release(version_root, "1.1.0")
    _write_release(version_root, "2.0.0")

    daily = audit_versions(version_root)
    full = audit_versions(version_root, full_history=True)

    assert tuple(version.folder for version in daily.versions) == ("1.1", "2.0")
    assert tuple(version.folder for version in full.versions) == (
        "1.0",
        "1.1",
        "2.0",
    )


def test_audit_supports_independent_development_and_stable_tracks(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "Version"
    _write_tracked_release(version_root, "5.0.0", "Development")
    _write_tracked_release(version_root, "6.0.0", "Development")
    _write_tracked_release(version_root, "1.0.0", "Stable")

    report = audit_versions(version_root)

    assert report.valid
    assert [(item.track, item.folder) for item in report.versions] == [
        ("Stable", "1.0"),
        ("Development", "5.0"),
        ("Development", "6.0"),
    ]


def test_audit_version_detects_tampering_and_unlisted_files(tmp_path: Path) -> None:
    release = _write_release(tmp_path / "Version", "1.3.2")
    (release / "MediaManager.exe").write_bytes(b"tampered")
    (release / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    result = audit_version(release)

    assert not result.valid
    assert "checksum mismatch: MediaManager.exe" in result.errors
    assert "unlisted file: unexpected.txt" in result.errors


def test_audit_version_detects_metadata_and_unsafe_manifest_paths(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path / "Version", "1.4.1")
    info_path = release / "release-info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    info["core_version"] = "1.5.0"
    info_path.write_text(json.dumps(info), encoding="utf-8")
    with (release / "SHA256SUMS.txt").open("a", encoding="ascii") as manifest:
        manifest.write(f"{'0' * 64}  ../outside.txt\n")

    result = audit_version(release)

    assert not result.valid
    assert "core_version does not match the version folder" in result.errors
    assert "exactly one version-matched wheel is required" in result.errors
    assert "unsafe checksum path: ../outside.txt" in result.errors


def test_audit_versions_reports_interrupted_or_unexpected_entries(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "Version"
    _write_release(version_root, "1.0.0")
    (version_root / ".1.1.staging").mkdir()

    report = audit_versions(version_root)

    assert not report.valid
    assert report.errors == ("unexpected version root entry: .1.1.staging",)


def test_audit_version_allows_only_a_complete_post_stage_signature_pair(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path / "Version", "1.5.0")
    security = release / "security"
    security.mkdir()
    (security / "release-manifest.json").write_text("{}", encoding="utf-8")

    incomplete = audit_version(release)

    assert not incomplete.valid
    assert "release manifest and signature must be present together" in incomplete.errors
    (security / "release-manifest.sig").write_bytes(b"signature")

    assert audit_version(release).valid


def test_audit_version_accepts_schema_two_build_binding(tmp_path: Path) -> None:
    release = _write_release(tmp_path / "Version", "2.0.0")
    info_path = release / "release-info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    info.update(
        {
            "schema_version": 2,
            "tool_schema_version": 2,
            "source_revision": "unavailable",
            "source_fingerprint": "a" * 64,
            "build_id": "b" * 64,
        }
    )
    info_path.write_text(json.dumps(info), encoding="utf-8")
    files = sorted(
        path
        for path in release.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (release / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(release).as_posix()}\n"
            for path in files
        ),
        encoding="ascii",
    )

    assert audit_version(release).valid
