"""Startup reconciliation for interrupted plugin filesystem transactions."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path

from core.plugins.cleanup import PluginCleanupManager
from core.plugins.manager import PluginManager
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    recovered: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class PluginTransactionRecovery:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        plugin_manager: PluginManager,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.plugin_manager = plugin_manager
        self.cleanup = PluginCleanupManager(self.mod_root, registry)

    def recover_all(self) -> RecoveryReport:
        recovered: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        records = self.registry.list_all()
        active_purge_paths = {
            self.cleanup.purge_staging_path(record.plugin_id)
            for record in records
            if record.pending_action is PendingAction.PURGE
        }
        for record in records:
            if record.pending_action in {PendingAction.NONE, PendingAction.REMOVE}:
                continue
            if record.pending_action is PendingAction.PURGE:
                error = self._recover_purge(record)
            elif record.pending_action in {
                PendingAction.UPDATE,
                PendingAction.ROLLBACK,
            }:
                error = self._recover_record(record)
            else:
                error = f"unsupported pending action {record.pending_action}"
            if error:
                errors.append(f"{record.plugin_id}: {error}")
            else:
                recovered.append(record.plugin_id)
        purge_root = self.mod_root / "quarantine" / "purge"
        if purge_root.is_dir():
            for path in purge_root.iterdir():
                if path in active_purge_paths or not path.is_dir():
                    continue
                try:
                    shutil.rmtree(path)
                except OSError as error:
                    warnings.append(
                        f"cannot finish committed purge {path.name}: {error}"
                    )
        return RecoveryReport(tuple(recovered), tuple(warnings), tuple(errors))

    def _recover_purge(self, record: PluginRecord) -> str | None:
        staging = self.cleanup.purge_staging_path(record.plugin_id)
        removed = self.cleanup.removed_path(record.plugin_id, record.installed_version)
        backups = (self.mod_root / "backups" / record.plugin_id).resolve()
        try:
            if staging.is_dir():
                staged_removed = staging / "removed"
                staged_backups = staging / "backups"
                if staged_removed.exists():
                    if removed.exists():
                        return "both staged and original removed archives exist"
                    removed.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staged_removed, removed)
                if staged_backups.exists():
                    if backups.exists():
                        return "both staged and original backup roots exist"
                    backups.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staged_backups, backups)
                shutil.rmtree(staging)
            self.registry.set_pending(record.plugin_id, PendingAction.REMOVE)
            return None
        except (OSError, KeyError, sqlite3.Error) as error:
            return f"purge recovery failed: {error}"

    def _recover_record(self, record: PluginRecord) -> str | None:
        installed = (self.mod_root / "installed" / record.plugin_id).resolve()
        old_backup = (
            self.mod_root / "backups" / record.plugin_id / record.installed_version
        ).resolve()
        if not installed.is_relative_to(self.mod_root) or not old_backup.is_relative_to(
            self.mod_root
        ):
            return "transaction paths escape the MOD root"
        old_record = replace(
            record,
            enabled=False,
            pending_action=PendingAction.NONE,
        )
        installed_version = self._directory_version(installed, record.plugin_id)
        if installed_version == record.installed_version:
            if old_backup.exists():
                return "both installed and backup contain the registered version"
            errors = self.plugin_manager.verify_directory(
                installed,
                old_record,
                allow_disabled_publisher=True,
            )
            if errors:
                return "; ".join(errors)
            try:
                self.registry.upsert(old_record)
                return None
            except (KeyError, sqlite3.Error) as error:
                return f"cannot clear pending journal: {error}"

        if not old_backup.is_dir():
            return "registered version is absent from installed and backups"
        errors = self.plugin_manager.verify_directory(
            old_backup,
            old_record,
            allow_disabled_publisher=True,
        )
        if errors:
            return "; ".join(errors)
        if installed.exists():
            if installed_version is None:
                return "interrupted replacement has an unreadable installed version"
            interrupted_backup = (
                self.mod_root / "backups" / record.plugin_id / installed_version
            ).resolve()
            if interrupted_backup.exists():
                return "backup destination for interrupted version already exists"
        else:
            interrupted_backup = None
        try:
            if interrupted_backup is not None:
                os.replace(installed, interrupted_backup)
            os.replace(old_backup, installed)
            try:
                self.registry.upsert(old_record)
            except KeyError, sqlite3.Error:
                os.replace(installed, old_backup)
                if interrupted_backup is not None:
                    os.replace(interrupted_backup, installed)
                raise
            return None
        except (OSError, KeyError, sqlite3.Error) as error:
            return f"transaction recovery failed: {error}"

    @staticmethod
    def _directory_version(path: Path, plugin_id: str) -> str | None:
        if not path.is_dir():
            return None
        try:
            raw = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            manifest = PluginManifest.from_dict(raw)
            return manifest.version if manifest.id == plugin_id else None
        except OSError, ValueError, TypeError, ManifestError:
            return None



