from __future__ import annotations

import base64
import hashlib
import json
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.plugins.installer import PluginInstaller
from core.plugins.manager import PluginManager
from core.plugins.package_verifier import signed_payload
from core.plugins.recovery import PluginTransactionRecovery
from core.plugins.registry import PendingAction, PluginRegistry
from core.plugins.updater import PluginUpdater
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureResult
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION


class AcceptingSignatureVerifier:
    def verify(
        self, payload: bytes, signature: bytes, public_key: str
    ) -> SignatureResult:
        assert payload and signature and public_key
        return SignatureResult(True, "accepted for test")


def build_package(path: Path, version: str) -> None:
    source = f"VERSION = '{version}'\n".encode()
    manifest = {
        "schema_version": 1,
        "id": "example.plugin",
        "name": "Example",
        "version": version,
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    manifest_bytes = json.dumps(manifest).encode()
    files_bytes = json.dumps(
        {"files": {"plugin.py": hashlib.sha256(source).hexdigest()}}
    ).encode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.json", manifest_bytes)
        archive.writestr("files.json", files_bytes)
        archive.writestr("plugin.sig", signed_payload(manifest_bytes, files_bytes)[:64])
        archive.writestr("plugin.py", source)


def setup_recovery(tmp_path: Path):
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("trusted.example", base64.b64encode(b"k" * 32).decode("ascii"))
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    verifier = AcceptingSignatureVerifier()
    installer = PluginInstaller(
        tmp_path / "mod", registry, store, signature_verifier=verifier
    )
    manager = PluginManager(
        tmp_path / "mod",
        registry,
        Mock(),
        store,
        signature_verifier=verifier,
    )
    initial = tmp_path / "initial.modpkg"
    build_package(initial, "1.0.0")
    assert installer.install(initial, security_mode=SecurityMode.SAFE_MODE).installed
    old_record = registry.get("example.plugin")
    recovery = PluginTransactionRecovery(tmp_path / "mod", registry, manager)
    return recovery, registry, manager, installer, old_record


def interrupted_replacement(tmp_path: Path, action: PendingAction):
    recovery, registry, manager, installer, old_record = setup_recovery(tmp_path)
    update = tmp_path / "update.modpkg"
    build_package(update, "1.1.0")
    updater = PluginUpdater(tmp_path / "mod", registry, installer, manager)
    assert updater.update(
        update,
        "example.plugin",
        approved_permissions=(),
        security_mode=SecurityMode.SAFE_MODE,
    ).updated
    registry.upsert(replace(old_record, enabled=False, pending_action=action))
    return recovery, registry


@pytest.mark.parametrize("action", [PendingAction.UPDATE, PendingAction.ROLLBACK])
def test_recovery_restores_registered_version_and_preserves_interrupted_one(
    tmp_path: Path, action: PendingAction
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, action)
    report = recovery.recover_all()
    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    interrupted = tmp_path / "mod" / "backups" / "example.plugin" / "1.1.0"
    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert installed.read_text() == "VERSION = '1.0.0'\n"
    assert (interrupted / "plugin.py").is_file()
    record = registry.get("example.plugin")
    assert record.installed_version == "1.0.0"
    assert record.pending_action is PendingAction.NONE
    registry.close()


def test_recovery_clears_journal_when_old_version_never_moved(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.UPDATE)
    )
    report = recovery.recover_all()
    assert report.recovered == ("example.plugin",)
    assert registry.get("example.plugin").pending_action is PendingAction.NONE
    registry.close()


def test_recovery_refuses_tampered_registered_backup(tmp_path: Path) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    (backup / "plugin.py").write_text("tampered", encoding="utf-8")
    report = recovery.recover_all()
    assert report.recovered == ()
    assert any("hash mismatch" in error for error in report.errors)
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE
    registry.close()


def test_recovery_reports_missing_registered_version(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    shutil.rmtree(installed)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.ROLLBACK)
    )
    report = recovery.recover_all()
    assert report.recovered == ()
    assert report.errors == (
        "example.plugin: registered version is absent from installed and backups",
    )
    registry.close()


def test_recovery_can_verify_with_disabled_publisher(tmp_path: Path) -> None:
    recovery, registry, manager, _, old_record = setup_recovery(tmp_path)
    manager.trust_store.set_enabled("trusted.example", False)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.UPDATE)
    )
    report = recovery.recover_all()
    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    registry.close()


def test_recovery_rejects_registry_path_escape(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    registry.upsert(
        replace(
            old_record,
            plugin_id="../../escape",
            enabled=False,
            pending_action=PendingAction.UPDATE,
        )
    )
    report = recovery.recover_all()
    assert report.recovered == ()
    assert report.errors == ("../../escape: transaction paths escape the MOD root",)
    registry.close()


def test_recovery_restores_interrupted_purge(tmp_path: Path) -> None:
    recovery, registry, _, _, record = setup_recovery(tmp_path)
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    removed = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / record.installed_version
    )
    removed.parent.mkdir(parents=True)
    installed.replace(removed)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "0.9.0"
    backup.mkdir(parents=True)
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    removed.replace(staging / "removed")
    (backup.parent).replace(staging / "backups")
    registry.set_pending("example.plugin", PendingAction.PURGE)

    report = recovery.recover_all()

    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert removed.is_dir() and backup.is_dir()
    assert not staging.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()


def test_recovery_finishes_orphaned_committed_purge(tmp_path: Path) -> None:
    recovery, registry, _, _, _ = setup_recovery(tmp_path)
    registry.delete("example.plugin")
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    (staging / "removed").mkdir()

    report = recovery.recover_all()

    assert report.errors == () and report.warnings == ()
    assert not staging.exists()
    registry.close()
