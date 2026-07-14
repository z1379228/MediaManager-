"""Transactional rollback between installed and backed-up plugin versions."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path

from core.plugins.manager import PluginManager
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.version import is_core_compatible, plugin_version_key


@dataclass(frozen=True, slots=True)
class RollbackResult:
    rolled_back: bool
    plugin_id: str | None = None
    previous_version: str | None = None
    version: str | None = None
    errors: tuple[str, ...] = ()


class PluginRollbackManager:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        plugin_manager: PluginManager,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.plugin_manager = plugin_manager

    def list_versions(self, plugin_id: str) -> tuple[str, ...]:
        root = self.mod_root / "backups" / plugin_id
        if not root.is_dir():
            return ()
        versions: list[str] = []
        for path in root.iterdir():
            if not path.is_dir():
                continue
            try:
                plugin_version_key(path.name)
            except ValueError:
                continue
            versions.append(path.name)
        return tuple(sorted(versions, key=plugin_version_key, reverse=True))

    def rollback(
        self,
        plugin_id: str,
        version: str,
        security_mode: SecurityMode,
    ) -> RollbackResult:
        if security_mode is SecurityMode.BLOCKED:
            return RollbackResult(
                False,
                plugin_id,
                errors=("plugins cannot be rolled back in BLOCKED security mode",),
            )
        record = self.registry.get(plugin_id)
        if record is None:
            return RollbackResult(False, plugin_id, errors=("plugin is not installed",))
        if record.pending_action is not PendingAction.NONE:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("plugin is not available for rollback",),
            )
        source = (self.mod_root / "backups" / plugin_id / version).resolve()
        target = (self.mod_root / "installed" / plugin_id).resolve()
        current_backup = (
            self.mod_root / "backups" / plugin_id / record.installed_version
        ).resolve()
        if not source.is_relative_to(self.mod_root) or not source.is_dir():
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("requested backup version does not exist",),
            )
        if not target.is_relative_to(self.mod_root) or not target.is_dir():
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("installed plugin directory is missing",),
            )
        if current_backup.exists():
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("backup for current version already exists",),
            )
        try:
            manifest_bytes = (source / "plugin.json").read_bytes()
            manifest = PluginManifest.from_dict(json.loads(manifest_bytes))
        except (OSError, ValueError, TypeError, ManifestError) as error:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                (f"backup manifest is invalid: {error}",),
            )
        if (
            manifest.id != plugin_id
            or manifest.version != version
            or manifest.publisher != record.publisher_id
        ):
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("backup identity does not match plugin record",),
            )
        if not is_core_compatible(
            manifest.minimum_core_version, manifest.maximum_core_version
        ):
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                ("backup is incompatible with the current core",),
            )
        missing_dependencies = tuple(
            dependency
            for dependency in manifest.dependencies
            if (dependency_record := self.registry.get(dependency)) is None
            or dependency_record.pending_action is not PendingAction.NONE
        )
        if missing_dependencies:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                (f"backup dependencies are missing: {missing_dependencies}",),
            )
        approved_permissions = tuple(
            permission
            for permission in record.approved_permissions
            if permission in manifest.permissions
        )
        candidate = PluginRecord(
            plugin_id=plugin_id,
            installed_version=version,
            enabled=False,
            pending_action=PendingAction.NONE,
            trust_level=record.trust_level,
            publisher_id=record.publisher_id,
            approved_permissions=approved_permissions,
            manifest_hash=hashlib.sha256(manifest_bytes).hexdigest(),
            failure_count=record.failure_count,
        )
        errors = self.plugin_manager.verify_directory(source, candidate)
        if errors:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                errors,
            )
        disabled = self.plugin_manager.set_enabled(plugin_id, False, security_mode)
        if not disabled.successful:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                disabled.errors,
            )
        old_record = replace(
            record,
            enabled=False,
            pending_action=PendingAction.NONE,
        )
        try:
            self.registry.set_enabled(plugin_id, False)
            self.registry.set_pending(plugin_id, PendingAction.ROLLBACK)
            os.replace(target, current_backup)
            try:
                os.replace(source, target)
                self.registry.upsert(candidate)
            except OSError, KeyError, sqlite3.Error:
                if target.exists():
                    os.replace(target, source)
                if current_backup.exists():
                    os.replace(current_backup, target)
                self.registry.upsert(old_record)
                raise
            return RollbackResult(
                True,
                plugin_id,
                record.installed_version,
                version,
            )
        except (OSError, KeyError, sqlite3.Error) as error:
            return RollbackResult(
                False,
                plugin_id,
                record.installed_version,
                version,
                (f"plugin rollback failed: {error}",),
            )
