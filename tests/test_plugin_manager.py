from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

from core.plugins.manager import PluginManager
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureResult
from core.security.trust_store import TrustStore


class AcceptingSignatureVerifier:
    def verify(
        self, payload: bytes, signature: bytes, public_key: str
    ) -> SignatureResult:
        assert payload and signature and public_key
        return SignatureResult(True, "accepted for test")


def setup_manager(tmp_path: Path) -> tuple[PluginManager, PluginRegistry, Mock, Path]:
    key = base64.b64encode(b"k" * 32).decode("ascii")
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("trusted.example", key)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    root = tmp_path / "mod" / "installed" / "example.plugin"
    root.mkdir(parents=True)
    source = b"def handle_request(request): return request\n"
    (root / "plugin.py").write_bytes(source)
    manifest = {
        "schema_version": 2,
        "id": "example.plugin",
        "name": "Example",
        "version": "1.0.0",
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": "1.0.0",
        "permissions": [],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
        "runtime": "python-subprocess",
        "runtime_protocol": "1.0",
        "ui_descriptor": "",
    }
    manifest_bytes = json.dumps(manifest).encode()
    (root / "plugin.json").write_bytes(manifest_bytes)
    (root / "plugin.sig").write_bytes(b"test-signature")
    (root / "files.json").write_text(
        json.dumps({"files": {"plugin.py": hashlib.sha256(source).hexdigest()}}),
        encoding="utf-8",
    )
    registry.upsert(
        PluginRecord(
            "example.plugin",
            "1.0.0",
            False,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            hashlib.sha256(manifest_bytes).hexdigest(),
        )
    )
    supervisor = Mock()
    manager = PluginManager(
        tmp_path / "mod",
        registry,
        supervisor,
        store,
        signature_verifier=AcceptingSignatureVerifier(),
    )
    return manager, registry, supervisor, root


def test_normal_mode_enables_verified_plugin(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert result.successful
    assert registry.get("example.plugin").enabled
    supervisor.start.assert_called_once()
    registry.close()


def test_safe_mode_refuses_enable(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    result = manager.set_enabled("example.plugin", True, SecurityMode.SAFE_MODE)
    assert not result.successful
    supervisor.start.assert_not_called()
    assert not registry.get("example.plugin").enabled
    registry.close()


def test_legacy_executable_manifest_is_refused_in_normal_mode(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    manifest_path = root / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 1
    manifest.pop("runtime")
    manifest.pop("runtime_protocol")
    manifest.pop("ui_descriptor")
    manifest_bytes = json.dumps(manifest).encode()
    manifest_path.write_bytes(manifest_bytes)
    record = registry.get("example.plugin")
    assert record is not None
    registry.upsert(
        PluginRecord(
            record.plugin_id,
            record.installed_version,
            False,
            record.pending_action,
            record.trust_level,
            record.publisher_id,
            record.approved_permissions,
            hashlib.sha256(manifest_bytes).hexdigest(),
        )
    )
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert result.errors == (
        "legacy executable MOD must be repackaged with manifest v2",
    )
    supervisor.start.assert_not_called()
    registry.close()


def test_executable_runtime_policy_can_fail_closed(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    manager.allow_executable_plugins = False
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert result.errors == (
        "external executable MOD runtime is disabled until OS-level isolation is available",
    )
    supervisor.start.assert_not_called()
    registry.close()


def test_modified_installed_file_is_refused(tmp_path: Path) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    (root / "plugin.py").write_text("tampered", encoding="utf-8")
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert not result.successful
    assert result.errors == ("installed file hash mismatch: plugin.py",)
    supervisor.start.assert_not_called()
    registry.close()


def test_disable_stops_running_plugin_in_safe_mode(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    result = manager.set_enabled("example.plugin", False, SecurityMode.SAFE_MODE)
    assert result.successful
    supervisor.stop.assert_called_once_with("example.plugin")
    assert not registry.get("example.plugin").enabled
    registry.close()

def test_undeclared_installed_file_is_refused(tmp_path: Path) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    (root / "hidden.py").write_text("hidden = True", encoding="utf-8")
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert not result.successful
    assert result.errors == ("undeclared installed files: ['hidden.py']",)
    supervisor.start.assert_not_called()
    registry.close()
