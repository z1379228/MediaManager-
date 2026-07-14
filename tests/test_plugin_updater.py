from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import Mock

from core.plugins.installer import PluginInstaller
from core.plugins.manager import PluginOperationResult
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PluginRegistry
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


def build_package(
    path: Path, version: str, *, publisher: str = "trusted.example"
) -> None:
    source = f"VERSION = '{version}'\n".encode()
    manifest = {
        "schema_version": 1,
        "id": "example.plugin",
        "name": "Example",
        "version": version,
        "publisher": publisher,
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


def setup_update(tmp_path: Path):
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("trusted.example", base64.b64encode(b"k" * 32).decode("ascii"))
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    verifier = AcceptingSignatureVerifier()
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        store,
        signature_verifier=verifier,
    )
    initial = tmp_path / "initial.modpkg"
    build_package(initial, "1.0.0")
    assert installer.install(
        initial,
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    plugin_manager = Mock()
    plugin_manager.set_enabled.return_value = PluginOperationResult(True)
    updater = PluginUpdater(tmp_path / "mod", registry, installer, plugin_manager)
    return updater, registry, plugin_manager, installer


def test_update_replaces_plugin_and_retains_backup(tmp_path: Path) -> None:
    updater, registry, plugin_manager, _ = setup_update(tmp_path)
    package = tmp_path / "update.modpkg"
    build_package(package, "1.1.0")
    result = updater.update(
        package,
        "example.plugin",
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    )
    record = registry.get("example.plugin")
    assert result.updated
    assert result.previous_version == "1.0.0"
    assert record.installed_version == "1.1.0"
    assert not record.enabled
    assert (
        tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    ).read_text() == "VERSION = '1.1.0'\n"
    assert (
        tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0" / "plugin.py"
    ).is_file()
    plugin_manager.set_enabled.assert_called_once_with(
        "example.plugin", False, SecurityMode.SAFE_MODE
    )
    registry.close()


def test_update_rejects_same_or_older_version(tmp_path: Path) -> None:
    updater, registry, plugin_manager, _ = setup_update(tmp_path)
    package = tmp_path / "same.modpkg"
    build_package(package, "1.0.0")
    result = updater.update(
        package,
        "example.plugin",
        approved_permissions=(),
        security_mode=SecurityMode.SAFE_MODE,
    )
    assert not result.updated
    assert result.errors == ("update version must be newer than installed version",)
    plugin_manager.set_enabled.assert_not_called()
    registry.close()


def test_update_rejects_different_publisher(tmp_path: Path) -> None:
    updater, registry, plugin_manager, installer = setup_update(tmp_path)
    installer.trust_store.add(
        "other.example", base64.b64encode(b"o" * 32).decode("ascii")
    )
    package = tmp_path / "other.modpkg"
    build_package(package, "1.1.0", publisher="other.example")
    result = updater.update(
        package,
        "example.plugin",
        approved_permissions=(),
        security_mode=SecurityMode.SAFE_MODE,
    )
    assert not result.updated
    assert result.errors == ("update package publisher does not match",)
    plugin_manager.set_enabled.assert_not_called()
    registry.close()


def test_registry_failure_restores_old_version(tmp_path: Path) -> None:
    updater, registry, plugin_manager, installer = setup_update(tmp_path)

    class FailingRegistry:
        def get(self, plugin_id):
            return registry.get(plugin_id)

        def set_enabled(self, plugin_id, enabled):
            registry.set_enabled(plugin_id, enabled)

        def set_pending(self, plugin_id, action):
            registry.set_pending(plugin_id, action)

        def upsert(self, record):
            raise sqlite3.OperationalError("simulated registry failure")

    updater = PluginUpdater(
        tmp_path / "mod", FailingRegistry(), installer, plugin_manager
    )
    package = tmp_path / "update.modpkg"
    build_package(package, "1.1.0")
    result = updater.update(
        package,
        "example.plugin",
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    )
    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    assert not result.updated
    assert installed.read_text() == "VERSION = '1.0.0'\n"
    assert not (tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0").exists()
    registry.close()
