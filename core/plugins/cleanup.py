"""Explicit permanent cleanup of removed plugins and retained backups."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.plugins.lifecycle import (
    PluginLifecycleLock,
    PluginLifecycleLockError,
    PluginLifecyclePathError,
    resolve_lifecycle_path,
)
from core.plugins.registry import PendingAction, PluginRegistry
from core.version import plugin_version_key


@dataclass(frozen=True, slots=True)
class PurgeResult:
    purged: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class PluginCleanupManager:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        *,
        lifecycle_lock: PluginLifecycleLock | None = None,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.lifecycle_lock = lifecycle_lock or PluginLifecycleLock(self.mod_root)

    def purge_removed_plugin(self, plugin_id: str) -> PurgeResult:
        try:
            with self.lifecycle_lock.hold():
                return self._purge_removed_plugin_locked(plugin_id)
        except PluginLifecycleLockError:
            return PurgeResult(False, errors=("plugin lifecycle is busy",))

    def _purge_removed_plugin_locked(self, plugin_id: str) -> PurgeResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return PurgeResult(False, errors=("plugin record does not exist",))
        if record.pending_action is not PendingAction.REMOVE:
            return PurgeResult(False, errors=("plugin must be removed before purge",))
        try:
            removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "removed",
                plugin_id,
                record.installed_version,
            )
        except PluginLifecyclePathError:
            return PurgeResult(
                False, errors=("removed plugin archive is missing or unsafe",)
            )
        if not self._safe_directory(removed):
            return PurgeResult(
                False, errors=("removed plugin archive is missing or unsafe",)
            )
        try:
            backups = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                plugin_id,
            )
        except PluginLifecyclePathError:
            return PurgeResult(False, errors=("plugin backup path is unsafe",))
        staging_key = self.purge_staging_key(plugin_id)
        try:
            staging = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
            )
            staged_removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
                "removed",
            )
            staged_backups = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
                "backups",
            )
        except PluginLifecyclePathError:
            return PurgeResult(False, errors=("plugin purge path is unsafe",))
        if staging.exists():
            return PurgeResult(
                False, errors=("plugin purge transaction already exists",)
            )
        moved_backups = False
        try:
            staging.mkdir(parents=True)
            # Re-check the freshly created compartment before any registered
            # archive can be moved into it.
            staging = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
            )
            removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "removed",
                plugin_id,
                record.installed_version,
            )
            backups = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                plugin_id,
            )
            staged_removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
                "removed",
            )
            staged_backups = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
                "backups",
            )
            self.registry.set_pending(plugin_id, PendingAction.PURGE)
            os.replace(removed, staged_removed)
            if backups.is_dir():
                os.replace(backups, staged_backups)
                moved_backups = True
            try:
                self.registry.delete(plugin_id)
            except KeyError, sqlite3.Error:
                os.replace(staged_removed, removed)
                if moved_backups:
                    backups.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staged_backups, backups)
                self.registry.set_pending(plugin_id, PendingAction.REMOVE)
                raise
        except (OSError, KeyError, sqlite3.Error, PluginLifecyclePathError) as error:
            return PurgeResult(False, errors=(f"plugin purge failed: {error}",))
        try:
            staging = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
                staging_key,
            )
        except PluginLifecyclePathError:
            warning = "purged data remains isolated for later cleanup: unsafe path"
        else:
            warning = self._erase(staging)
        return PurgeResult(True, (warning,) if warning else ())

    def purge_backup(self, plugin_id: str, version: str) -> PurgeResult:
        try:
            with self.lifecycle_lock.hold():
                return self._purge_backup_locked(plugin_id, version)
        except PluginLifecycleLockError:
            return PurgeResult(False, errors=("plugin lifecycle is busy",))

    def _purge_backup_locked(self, plugin_id: str, version: str) -> PurgeResult:
        try:
            plugin_version_key(version)
        except ValueError:
            return PurgeResult(False, errors=("invalid backup version",))
        record = self.registry.get(plugin_id)
        if record is None:
            return PurgeResult(False, errors=("plugin record does not exist",))
        if version == record.installed_version:
            return PurgeResult(False, errors=("cannot purge the installed version",))
        try:
            source = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                plugin_id,
                version,
            )
        except PluginLifecyclePathError:
            return PurgeResult(False, errors=("backup version is missing or unsafe",))
        if not self._safe_directory(source):
            return PurgeResult(False, errors=("backup version is missing or unsafe",))
        warning = self._erase(source)
        return PurgeResult(True, (warning,) if warning else ())

    def removed_path(self, plugin_id: str, version: str) -> Path:
        return (
            self.mod_root / "quarantine" / "removed" / plugin_id / version
        ).resolve()

    def purge_staging_path(self, plugin_id: str) -> Path:
        key = self.purge_staging_key(plugin_id)
        return (self.mod_root / "quarantine" / "purge" / key).resolve()

    @staticmethod
    def purge_staging_key(plugin_id: str) -> str:
        return hashlib.sha256(plugin_id.encode("utf-8")).hexdigest()

    def _safe_directory(self, path: Path) -> bool:
        return (
            path.is_relative_to(self.mod_root)
            and path.is_dir()
            and not path.is_symlink()
        )

    @staticmethod
    def _erase(path: Path) -> str | None:
        try:
            shutil.rmtree(path)
            return None
        except OSError as error:
            return f"purged data remains isolated for later cleanup: {error}"
