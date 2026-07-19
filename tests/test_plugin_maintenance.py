from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

import core.plugins.lifecycle as lifecycle_module
import core.plugins.maintenance as maintenance_module
from core.plugins.dependency_graph import MAX_MANIFEST_BYTES
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.maintenance import PluginMaintenanceManager
from core.plugins.manager import PluginOperationResult
from core.plugins.recovery import PluginTransactionRecovery
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.version import CORE_VERSION


def manifest_bytes(
    plugin_id: str,
    *,
    dependencies: list[str] | None = None,
    maximum_core_version: str = CORE_VERSION,
) -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "id": plugin_id,
            "name": "Test plugin",
            "version": "1.0.0",
            "publisher": "trusted.example",
            "plugin_type": "processor",
            "entry_point": "plugin.py",
            "api_version": "1.0",
            "minimum_core_version": "0.1.0",
            "maximum_core_version": maximum_core_version,
            "permissions": [],
            "external_tools": [],
            "dependencies": dependencies or [],
            "files_manifest": "files.json",
            "signature": "plugin.sig",
        }
    ).encode()


def setup_maintenance(tmp_path):
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    installed.mkdir(parents=True)
    manifest = manifest_bytes("example.plugin")
    (installed / "plugin.json").write_bytes(manifest)
    (installed / "plugin.py").write_text("source", encoding="utf-8")
    registry.upsert(
        PluginRecord(
            "example.plugin",
            "1.0.0",
            True,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            hashlib.sha256(manifest).hexdigest(),
        )
    )
    plugin_manager = Mock()
    plugin_manager.set_enabled.return_value = PluginOperationResult(True)
    plugin_manager.verify_directory.return_value = ()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    maintenance = PluginMaintenanceManager(
        tmp_path / "mod", registry, plugin_manager
    )
    return maintenance, registry, plugin_manager, installed


def test_remove_moves_plugin_to_recoverable_quarantine(tmp_path) -> None:
    maintenance, registry, plugin_manager, installed = setup_maintenance(tmp_path)
    result = maintenance.remove("example.plugin", SecurityMode.BLOCKED)
    removed = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    assert result.successful
    assert not installed.exists()
    assert (removed / "plugin.py").is_file()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    plugin_manager.set_enabled.assert_called_once_with(
        "example.plugin", False, SecurityMode.BLOCKED
    )
    registry.close()


def test_restore_returns_plugin_disabled_to_installed_root(tmp_path) -> None:
    maintenance, registry, plugin_manager, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)
    record = registry.get("example.plugin")
    assert result.successful
    assert installed.is_dir()
    assert record.pending_action is PendingAction.NONE
    assert not record.enabled
    assert plugin_manager.verify_directory.call_count == 2
    assert all(
        call.kwargs["refresh_trust_store"]
        for call in plugin_manager.verify_directory.call_args_list
    )
    registry.close()


def test_blocked_mode_can_remove_but_cannot_restore(tmp_path) -> None:
    maintenance, registry, _, _ = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.BLOCKED).successful
    result = maintenance.restore("example.plugin", SecurityMode.BLOCKED)
    assert not result.successful
    assert result.errors == (
        "plugins cannot be restored in BLOCKED security mode",
    )
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()


def test_remove_refuses_existing_archive_without_overwrite(tmp_path) -> None:
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    archive.mkdir(parents=True)
    result = maintenance.remove("example.plugin", SecurityMode.SAFE_MODE)
    assert not result.successful
    assert result.errors == ("removed plugin archive already exists",)
    assert installed.is_dir()
    registry.close()

def test_remove_refuses_plugin_required_by_another_install(tmp_path) -> None:
    maintenance, registry, plugin_manager, installed = setup_maintenance(tmp_path)
    dependent = tmp_path / "mod" / "installed" / "dependent.plugin"
    dependent.mkdir(parents=True)
    manifest = manifest_bytes(
        "dependent.plugin",
        dependencies=["example.plugin"],
    )
    (dependent / "plugin.json").write_bytes(manifest)
    registry.upsert(
        PluginRecord(
            "dependent.plugin",
            "1.0.0",
            False,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            hashlib.sha256(manifest).hexdigest(),
        )
    )
    result = maintenance.remove("example.plugin", SecurityMode.SAFE_MODE)
    assert not result.successful
    assert result.errors == (
        "plugin is required by installed plugins: ('dependent.plugin',)",
    )
    assert installed.is_dir()
    plugin_manager.set_enabled.assert_not_called()
    registry.close()


