from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

import core.plugins.installer as installer_module
from core.plugins.installer import PluginInstaller
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureResult
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION


class AcceptingSignatureVerifier:
    def verify(
        self, payload: bytes, signature: bytes, public_key: str
    ) -> SignatureResult:
        assert payload
        assert signature == b"test-signature"
        assert public_key == base64.b64encode(b"k" * 32).decode("ascii")
        return SignatureResult(True, "accepted for test")


def build_package(
    path: Path,
    *,
    publisher: str = "trusted.example",
    minimum_core_version: str = "0.1.0",
    maximum_core_version: str = CORE_VERSION,
    dependencies: list[str] | None = None,
) -> None:
    plugin_source = b"def handle_request(request):\n    return request\n"
    manifest = {
        "schema_version": 1,
        "id": "example.plugin",
        "name": "Example",
        "version": "1.0.0",
        "publisher": publisher,
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": minimum_core_version,
        "maximum_core_version": maximum_core_version,
        "permissions": ["media.read"],
        "external_tools": [],
        "dependencies": dependencies or [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    files = {"files": {"plugin.py": hashlib.sha256(plugin_source).hexdigest()}}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr("files.json", json.dumps(files))
        archive.writestr("plugin.sig", b"test-signature")
        archive.writestr("plugin.py", plugin_source)


def trust_store(path: Path) -> TrustStore:
    path.write_text(
        json.dumps(
            {
                "publishers": [
                    {
                        "publisher_id": "trusted.example",
                        "public_key": base64.b64encode(b"k" * 32).decode("ascii"),
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    store = TrustStore(path)
    store.load()
    return store


def write_installed_plugin(
    mod_root: Path,
    registry: PluginRegistry,
    plugin_id: str,
    *,
    dependencies: list[str],
) -> PluginRecord:
    manifest = {
        "schema_version": 1,
        "id": plugin_id,
        "name": "Installed dependency",
        "version": "1.0.0",
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": dependencies,
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    manifest_bytes = json.dumps(manifest).encode()
    plugin_root = mod_root / "installed" / plugin_id
    plugin_root.mkdir(parents=True)
    (plugin_root / "plugin.json").write_bytes(manifest_bytes)
    record = PluginRecord(
        plugin_id,
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


def test_installs_verified_package_disabled(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(
        package,
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    )
    record = registry.get("example.plugin")
    assert result.installed
    assert (tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py").is_file()
    assert record is not None
    assert not record.enabled
    assert record.approved_permissions == ("media.read",)
    registry.close()


def test_rejects_untrusted_publisher_without_extracting(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package, publisher="unknown.example")
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == ("publisher is not trusted",)
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_default_signature_verifier_fails_closed(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors[0].startswith("signature rejected:")
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_blocked_mode_rejects_before_reading_package(tmp_path: Path) -> None:
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(
        tmp_path / "missing.modpkg",
        security_mode=SecurityMode.BLOCKED,
    )
    assert not result.installed
    assert result.errors == ("plugins cannot be installed in BLOCKED security mode",)
    registry.close()


def test_rejects_incompatible_core_version(tmp_path: Path) -> None:
    package = tmp_path / "future.modpkg"
    build_package(
        package,
        minimum_core_version="17.0.0",
        maximum_core_version="17.9.9",
    )
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == (f"plugin is incompatible with core {CORE_VERSION}",)
    registry.close()


def test_rejects_missing_plugin_dependency(tmp_path: Path) -> None:
    package = tmp_path / "dependent.modpkg"
    build_package(package, dependencies=["required.plugin"])
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == ("plugin dependencies are missing: ('required.plugin',)",)
    registry.close()


def test_rejects_dependency_overflow_before_per_dependency_queries(
    tmp_path: Path,
) -> None:
    package = tmp_path / "example.modpkg"
    build_package(
        package,
        dependencies=[f"dependency-{index}.plugin" for index in range(65)],
    )
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry_get = registry.get
    registry.get = Mock(wraps=registry_get)
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )

    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)

    assert not result.installed
    assert result.errors == (
        "plugin dependency graph is invalid: too many dependencies for "
        "example.plugin",
    )
    registry.get.assert_not_called()
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_install_reloads_revoked_publisher_under_lifecycle_lock(
    tmp_path: Path,
) -> None:
    trust_path = tmp_path / "trust-store.json"
    primary_store = trust_store(trust_path)
    stale_store = TrustStore(trust_path)
    stale_store.load()
    primary_store.set_enabled("trusted.example", False)
    package = tmp_path / "example.modpkg"
    build_package(package)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        stale_store,
        signature_verifier=AcceptingSignatureVerifier(),
    )

    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)

    assert not result.installed
    assert result.errors == ("publisher is not trusted",)
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_install_holds_lifecycle_lock_through_file_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod_root = tmp_path / "mod"
    lifecycle_lock = PluginLifecycleLock(mod_root)
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    installer = PluginInstaller(
        mod_root,
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
        lifecycle_lock=lifecycle_lock,
    )
    package = tmp_path / "example.modpkg"
    build_package(package)
    competitor = PluginLifecycleLock(mod_root, timeout_seconds=0)
    original_replace = installer_module.os.replace
    checked = False

    def guarded_replace(source: Path, destination: Path) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(installer_module.os, "replace", guarded_replace)

    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)

    assert result.installed
    assert checked
    assert installer.lifecycle_lock is lifecycle_lock
    registry.close()


def test_install_rejects_invalid_candidate_graph_before_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    dependent_before = write_installed_plugin(
        mod_root,
        registry,
        "dependent.plugin",
        dependencies=["example.plugin"],
    )
    installer = PluginInstaller(
        mod_root,
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    package = tmp_path / "cycle.modpkg"
    build_package(package, dependencies=["dependent.plugin"])
    replace_spy = Mock(wraps=installer_module.os.replace)
    monkeypatch.setattr(installer_module.os, "replace", replace_spy)

    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)

    assert not result.installed
    assert any("dependency" in error for error in result.errors)
    replace_spy.assert_not_called()
    assert registry.get("dependent.plugin") == dependent_before
    assert registry.get("example.plugin") is None
    assert not (mod_root / "installed" / "example.plugin").exists()
    registry.close()
