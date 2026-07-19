from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

import core.plugins.cleanup as cleanup_module
import core.plugins.lifecycle as lifecycle_module
from core.plugins.cleanup import PluginCleanupManager
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
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


def test_purge_backup_rejects_version_reparse_before_erasing_target(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup, registry = setup_cleanup(tmp_path)
    backup_alias = backup_path(tmp_path)
    backup_alias.parent.mkdir(parents=True)
    installed_victim = tmp_path / "mod" / "installed" / "example.plugin"
    installed_victim.mkdir(parents=True)
    (installed_victim / "plugin.py").write_text("installed", encoding="utf-8")
    original_resolve = Path.resolve

    def resolve_version_alias(path: Path, *args, **kwargs) -> Path:
        if path == backup_alias:
            return installed_victim
        return original_resolve(path, *args, **kwargs)

    original_reparse_check = lifecycle_module._is_reparse_point
    monkeypatch.setattr(Path, "resolve", resolve_version_alias)
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path == backup_alias or original_reparse_check(path),
    )
    erase_spy = Mock(wraps=cleanup_module.shutil.rmtree)
    monkeypatch.setattr(cleanup_module.shutil, "rmtree", erase_spy)

    result = cleanup.purge_backup("example.plugin", "1.0.0")

    assert not result.purged
    assert result.errors == ("backup version is missing or unsafe",)
    erase_spy.assert_not_called()
    assert (installed_victim / "plugin.py").read_text(encoding="utf-8") == "installed"
    registry.close()


def test_purge_removed_rejects_reparse_purge_root_before_file_move(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup, registry = setup_cleanup(tmp_path, PendingAction.REMOVE)
    removed = removed_path(tmp_path)
    removed.mkdir(parents=True)
    purge_root = tmp_path / "mod" / "quarantine" / "purge"
    purge_root.mkdir(parents=True)
    original_reparse_check = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path == purge_root or original_reparse_check(path),
    )
    replace_spy = Mock(wraps=cleanup_module.os.replace)
    monkeypatch.setattr(cleanup_module.os, "replace", replace_spy)

    result = cleanup.purge_removed_plugin("example.plugin")

    assert not result.purged
    assert result.errors == ("plugin purge path is unsafe",)
    replace_spy.assert_not_called()
    assert removed.is_dir()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
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


def test_purge_holds_lifecycle_lock_through_file_moves(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup, registry = setup_cleanup(tmp_path, PendingAction.REMOVE)
    shared_lock = PluginLifecycleLock(tmp_path / "mod")
    cleanup.lifecycle_lock = shared_lock
    removed = removed_path(tmp_path)
    removed.mkdir(parents=True)
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_replace = cleanup_module.os.replace
    checked = False

    def guarded_replace(source, destination) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(cleanup_module.os, "replace", guarded_replace)

    result = cleanup.purge_removed_plugin("example.plugin")

    assert result.purged
    assert checked
    registry.close()




