from __future__ import annotations

import base64
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.updates.offline_bundle import (
    OfflineUpdateInstaller,
    create_offline_bundle,
)


def public_key(private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")


def build_bundle(tmp_path: Path, *, minimum: str = "1.9.0"):
    release = tmp_path / "source" / "2.0"
    release.mkdir(parents=True)
    (release / "MediaManager.exe").write_bytes(b"version 2")
    (release / "release-info.json").write_text("{}", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    package = tmp_path / "MediaManager-2.0.mmupdate"
    create_offline_bundle(
        release,
        package,
        private_key,
        key_id="release-test",
        minimum_source_version=minimum,
        maximum_source_version="1.9.9",
        target_version="2.0.0",
    )
    return package, private_key


def build_testing_bundle(
    tmp_path: Path,
    *,
    target_version: str,
    folder: str,
    minimum: str,
    maximum: str,
):
    release = tmp_path / "source" / "Testing" / folder
    release.mkdir(parents=True)
    (release / "MediaManager.exe").write_bytes(
        f"testing {target_version}".encode("ascii")
    )
    (release / "release-info.json").write_text("{}", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    package = tmp_path / f"MediaManager-Testing-{target_version}.mmupdate"
    create_offline_bundle(
        release,
        package,
        private_key,
        key_id="release-test",
        minimum_source_version=minimum,
        maximum_source_version=maximum,
        target_version=target_version,
    )
    return package, private_key


def test_signed_offline_update_installs_side_by_side(tmp_path: Path) -> None:
    package, private_key = build_bundle(tmp_path)
    version_root = tmp_path / "installed" / "Version"
    old = version_root / "1.9"
    old.mkdir(parents=True)
    (old / "MediaManager.exe").write_bytes(b"version 1")
    installer = OfflineUpdateInstaller(
        version_root,
        public_key=public_key(private_key),
        key_id="release-test",
    )
    verified = installer.verify(package, current_version="1.9.0")
    assert verified.valid
    target = installer.install(verified)
    assert target == version_root / "2.0"
    assert (target / "MediaManager.exe").read_bytes() == b"version 2"
    assert (old / "MediaManager.exe").read_bytes() == b"version 1"
    assert not (version_root / ".2.0.staging").exists()
    assert not (version_root / ".2.0.backup").exists()


def test_testing_baseline_keeps_two_segment_version_folder(tmp_path: Path) -> None:
    package, private_key = build_testing_bundle(
        tmp_path,
        target_version="1.2.0",
        folder="1.2",
        minimum="1.1.0",
        maximum="1.1.9",
    )
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("update.json"))
    assert manifest["target_version"] == "1.2.0"
    assert manifest["version_folder"] == "1.2"

    version_root = tmp_path / "installed" / "Version" / "Testing"
    installer = OfflineUpdateInstaller(
        version_root,
        public_key=public_key(private_key),
        key_id="release-test",
    )
    verified = installer.verify(package, current_version="1.1.0")
    assert verified.valid
    assert verified.manifest is not None
    assert verified.manifest.version_folder == "1.2"
    assert installer.install(verified) == version_root / "1.2"


def test_testing_patch_installs_beside_immutable_baseline(tmp_path: Path) -> None:
    package, private_key = build_testing_bundle(
        tmp_path,
        target_version="1.2.1",
        folder="1.2.1",
        minimum="1.2.0",
        maximum="1.2.0",
    )
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("update.json"))
    assert manifest["target_version"] == "1.2.1"
    assert manifest["version_folder"] == "1.2.1"

    wrong_track = OfflineUpdateInstaller(
        tmp_path / "installed-other" / "Version",
        public_key=public_key(private_key),
        key_id="release-test",
    )
    rejected = wrong_track.verify(package, current_version="1.2.0")
    assert not rejected.valid
    assert rejected.errors == ("offline update version range is invalid",)

    version_root = tmp_path / "installed" / "Version" / "Testing"
    baseline = version_root / "1.2"
    baseline.mkdir(parents=True)
    baseline_executable = baseline / "MediaManager.exe"
    baseline_executable.write_bytes(b"testing 1.2.0 baseline")
    installer = OfflineUpdateInstaller(
        version_root,
        public_key=public_key(private_key),
        key_id="release-test",
    )
    verified = installer.verify(package, current_version="1.2.0")
    assert verified.valid
    assert verified.manifest is not None
    assert verified.manifest.version_folder == "1.2.1"

    target = installer.install(verified)
    assert target == version_root / "1.2.1"
    assert (target / "MediaManager.exe").read_bytes() == b"testing 1.2.1"
    assert baseline_executable.read_bytes() == b"testing 1.2.0 baseline"
    assert not (version_root / ".1.2.1.staging").exists()
    assert not (version_root / ".1.2.1.backup").exists()


def test_non_testing_patch_keeps_two_segment_version_folder(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    for track in ("Development", "Stable", "source"):
        release = tmp_path / track / "2.0"
        release.mkdir(parents=True)
        (release / "MediaManager.exe").write_bytes(track.encode("ascii"))
        package = tmp_path / f"{track}.mmupdate"
        create_offline_bundle(
            release,
            package,
            private_key,
            key_id="release-test",
            minimum_source_version="1.9.0",
            maximum_source_version="1.9.9",
            target_version="2.0.1",
        )
        with zipfile.ZipFile(package) as archive:
            manifest = json.loads(archive.read("update.json"))
        assert manifest["version_folder"] == "2.0"


def test_offline_update_panel_explains_channel_aware_version_folders() -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLabel

    from trusted_ui.offline_update_panel import create_offline_update_panel

    app = QApplication.instance() or QApplication([])
    context = SimpleNamespace(
        offline_updates=SimpleNamespace(
            public_key="test-public-key",
            key_id="test-key-id",
        )
    )
    panel = create_offline_update_panel(context)
    intro = panel.findChild(QLabel, "sectionSubtitle")

    assert intro is not None
    assert "Version/Testing/<major>.<minor>.<patch>" in intro.text()
    assert "Version/<track>/<major>.<minor>" in intro.text()
    assert "目前版本不會被直接覆寫" in intro.text()
    panel.close()
    app.processEvents()


def test_offline_update_rejects_wrong_source_range(tmp_path: Path) -> None:
    package, private_key = build_bundle(tmp_path, minimum="1.9.1")
    installer = OfflineUpdateInstaller(
        tmp_path / "Version",
        public_key=public_key(private_key),
        key_id="release-test",
    )
    result = installer.verify(package, current_version="1.9.0")
    assert result.errors == ("offline update version range is invalid",)


def test_offline_update_rejects_tampered_signature(tmp_path: Path) -> None:
    package, private_key = build_bundle(tmp_path)
    replacement = package.with_suffix(".tampered")
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(
        replacement, "w"
    ) as target:
        for info in source.infolist():
            content = b"x" * 64 if info.filename == "update.sig" else source.read(info)
            target.writestr(info, content)
    replacement.replace(package)
    installer = OfflineUpdateInstaller(
        tmp_path / "Version",
        public_key=public_key(private_key),
        key_id="release-test",
    )
    result = installer.verify(package, current_version="1.9.0")
    assert not result.valid
    assert any("unsafe" in error or "signature" in error for error in result.errors)


def test_offline_update_rejects_unverified_install(tmp_path: Path) -> None:
    installer = OfflineUpdateInstaller(
        tmp_path / "Version",
        public_key="invalid",
        key_id="release-test",
    )
    from core.updates.offline_bundle import OfflineUpdateVerification

    try:
        installer.install(OfflineUpdateVerification(False))
    except ValueError as error:
        assert "passed verification" in str(error)
    else:
        raise AssertionError("unverified update was installed")
