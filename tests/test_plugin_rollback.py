from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import Mock

from core.plugins.installer import PluginInstaller
from core.plugins.manager import PluginManager
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PendingAction, PluginRegistry
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
    rollback, registry, _ = setup_rollback(tmp_path)
    assert rollback.list_versions("example.plugin") == ("1.0.0",)
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
    registry.close()


def test_rollback_rejects_tampered_backup(tmp_path: Path) -> None:
    rollback, registry, manager = setup_rollback(tmp_path)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    (backup / "plugin.py").write_text("tampered", encoding="utf-8")
    result = rollback.rollback("example.plugin", "1.0.0", SecurityMode.SAFE_MODE)
    assert not result.rolled_back
    assert result.errors == ("installed file hash mismatch: plugin.py",)
    manager.supervisor.stop.assert_not_called()
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
