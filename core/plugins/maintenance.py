"""Transactional removal and restoration of installed plugins."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.plugins.manager import PluginManager
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PendingAction, PluginRegistry
from core.security.safe_mode import SecurityMode


@dataclass(frozen=True, slots=True)
class MaintenanceResult:
    successful: bool
    errors: tuple[str, ...] = ()


class PluginMaintenanceManager:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        plugin_manager: PluginManager,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.plugin_manager = plugin_manager

    def remove(
        self,
        plugin_id: str,
        security_mode: SecurityMode,
    ) -> MaintenanceResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return MaintenanceResult(False, ("plugin is not installed",))
        if record.pending_action is PendingAction.REMOVE:
            return MaintenanceResult(False, ("plugin is already removed",))
        dependents, dependency_errors = self._dependents_of(plugin_id)
        if dependency_errors:
            return MaintenanceResult(False, dependency_errors)
        if dependents:
            return MaintenanceResult(
                False,
                (f"plugin is required by installed plugins: {dependents}",),
            )
        disable = self.plugin_manager.set_enabled(plugin_id, False, security_mode)
        if not disable.successful:
            return MaintenanceResult(False, disable.errors)
        self.registry.set_enabled(plugin_id, False)
        source = (self.mod_root / "installed" / plugin_id).resolve()
        destination = self._removed_path(plugin_id, record.installed_version)
        if not source.is_relative_to(self.mod_root) or not source.is_dir():
            return MaintenanceResult(False, ("installed plugin directory is missing",))
        if destination.exists():
            return MaintenanceResult(False, ("removed plugin archive already exists",))
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, destination)
            try:
                self.registry.set_pending(plugin_id, PendingAction.REMOVE)
            except (KeyError, sqlite3.Error):
                os.replace(destination, source)
                raise
            return MaintenanceResult(True)
        except OSError as error:
            return MaintenanceResult(False, (f"plugin removal failed: {error}",))

    def restore(
        self,
        plugin_id: str,
        security_mode: SecurityMode,
    ) -> MaintenanceResult:
        if security_mode is SecurityMode.BLOCKED:
            return MaintenanceResult(
                False,
                ("plugins cannot be restored in BLOCKED security mode",),
            )
        record = self.registry.get(plugin_id)
        if record is None:
            return MaintenanceResult(False, ("removed plugin record is missing",))
        if record.pending_action is not PendingAction.REMOVE:
            return MaintenanceResult(False, ("plugin is not removed",))
        source = self._removed_path(plugin_id, record.installed_version)
        destination = (self.mod_root / "installed" / plugin_id).resolve()
        if not source.is_relative_to(self.mod_root) or not source.is_dir():
            return MaintenanceResult(False, ("removed plugin archive is missing",))
        if destination.exists():
            return MaintenanceResult(False, ("plugin installation target already exists",))
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, destination)
            try:
                self.registry.set_pending(plugin_id, PendingAction.NONE)
            except (KeyError, sqlite3.Error):
                os.replace(destination, source)
                raise
            return MaintenanceResult(True)
        except OSError as error:
            return MaintenanceResult(False, (f"plugin restoration failed: {error}",))

    def _dependents_of(self, plugin_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        dependents: list[str] = []
        errors: list[str] = []
        for record in self.registry.list_all():
            if (
                record.plugin_id == plugin_id
                or record.pending_action is PendingAction.REMOVE
            ):
                continue
            manifest_path = (
                self.mod_root / "installed" / record.plugin_id / "plugin.json"
            )
            try:
                manifest = PluginManifest.load(manifest_path)
                if plugin_id in manifest.dependencies:
                    dependents.append(record.plugin_id)
            except (OSError, ManifestError) as error:
                errors.append(
                    f"cannot verify dependencies for {record.plugin_id}: {error}"
                )
        return tuple(sorted(dependents)), tuple(errors)

    def _removed_path(self, plugin_id: str, version: str) -> Path:
        return (
            self.mod_root
            / "quarantine"
            / "removed"
            / plugin_id
            / version
        ).resolve()