def test_remove_holds_lifecycle_lock_through_file_move(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, plugin_manager, _ = setup_maintenance(tmp_path)
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_replace = maintenance_module.os.replace
    checked = False

    def guarded_replace(source, destination) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(maintenance_module.os, "replace", guarded_replace)

    result = maintenance.remove("example.plugin", SecurityMode.SAFE_MODE)

    assert result.successful
    assert checked
    assert maintenance.lifecycle_lock is plugin_manager.lifecycle_lock
    registry.close()


def test_restore_holds_lifecycle_lock_through_file_move(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, plugin_manager, _ = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_replace = maintenance_module.os.replace
    checked = False

    def guarded_replace(source, destination) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(maintenance_module.os, "replace", guarded_replace)

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert result.successful
    assert checked
    assert maintenance.lifecycle_lock is plugin_manager.lifecycle_lock
    registry.close()


def test_restore_rejects_invalid_candidate_graph_before_file_or_registry_change(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    candidate_manifest = manifest_bytes(
        "example.plugin",
        dependencies=["missing.plugin"],
    )
    (archive / "plugin.json").write_bytes(candidate_manifest)
    removed = registry.get("example.plugin")
    registry.upsert(
        PluginRecord(
            removed.plugin_id,
            removed.installed_version,
            removed.enabled,
            removed.pending_action,
            removed.trust_level,
            removed.publisher_id,
            removed.approved_permissions,
            hashlib.sha256(candidate_manifest).hexdigest(),
            removed.failure_count,
            removed.quarantine_reason,
        )
    )
    removed_before = registry.get("example.plugin")
    replace_spy = Mock(wraps=maintenance_module.os.replace)
    monkeypatch.setattr(maintenance_module.os, "replace", replace_spy)

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert any("dependency" in error for error in result.errors)
    replace_spy.assert_not_called()
    assert registry.get("example.plugin") == removed_before
    assert archive.is_dir()
    assert not installed.exists()
    registry.close()


def test_restore_rejects_incompatible_core_before_file_or_registry_change(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    candidate_manifest = manifest_bytes(
        "example.plugin",
        maximum_core_version="0.1.0",
    )
    (archive / "plugin.json").write_bytes(candidate_manifest)
    removed = registry.get("example.plugin")
    registry.upsert(
        replace(
            removed,
            manifest_hash=hashlib.sha256(candidate_manifest).hexdigest(),
        )
    )
    removed_before = registry.get("example.plugin")
    replace_spy = Mock(wraps=maintenance_module.os.replace)
    monkeypatch.setattr(maintenance_module.os, "replace", replace_spy)

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert result.errors == (f"plugin is incompatible with core {CORE_VERSION}",)
    replace_spy.assert_not_called()
    assert registry.get("example.plugin") == removed_before
    assert archive.is_dir()
    assert not installed.exists()
    registry.close()


def test_restore_reverts_move_when_post_move_verification_fails(tmp_path) -> None:
    maintenance, registry, plugin_manager, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    removed_before = registry.get("example.plugin")
    plugin_manager.verify_directory.side_effect = [
        (),
        ("installed plugin manifest was modified",),
    ]

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert result.errors == ("installed plugin manifest was modified",)
    assert archive.is_dir()
    assert not installed.exists()
    assert registry.get("example.plugin") == removed_before
    registry.close()


def test_restore_rejects_oversized_manifest_before_file_move(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    (archive / "plugin.json").write_bytes(b"x" * (MAX_MANIFEST_BYTES + 1))
    replace_spy = Mock(wraps=maintenance_module.os.replace)
    monkeypatch.setattr(maintenance_module.os, "replace", replace_spy)

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert result.errors == (
        "removed plugin manifest is invalid: plugin manifest exceeds the size limit",
    )
    replace_spy.assert_not_called()
    assert archive.is_dir()
    assert not installed.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()


def test_startup_recovery_contains_restore_when_compensation_move_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, plugin_manager, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    plugin_manager.verify_directory.side_effect = [
        (),
        ("installed plugin manifest was modified",),
    ]
    original_replace = maintenance_module.os.replace
    replace_count = 0

    def fail_first_compensation(source, destination) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("simulated compensation failure")
        original_replace(source, destination)

    monkeypatch.setattr(
        maintenance_module.os,
        "replace",
        fail_first_compensation,
    )

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert installed.is_dir()
    assert not archive.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE

    recovery = PluginTransactionRecovery(
        tmp_path / "mod",
        registry,
        plugin_manager,
    )
    report = recovery.recover_all()

    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert archive.is_dir()
    assert not installed.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()


def test_restore_rejects_reparse_installed_root_before_file_move(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    archive = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / "1.0.0"
    )
    original = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path.name == "installed" or original(path),
    )

    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)

    assert not result.successful
    assert result.errors == ("plugin lifecycle path is unsafe",)
    assert archive.is_dir()
    assert not installed.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()
