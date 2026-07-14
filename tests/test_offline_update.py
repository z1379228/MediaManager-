from __future__ import annotations

import base64
import zipfile
from pathlib import Path

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
