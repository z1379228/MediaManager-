"""Transactional plugin update with retained rollback backup."""

from __future__ import annotations

import io
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

from core.plugins.dependency_graph import candidate_dependency_graph_errors
from core.plugins.installer import PluginInstaller
from core.plugins.lifecycle import (
    PluginLifecycleLockError,
    PluginLifecyclePathError,
    resolve_lifecycle_path,
)
from core.plugins.manager import PluginManager
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.version import is_newer_plugin_version


@dataclass(frozen=True, slots=True)
class UpdateResult:
    updated: bool
    plugin_id: str | None = None
    previous_version: str | None = None
    version: str | None = None
    errors: tuple[str, ...] = ()


class PluginUpdater:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        installer: PluginInstaller,
        plugin_manager: PluginManager,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.installer = installer
        self.plugin_manager = plugin_manager
        self.lifecycle_lock = plugin_manager.lifecycle_lock

    def update(
        self,
        package: Path,
        plugin_id: str,
        *,
        approved_permissions: tuple[str, ...],
        security_mode: SecurityMode,
    ) -> UpdateResult:
        try:
            with self.lifecycle_lock.hold():
                return self._update_locked(
                    package,
                    plugin_id,
                    approved_permissions=approved_permissions,
                    security_mode=security_mode,
                )
        except PluginLifecycleLockError:
            return UpdateResult(
                False,
                plugin_id,
                errors=("plugin lifecycle is busy",),
            )

    def _update_locked(
        self,
        package: Path,
        plugin_id: str,
        *,
        approved_permissions: tuple[str, ...],
        security_mode: SecurityMode,
    ) -> UpdateResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return UpdateResult(False, plugin_id, errors=("plugin is not installed",))
        if record.pending_action is not PendingAction.NONE:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                errors=("plugin is not available for update",),
            )
        prepared = self.installer._prepare_locked(package, security_mode)
        manifest = prepared.manifest
        if not prepared.valid or manifest is None:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version if manifest else None,
                prepared.errors,
            )
        if manifest.id != record.plugin_id:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("update package plugin id does not match",),
            )
        if manifest.publisher != record.publisher_id:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("update package publisher does not match",),
            )
        if not is_newer_plugin_version(manifest.version, record.installed_version):
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("update version must be newer than installed version",),
            )
        if not set(approved_permissions).issubset(manifest.permissions):
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("approved permissions exceed the update request",),
            )
        graph_errors = candidate_dependency_graph_errors(
            self.mod_root,
            self.registry,
            manifest,
        )
        if graph_errors:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                graph_errors,
            )
        try:
            installed_root = resolve_lifecycle_path(self.mod_root, "installed")
            target = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                plugin_id,
            )
            backup = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                plugin_id,
                record.installed_version,
            )
        except PluginLifecyclePathError:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("plugin update paths are unsafe",),
            )
        if not target.is_dir():
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("installed plugin directory is missing",),
            )
        if backup.exists():
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("backup for installed version already exists",),
            )
        try:
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                plugin_id,
                record.installed_version,
            )
        except (OSError, PluginLifecyclePathError):
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                ("plugin update paths are unsafe",),
            )
        disabled = self.plugin_manager.set_enabled(plugin_id, False, security_mode)
        if not disabled.successful:
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                disabled.errors,
            )
        self.registry.set_enabled(plugin_id, False)

        old_record = replace(record, enabled=False, pending_action=PendingAction.NONE)
        try:
            staging = Path(
                tempfile.mkdtemp(prefix=f".{plugin_id}-update-", dir=installed_root)
            )
            staging = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                staging.name,
            )
        except (OSError, PluginLifecyclePathError) as error:
            try:
                self.registry.upsert(old_record)
            except (KeyError, sqlite3.Error):
                pass
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                (f"plugin update failed: {error}",),
            )
        try:
            with zipfile.ZipFile(io.BytesIO(prepared.package_bytes)) as archive:
                self.installer.extract_archive(archive, staging)
            self.registry.set_pending(plugin_id, PendingAction.UPDATE)
            os.replace(target, backup)
            try:
                os.replace(staging, target)
                self.registry.upsert(
                    PluginRecord(
                        plugin_id=manifest.id,
                        installed_version=manifest.version,
                        enabled=False,
                        pending_action=PendingAction.NONE,
                        trust_level="TRUSTED_PUBLISHER",
                        publisher_id=manifest.publisher,
                        approved_permissions=approved_permissions,
                        manifest_hash=prepared.manifest_hash,
                        failure_count=record.failure_count,
                    )
                )
            except OSError, KeyError, sqlite3.Error:
                if target.exists():
                    os.replace(target, staging)
                if backup.exists():
                    os.replace(backup, target)
                raise
            return UpdateResult(
                True,
                plugin_id,
                record.installed_version,
                manifest.version,
            )
        except (
            OSError,
            KeyError,
            ValueError,
            zipfile.BadZipFile,
            sqlite3.Error,
        ) as error:
            try:
                if target.is_dir() and not backup.exists():
                    self.registry.upsert(old_record)
            except KeyError, sqlite3.Error:
                pass
            return UpdateResult(
                False,
                plugin_id,
                record.installed_version,
                manifest.version,
                (f"plugin update failed: {error}",),
            )
        finally:
            try:
                safe_staging = resolve_lifecycle_path(
                    self.mod_root,
                    "installed",
                    staging.name,
                )
            except PluginLifecyclePathError:
                pass
            else:
                shutil.rmtree(safe_staging, ignore_errors=True)
