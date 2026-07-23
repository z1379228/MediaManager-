from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import Mock

from core.plugins.host_launcher import PluginLaunchError, PluginProcess
from core.plugins.lifecycle import PluginLifecycleLockError
from core.plugins.manager import PluginManager
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.supervisor import PluginSupervisor
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
        "maximum_core_version": CORE_VERSION,
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


def install_plugin(
    tmp_path: Path,
    registry: PluginRegistry,
    plugin_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    enabled: bool = False,
    pending_action: PendingAction = PendingAction.NONE,
) -> Path:
    root = tmp_path / "mod" / "installed" / plugin_id
    root.mkdir(parents=True, exist_ok=True)
    source = f"def handle_request(request): return {plugin_id!r}\n".encode()
    (root / "plugin.py").write_bytes(source)
    manifest = {
        "schema_version": 2,
        "id": plugin_id,
        "name": plugin_id,
        "version": "1.0.0",
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": list(dependencies),
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
        json.dumps(
            {"files": {"plugin.py": hashlib.sha256(source).hexdigest()}}
        ),
        encoding="utf-8",
    )
    registry.upsert(
        PluginRecord(
            plugin_id,
            "1.0.0",
            enabled,
            pending_action,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            hashlib.sha256(manifest_bytes).hexdigest(),
        )
    )
    return root


def assert_errors_contain(
    errors: tuple[str, ...],
    *fragments: str,
) -> None:
    message = "\n".join(errors).lower()
    for fragment in fragments:
        assert fragment.lower() in message


