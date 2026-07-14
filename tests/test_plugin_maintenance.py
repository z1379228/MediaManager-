from __future__ import annotations

import json

from unittest.mock import Mock

from core.plugins.maintenance import PluginMaintenanceManager
from core.plugins.manager import PluginOperationResult
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode


def setup_maintenance(tmp_path):
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry.upsert(
        PluginRecord(
            "example.plugin",
            "1.0.0",
            True,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            "manifest-hash",
        )
    )
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    installed.mkdir(parents=True)
    (installed / "plugin.py").write_text("source", encoding="utf-8")
    plugin_manager = Mock()
    plugin_manager.set_enabled.return_value = PluginOperationResult(True)
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
    maintenance, registry, _, installed = setup_maintenance(tmp_path)
    assert maintenance.remove("example.plugin", SecurityMode.SAFE_MODE).successful
    result = maintenance.restore("example.plugin", SecurityMode.SAFE_MODE)
    record = registry.get("example.plugin")
    assert result.successful
    assert installed.is_dir()
    assert record.pending_action is PendingAction.NONE
    assert not record.enabled
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
        "maximum_core_version": "1.0.0",
        "permissions": [],
        "external_tools": [],
        "dependencies": ["example.plugin"],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    (dependent / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    registry.upsert(
        PluginRecord(
            "dependent.plugin",
            "1.0.0",
            False,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            "manifest-hash",
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
