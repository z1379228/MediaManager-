from __future__ import annotations

import sqlite3

from core.plugins.cleanup import PluginCleanupManager
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry


def make_record(pending: PendingAction = PendingAction.NONE) -> PluginRecord:
    return PluginRecord(
        "example.plugin",
        "1.1.0",
        False,
        pending,
        "TRUSTED_PUBLISHER",
        "trusted.example",
        (),
        "manifest-hash",
    )


def setup_cleanup(tmp_path, pending: PendingAction = PendingAction.NONE):
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry.upsert(make_record(pending))
    return PluginCleanupManager(tmp_path / "mod", registry), registry


def removed_path(tmp_path):
    return tmp_path / "mod" / "quarantine" / "removed" / "example.plugin" / "1.1.0"


def backup_path(tmp_path):
    return tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"


def test_purge_removed_plugin_deletes_record_archive_and_backups(tmp_path) -> None:
    cleanup, registry = setup_cleanup(tmp_path, PendingAction.REMOVE)
    removed, backup = removed_path(tmp_path), backup_path(tmp_path)
    removed.mkdir(parents=True)
    backup.mkdir(parents=True)
    (removed / "plugin.py").write_text("removed", encoding="utf-8")
    (backup / "plugin.py").write_text("backup", encoding="utf-8")
    result = cleanup.purge_removed_plugin("example.plugin")
    assert result.purged and result.warnings == ()
    assert registry.get("example.plugin") is None
    assert not removed.exists() and not backup.exists()
    registry.close()


def test_purge_removed_rolls_files_back_when_registry_delete_fails(tmp_path) -> None:
    _, registry = setup_cleanup(tmp_path, PendingAction.REMOVE)
    removed, backup = removed_path(tmp_path), backup_path(tmp_path)
    removed.mkdir(parents=True)
    backup.mkdir(parents=True)

    class FailingRegistry:
        def get(self, plugin_id):
            return registry.get(plugin_id)

        def delete(self, plugin_id):
            raise sqlite3.OperationalError("simulated delete failure")

        def set_pending(self, plugin_id, pending_action):
            registry.set_pending(plugin_id, pending_action)

    result = PluginCleanupManager(
        tmp_path / "mod", FailingRegistry()
    ).purge_removed_plugin("example.plugin")
    assert not result.purged
    assert removed.is_dir() and backup.is_dir()
    assert registry.get("example.plugin") is not None
    registry.close()


def test_purge_selected_backup_keeps_installed_record(tmp_path) -> None:
    cleanup, registry = setup_cleanup(tmp_path)
    backup = backup_path(tmp_path)
    backup.mkdir(parents=True)
    (backup / "plugin.py").write_text("backup", encoding="utf-8")
    result = cleanup.purge_backup("example.plugin", "1.0.0")
    assert result.purged and not backup.exists()
    assert registry.get("example.plugin") is not None
    registry.close()


def test_purge_refuses_active_plugin_and_current_version(tmp_path) -> None:
    cleanup, registry = setup_cleanup(tmp_path)
    assert cleanup.purge_removed_plugin("example.plugin").errors == (
        "plugin must be removed before purge",
    )
    assert cleanup.purge_backup("example.plugin", "1.1.0").errors == (
        "cannot purge the installed version",
    )
    registry.close()


def test_purge_rejects_path_escape_from_tampered_registry(tmp_path) -> None:
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry.upsert(
        PluginRecord(
            "../../escape",
            "1.0.0",
            False,
            PendingAction.REMOVE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            "hash",
        )
    )
    result = PluginCleanupManager(tmp_path / "mod", registry).purge_removed_plugin(
        "../../escape"
    )
    assert not result.purged
    assert result.errors == ("removed plugin archive is missing or unsafe",)
    registry.close()




