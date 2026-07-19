from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

import core.plugins.lifecycle as lifecycle_module
import core.plugins.rollback as rollback_module
from core.plugins.dependency_graph import MAX_MANIFEST_BYTES
from core.plugins.installer import PluginInstaller
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.manager import PluginManager
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.rollback import PluginRollbackManager
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
        "permissions": ["media.read"],
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


def write_installed_dependency(
    mod_root: Path,
    registry: PluginRegistry,
) -> PluginRecord:
    manifest = {
        "schema_version": 1,
        "id": "dependent.plugin",
        "name": "Dependent",
        "version": "1.0.0",
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": ["example.plugin"],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    manifest_bytes = json.dumps(manifest).encode()
    plugin_root = mod_root / "installed" / "dependent.plugin"
    plugin_root.mkdir(parents=True)
    (plugin_root / "plugin.json").write_bytes(manifest_bytes)
    record = PluginRecord(
        "dependent.plugin",
        "1.0.0",
        False,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "trusted.example",
        (),
        hashlib.sha256(manifest_bytes).hexdigest(),
    )
    registry.upsert(record)
    return record


def setup_rollback(tmp_path: Path):
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("trusted.example", base64.b64encode(b"k" * 32).decode("ascii"))
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    verifier = AcceptingSignatureVerifier()
    installer = PluginInstaller(
        tmp_path / "mod", registry, store, signature_verifier=verifier
    )
    supervisor = Mock()
    manager = PluginManager(
        tmp_path / "mod",
        registry,
        supervisor,
        store,
        signature_verifier=verifier,
    )
    initial = tmp_path / "initial.modpkg"
    update = tmp_path / "update.modpkg"
    build_package(initial, "1.0.0")
    build_package(update, "1.1.0")
    assert installer.install(
        initial,
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    updater = PluginUpdater(tmp_path / "mod", registry, installer, manager)
    assert updater.update(
        update,
        "example.plugin",
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    ).updated
    supervisor.reset_mock()
    rollback = PluginRollbackManager(tmp_path / "mod", registry, manager)
    return rollback, registry, manager


def test_rollback_swaps_versions_and_keeps_forward_backup(tmp_path: Path) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    assert rollback.list_versions("example.plugin") == ("1.0.0",)
    load = manager.trust_store.load
    manager.trust_store.load = Mock(wraps=load)
    result = rollback.rollback("example.plugin", "1.0.0", SecurityMode.SAFE_MODE)
    record = registry.get("example.plugin")
    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    forward = tmp_path / "mod" / "backups" / "example.plugin" / "1.1.0"
    assert result.rolled_back
    assert record.installed_version == "1.0.0"
    assert not record.enabled
    assert installed.read_text() == "VERSION = '1.0.0'\n"
    assert (forward / "plugin.py").is_file()
    assert rollback.list_versions("example.plugin") == ("1.1.0",)
    assert manager.trust_store.load.call_count == 2
    registry.close()


def test_rollback_rejects_tampered_backup(tmp_path: Path) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    (backup / "plugin.py").write_text("tampered", encoding="utf-8")
    result = rollback.rollback("example.plugin", "1.0.0", SecurityMode.SAFE_MODE)
    assert not result.rolled_back
    assert result.errors == ("installed file hash mismatch: plugin.py",)
    manager._supervisor.stop.assert_not_called()
    assert registry.get("example.plugin").installed_version == "1.1.0"
    registry.close()


def test_blocked_mode_rejects_rollback(tmp_path: Path) -> None:
    rollback, registry, _ = setup_rollback(tmp_path)
    result = rollback.rollback("example.plugin", "1.0.0", SecurityMode.BLOCKED)
    assert not result.rolled_back
    assert result.errors == ("plugins cannot be rolled back in BLOCKED security mode",)
    registry.close()


def test_registry_failure_restores_current_and_backup(tmp_path: Path) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)

    class FailingOnceRegistry:
        def __init__(self):
            self.failed = False

        def get(self, plugin_id):
            return registry.get(plugin_id)

        def list_dependency_records(self, *, limit):
            return registry.list_dependency_records(limit=limit)

        def set_enabled(self, plugin_id, enabled):
            registry.set_enabled(plugin_id, enabled)

        def set_pending(self, plugin_id, action):
            registry.set_pending(plugin_id, action)

        def upsert(self, record):
            if not self.failed:
                self.failed = True
                raise sqlite3.OperationalError("simulated registry failure")
            registry.upsert(record)

    rollback = PluginRollbackManager(tmp_path / "mod", FailingOnceRegistry(), manager)
    result = rollback.rollback("example.plugin", "1.0.0", SecurityMode.SAFE_MODE)
    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    assert not result.rolled_back
    assert installed.read_text() == "VERSION = '1.1.0'\n"
    assert (backup / "plugin.py").is_file()
    record = registry.get("example.plugin")
    assert record.installed_version == "1.1.0"
    assert record.pending_action is PendingAction.NONE
    registry.close()


def test_rollback_holds_lifecycle_lock_through_file_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_replace = rollback_module.os.replace
    checked = False

    def guarded_replace(source: Path, destination: Path) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(rollback_module.os, "replace", guarded_replace)

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    assert result.rolled_back
    assert checked
    assert rollback.lifecycle_lock is manager.lifecycle_lock
    registry.close()


def test_rollback_rejects_invalid_candidate_graph_before_disable_or_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    mod_root = tmp_path / "mod"
    dependent_before = write_installed_dependency(mod_root, registry)
    backup_manifest = (
        mod_root
        / "backups"
        / "example.plugin"
        / "1.0.0"
        / "plugin.json"
    )
    candidate = json.loads(backup_manifest.read_text(encoding="utf-8"))
    candidate["dependencies"] = ["dependent.plugin"]
    backup_manifest.write_text(json.dumps(candidate), encoding="utf-8")
    registry.set_enabled("example.plugin", True)
    example_before = registry.get("example.plugin")
    manager._supervisor.reset_mock()
    replace_spy = Mock(wraps=rollback_module.os.replace)
    monkeypatch.setattr(rollback_module.os, "replace", replace_spy)

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    assert not result.rolled_back
    assert any("dependency" in error for error in result.errors)
    manager._supervisor.stop.assert_not_called()
    replace_spy.assert_not_called()
    assert registry.get("example.plugin") == example_before
    assert registry.get("dependent.plugin") == dependent_before
    assert (
        mod_root / "installed" / "example.plugin" / "plugin.py"
    ).read_text() == "VERSION = '1.1.0'\n"
    assert backup_manifest.is_file()
    registry.close()


def test_rollback_reverts_swap_when_post_move_verification_fails(
    tmp_path: Path,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    manager.verify_directory = Mock(
        side_effect=[(), ("installed plugin manifest was modified",)]
    )

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    record = registry.get("example.plugin")
    assert not result.rolled_back
    assert result.errors == ("installed plugin manifest was modified",)
    assert installed.read_text(encoding="utf-8") == "VERSION = '1.1.0'\n"
    assert (backup / "plugin.py").is_file()
    assert record.installed_version == "1.1.0"
    assert record.pending_action is PendingAction.NONE
    assert manager.verify_directory.call_count == 2
    assert all(
        call.kwargs["refresh_trust_store"]
        for call in manager.verify_directory.call_args_list
    )
    registry.close()


def test_rollback_rejects_oversized_manifest_before_disable_or_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    mod_root = tmp_path / "mod"
    backup_manifest = (
        mod_root
        / "backups"
        / "example.plugin"
        / "1.0.0"
        / "plugin.json"
    )
    backup_manifest.write_bytes(b"x" * (MAX_MANIFEST_BYTES + 1))
    before = registry.get("example.plugin")
    replace_spy = Mock(wraps=rollback_module.os.replace)
    monkeypatch.setattr(rollback_module.os, "replace", replace_spy)

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    assert not result.rolled_back
    assert result.errors == (
        "backup manifest is invalid: plugin manifest exceeds the size limit",
    )
    manager._supervisor.stop.assert_not_called()
    replace_spy.assert_not_called()
    assert registry.get("example.plugin") == before
    assert (
        mod_root / "installed" / "example.plugin" / "plugin.py"
    ).read_text(encoding="utf-8") == "VERSION = '1.1.0'\n"
    registry.close()


def test_rollback_rejects_dependency_overflow_before_per_dependency_queries(
    tmp_path: Path,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    backup_manifest = (
        tmp_path
        / "mod"
        / "backups"
        / "example.plugin"
        / "1.0.0"
        / "plugin.json"
    )
    candidate = json.loads(backup_manifest.read_text(encoding="utf-8"))
    candidate["dependencies"] = [f"dependency-{index}.plugin" for index in range(65)]
    backup_manifest.write_text(json.dumps(candidate), encoding="utf-8")
    registry_get = registry.get
    registry.get = Mock(wraps=registry_get)

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    assert not result.rolled_back
    assert any("too many dependencies" in error for error in result.errors)
    assert registry.get.call_count == 1
    manager._supervisor.stop.assert_not_called()
    registry.close()


def test_rollback_rejects_reparse_backup_root_before_file_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    original = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path.name == "backups" or original(path),
    )

    result = rollback.rollback(
        "example.plugin",
        "1.0.0",
        SecurityMode.SAFE_MODE,
    )

    assert not result.rolled_back
    assert result.errors == ("plugin lifecycle path is unsafe",)
    manager._supervisor.stop.assert_not_called()
    assert registry.get("example.plugin").installed_version == "1.1.0"
    registry.close()