def test_normal_mode_enables_verified_plugin(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert result.successful
    assert registry.get("example.plugin").enabled
    supervisor._start_claimed.assert_called_once()
    registry.close()


def test_safe_mode_refuses_enable(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    result = manager.set_enabled("example.plugin", True, SecurityMode.SAFE_MODE)
    assert not result.successful
    supervisor._start_claimed.assert_not_called()
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
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_executable_runtime_policy_can_fail_closed(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    manager.allow_executable_plugins = False
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert result.errors == (
        "external executable MOD runtime is disabled until OS-level isolation is available",
    )
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_modified_installed_file_is_refused(tmp_path: Path) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    (root / "plugin.py").write_text("tampered", encoding="utf-8")
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert not result.successful
    assert result.errors == ("installed file hash mismatch: plugin.py",)
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_enable_rejects_missing_transitive_dependency_before_claim(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=True,
    )
    claim_lifecycle = Mock(wraps=registry.claim_lifecycle)
    registry.claim_lifecycle = claim_lifecycle

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(result.errors, "missing", "dependency", "leaf.plugin")
    claim_lifecycle.assert_not_called()
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_enable_rejects_disabled_transitive_dependency_before_claim(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=True,
    )
    install_plugin(tmp_path, registry, "leaf.plugin", enabled=False)
    claim_lifecycle = Mock(wraps=registry.claim_lifecycle)
    registry.claim_lifecycle = claim_lifecycle

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(result.errors, "disabled", "dependency", "leaf.plugin")
    claim_lifecycle.assert_not_called()
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_enable_rejects_pending_transitive_dependency_before_claim(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=True,
    )
    install_plugin(
        tmp_path,
        registry,
        "leaf.plugin",
        enabled=True,
        pending_action=PendingAction.UPDATE,
    )
    claim_lifecycle = Mock(wraps=registry.claim_lifecycle)
    registry.claim_lifecycle = claim_lifecycle

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "pending",
        "dependency",
        "leaf.plugin",
        "UPDATE",
    )
    claim_lifecycle.assert_not_called()
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_enable_rejects_tampered_transitive_dependency_before_claim(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=True,
    )
    leaf_root = install_plugin(tmp_path, registry, "leaf.plugin", enabled=True)
    (leaf_root / "plugin.py").write_text("tampered", encoding="utf-8")
    claim_lifecycle = Mock(wraps=registry.claim_lifecycle)
    registry.claim_lifecycle = claim_lifecycle

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "dependency",
        "leaf.plugin",
        "hash mismatch",
    )
    claim_lifecycle.assert_not_called()
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_enable_accepts_verified_enabled_transitive_dependencies_without_cascade(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=True,
    )
    install_plugin(tmp_path, registry, "leaf.plugin", enabled=True)

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert result.successful
    supervisor._start_claimed.assert_called_once()
    middle = registry.get("middle.plugin")
    leaf = registry.get("leaf.plugin")
    assert middle is not None and middle.enabled
    assert leaf is not None and leaf.enabled
    registry.close()


def test_disable_stops_running_plugin_in_safe_mode(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    result = manager.set_enabled("example.plugin", False, SecurityMode.SAFE_MODE)
    assert result.successful
    supervisor.stop.assert_called_once_with("example.plugin")
    assert not registry.get("example.plugin").enabled
    registry.close()


def test_disable_contains_runtime_and_retains_journal_when_graph_is_tampered(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    manifest_path = root / "plugin.json"
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    observer = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    finish_lifecycle = Mock(wraps=registry.finish_lifecycle)
    registry.finish_lifecycle = finish_lifecycle

    def observe_disable_claim(_plugin_id: str) -> None:
        claimed = observer.get("example.plugin")
        assert claimed is not None
        assert claimed.enabled
        assert claimed.pending_action is PendingAction.DISABLE

    supervisor.stop.side_effect = observe_disable_claim

    result = manager.set_enabled("example.plugin", False, SecurityMode.SAFE_MODE)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "manifest tampered",
        "runtime stopped",
        "dependency safety",
        "journal remains",
        "recovery",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    finish_lifecycle.assert_not_called()
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    observer.close()
    registry.close()


def test_disable_retains_containment_journal_when_graph_invalid_stop_fails(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    (root / "plugin.json").unlink()
    supervisor.stop.side_effect = RuntimeError("stop unconfirmed")

    result = manager.set_enabled("example.plugin", False, SecurityMode.SAFE_MODE)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "manifest missing",
        "containment could not be confirmed",
        "stop unconfirmed",
        "journal remains",
        "recovery",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_disable_contains_target_when_unrelated_manifest_invalidates_graph(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    unrelated_root = install_plugin(
        tmp_path,
        registry,
        "unrelated.plugin",
        enabled=False,
    )
    manifest_path = unrelated_root / "plugin.json"
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")

    result = manager.set_enabled("example.plugin", False, SecurityMode.SAFE_MODE)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "manifest tampered",
        "unrelated.plugin",
        "runtime stopped",
        "journal remains",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_disable_rejects_enabled_transitive_dependent_through_disabled_node(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
        enabled=True,
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=False,
    )
    install_plugin(tmp_path, registry, "leaf.plugin", enabled=True)
    claim_lifecycle = Mock(wraps=registry.claim_lifecycle)
    registry.claim_lifecycle = claim_lifecycle

    result = manager.set_enabled("leaf.plugin", False, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "enabled",
        "dependent",
        "example.plugin",
    )
    claim_lifecycle.assert_not_called()
    supervisor.stop.assert_not_called()
    leaf = registry.get("leaf.plugin")
    assert leaf is not None
    assert leaf.enabled
    assert leaf.pending_action is PendingAction.NONE
    registry.close()


def test_disable_allows_target_when_all_transitive_dependents_are_disabled(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "example.plugin",
        dependencies=("middle.plugin",),
        enabled=False,
    )
    install_plugin(
        tmp_path,
        registry,
        "middle.plugin",
        dependencies=("leaf.plugin",),
        enabled=False,
    )
    install_plugin(tmp_path, registry, "leaf.plugin", enabled=True)

    result = manager.set_enabled("leaf.plugin", False, SecurityMode.NORMAL)

    assert result.successful
    supervisor.stop.assert_called_once_with("leaf.plugin")
    leaf = registry.get("leaf.plugin")
    assert leaf is not None
    assert not leaf.enabled
    assert leaf.pending_action is PendingAction.NONE
    registry.close()


def test_toggle_rejects_existing_pending_journal_without_side_effects(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    record = registry.get("example.plugin")
    assert record is not None
    registry.upsert(replace(record, pending_action=PendingAction.UPDATE))

    result = manager.set_enabled(
        "example.plugin",
        False,
        SecurityMode.NORMAL,
    )

    assert not result.successful
    assert result.errors == ("plugin lifecycle has pending action: UPDATE",)
    supervisor.stop.assert_not_called()
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE
    registry.close()


def test_enable_journal_is_committed_before_supervisor_start(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    observer = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")

    def observe_enable_claim(_record: PluginRecord) -> None:
        claimed = observer.get("example.plugin")
        assert claimed is not None
        assert claimed.pending_action is PendingAction.ENABLE
        assert not claimed.enabled

    supervisor._start_claimed.side_effect = observe_enable_claim

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert result.successful
    finalized = registry.get("example.plugin")
    assert finalized is not None
    assert finalized.enabled
    assert finalized.pending_action is PendingAction.NONE
    observer.close()
    registry.close()


def test_disable_journal_is_committed_before_supervisor_stop(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    observer = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")

    def observe_disable_claim(_plugin_id: str) -> None:
        claimed = observer.get("example.plugin")
        assert claimed is not None
        assert claimed.pending_action is PendingAction.DISABLE
        assert claimed.enabled

    supervisor.stop.side_effect = observe_disable_claim

    result = manager.set_enabled("example.plugin", False, SecurityMode.NORMAL)

    assert result.successful
    finalized = registry.get("example.plugin")
    assert finalized is not None
    assert not finalized.enabled
    assert finalized.pending_action is PendingAction.NONE
    observer.close()
    registry.close()


def test_lifecycle_lock_failure_has_no_toggle_side_effects(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)

    class BusyLifecycleLock:
        @contextmanager
        def hold(self) -> Iterator[None]:
            raise PluginLifecycleLockError("busy")
            yield

    manager.lifecycle_lock = BusyLifecycleLock()

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert result.errors == ("plugin lifecycle is busy",)
    supervisor._start_claimed.assert_not_called()
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.NONE
    registry.close()


def test_outer_shared_lifecycle_lock_is_reentrant(tmp_path: Path) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)

    with manager.lifecycle_lock.hold():
        result = manager.set_enabled(
            "example.plugin",
            True,
            SecurityMode.NORMAL,
        )

    assert result.successful
    supervisor._start_claimed.assert_called_once()
    registry.close()


def test_start_failure_reports_complete_rollback_after_journal_clear(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    supervisor._start_claimed.side_effect = RuntimeError("start failed")

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "plugin failed to start: start failed",
        "rollback complete",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.NONE
    registry.close()


def test_start_failure_reports_incomplete_rollback_when_stop_fails(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    supervisor._start_claimed.side_effect = RuntimeError("start failed")
    supervisor.stop.side_effect = RuntimeError("stop failed")

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "plugin failed to start: start failed",
        "rollback incomplete",
        "stop failed",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_start_failure_keeps_enable_journal_when_rollback_clear_errors(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    supervisor._start_claimed.side_effect = RuntimeError("start failed")
    registry.finish_lifecycle = Mock(
        side_effect=sqlite3.OperationalError("registry unavailable")
    )

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "plugin failed to start: start failed",
        "runtime is not running",
        "ENABLE journal state is unconfirmed",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_launch_cleanup_failure_keeps_retryable_handle_and_enable_journal(
    tmp_path: Path,
) -> None:
    manager, registry, _supervisor, _ = setup_manager(tmp_path)
    process = SimpleNamespace(pid=321, poll=lambda: None)
    launched = PluginProcess("example.plugin", process, Mock())
    launcher = Mock()
    launcher.launch.side_effect = PluginLaunchError(
        launched,
        RuntimeError("invalid handshake"),
        RuntimeError("cleanup could not be confirmed"),
    )
    launcher.stop.side_effect = RuntimeError("retry stop failed")
    supervisor = PluginSupervisor(
        tmp_path / "mod",
        registry,
        launcher=launcher,
    )
    manager._supervisor = supervisor

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "invalid handshake",
        "cleanup could not be confirmed",
        "rollback incomplete",
        "retry stop failed",
    )
    assert "rollback complete" not in "\n".join(result.errors).lower()
    assert supervisor.processes["example.plugin"] is launched
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_stop_failure_preserves_disable_journal_for_recovery(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    supervisor.stop.side_effect = RuntimeError("stop failed")

    result = manager.set_enabled("example.plugin", False, SecurityMode.NORMAL)

    assert not result.successful
    assert result.errors == (
        "plugin failed to stop: stop failed; "
        "DISABLE rollback incomplete; recovery is required",
    )
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_enable_finalize_conflict_stops_runtime_and_preserves_journal(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    manager.registry.finish_lifecycle = Mock(return_value=False)

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert result.errors == (
        "plugin ENABLE finalization failed; recovery is required",
        "plugin ENABLE rollback incomplete: "
        "runtime is not running; ENABLE journal state is unconfirmed",
    )
    supervisor._start_claimed.assert_called_once()
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_enable_finalize_sqlite_error_stops_runtime_and_preserves_journal(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.finish_lifecycle = Mock(
        side_effect=sqlite3.OperationalError("registry unavailable")
    )

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "ENABLE finalization failed",
        "runtime is not running",
        "ENABLE journal state is unconfirmed",
    )
    supervisor._start_claimed.assert_called_once()
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_disable_finalize_conflict_reports_incomplete_rollback(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    manager.registry.finish_lifecycle = Mock(return_value=False)

    result = manager.set_enabled("example.plugin", False, SecurityMode.NORMAL)

    assert not result.successful
    assert result.errors == (
        "plugin DISABLE finalization failed; recovery is required",
        "plugin DISABLE rollback incomplete: "
        "runtime is not running; DISABLE journal state is unconfirmed",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_disable_finalize_sqlite_error_reports_incomplete_rollback(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    registry.set_enabled("example.plugin", True)
    registry.finish_lifecycle = Mock(
        side_effect=sqlite3.OperationalError("registry unavailable")
    )

    result = manager.set_enabled("example.plugin", False, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "DISABLE finalization failed",
        "runtime is not running",
        "DISABLE journal state is unconfirmed",
    )
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_enable_finalize_failure_reports_incomplete_rollback_when_stop_fails(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    manager.registry.finish_lifecycle = Mock(return_value=False)
    supervisor.stop.side_effect = RuntimeError("stop failed")

    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)

    assert not result.successful
    assert_errors_contain(
        result.errors,
        "ENABLE finalization failed",
        "rollback incomplete",
        "stop failed",
    )
    supervisor._start_claimed.assert_called_once()
    supervisor.stop.assert_called_once_with("example.plugin")
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.ENABLE
    registry.close()


def test_undeclared_installed_file_is_refused(tmp_path: Path) -> None:
    manager, registry, supervisor, root = setup_manager(tmp_path)
    (root / "hidden.py").write_text("hidden = True", encoding="utf-8")
    result = manager.set_enabled("example.plugin", True, SecurityMode.NORMAL)
    assert not result.successful
    assert result.errors == ("undeclared installed files: ['hidden.py']",)
    supervisor._start_claimed.assert_not_called()
    registry.close()


def test_start_enabled_uses_dependency_first_order_from_manager(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "a.dependent",
        dependencies=("z.dependency",),
        enabled=True,
    )
    install_plugin(tmp_path, registry, "z.dependency", enabled=True)

    outcomes = manager.start_enabled(SecurityMode.NORMAL)

    assert [
        call.args[0].plugin_id
        for call in supervisor._start_claimed.call_args_list
    ] == [
        "z.dependency",
        "a.dependent",
    ]
    assert tuple(plugin_id for plugin_id, result in outcomes if result.successful) == (
        "z.dependency",
        "a.dependent",
    )
    registry.close()


def test_start_enabled_blocks_transitive_downstream_after_dependency_failure(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "a.downstream",
        dependencies=("z.dependency",),
        enabled=True,
    )
    install_plugin(
        tmp_path,
        registry,
        "b.transitive",
        dependencies=("a.downstream",),
        enabled=True,
    )
    install_plugin(tmp_path, registry, "m.independent", enabled=True)
    install_plugin(tmp_path, registry, "z.dependency", enabled=True)

    def fail_dependency(record: PluginRecord) -> None:
        if record.plugin_id == "z.dependency":
            raise RuntimeError("dependency boot failed")

    supervisor._start_claimed.side_effect = fail_dependency

    outcomes = manager.start_enabled(SecurityMode.NORMAL)

    assert [
        call.args[0].plugin_id
        for call in supervisor._start_claimed.call_args_list
    ] == [
        "z.dependency",
        "m.independent",
    ]
    by_id = dict(outcomes)
    assert not by_id["z.dependency"].successful
    assert_errors_contain(
        by_id["z.dependency"].errors,
        "dependency boot failed",
    )
    assert not by_id["a.downstream"].successful
    assert_errors_contain(
        by_id["a.downstream"].errors,
        "dependency",
        "z.dependency",
        "blocked",
    )
    assert not by_id["b.transitive"].successful
    assert_errors_contain(
        by_id["b.transitive"].errors,
        "dependency",
        "blocked",
    )
    assert by_id["m.independent"].successful
    registry.close()


def test_start_enabled_invalid_graph_returns_audit_failures_without_start(
    tmp_path: Path,
) -> None:
    manager, registry, supervisor, _ = setup_manager(tmp_path)
    install_plugin(
        tmp_path,
        registry,
        "a.dependent",
        dependencies=("missing.dependency",),
        enabled=True,
    )

    outcomes = manager.start_enabled(SecurityMode.NORMAL)

    supervisor._start_claimed.assert_not_called()
    assert tuple(plugin_id for plugin_id, _ in outcomes) == ("a.dependent",)
    result = dict(outcomes)["a.dependent"]
    assert not result.successful
    assert_errors_contain(
        result.errors,
        "dependency graph",
        "missing dependency",
        "missing.dependency",
    )
    registry.close()
