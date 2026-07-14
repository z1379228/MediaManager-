"""Explicit permanent cleanup of removed plugins and retained backups."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.plugins.registry import PendingAction, PluginRegistry
from core.version import plugin_version_key


@dataclass(frozen=True, slots=True)
class PurgeResult:
    purged: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class PluginCleanupManager:
    def __init__(self, mod_root: Path, registry: PluginRegistry) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry

    def purge_removed_plugin(self, plugin_id: str) -> PurgeResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return PurgeResult(False, errors=("plugin record does not exist",))
        if record.pending_action is not PendingAction.REMOVE:
            return PurgeResult(False, errors=("plugin must be removed before purge",))
        removed = self.removed_path(plugin_id, record.installed_version)
        backups = (self.mod_root / "backups" / plugin_id).resolve()
        if not self._safe_directory(removed):
            return PurgeResult(
                False, errors=("removed plugin archive is missing or unsafe",)
            )
        if not backups.is_relative_to(self.mod_root) or backups.is_symlink():
            return PurgeResult(False, errors=("plugin backup path is unsafe",))
        staging = self.purge_staging_path(plugin_id)
        if staging.exists():
            return PurgeResult(
                False, errors=("plugin purge transaction already exists",)
            )
        staged_removed = staging / "removed"
        staged_backups = staging / "backups"
        staging.mkdir(parents=True)
        moved_backups = False
        try:
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
        except (OSError, KeyError, sqlite3.Error) as error:
            return PurgeResult(False, errors=(f"plugin purge failed: {error}",))
        warning = self._erase(staging)
        return PurgeResult(True, (warning,) if warning else ())

    def purge_backup(self, plugin_id: str, version: str) -> PurgeResult:
        try:
            plugin_version_key(version)
        except ValueError:
            return PurgeResult(False, errors=("invalid backup version",))
        record = self.registry.get(plugin_id)
        if record is None:
            return PurgeResult(False, errors=("plugin record does not exist",))
        if version == record.installed_version:
            return PurgeResult(False, errors=("cannot purge the installed version",))
        source = (self.mod_root / "backups" / plugin_id / version).resolve()
        if not self._safe_directory(source):
            return PurgeResult(False, errors=("backup version is missing or unsafe",))
        warning = self._erase(source)
        return PurgeResult(True, (warning,) if warning else ())

    def removed_path(self, plugin_id: str, version: str) -> Path:
        return (
            self.mod_root / "quarantine" / "removed" / plugin_id / version
        ).resolve()

    def purge_staging_path(self, plugin_id: str) -> Path:
        key = hashlib.sha256(plugin_id.encode("utf-8")).hexdigest()
        return (self.mod_root / "quarantine" / "purge" / key).resolve()

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
