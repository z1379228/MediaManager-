"""Transactional removal and restoration of installed plugins."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path

from core.plugins.dependency_graph import (
    candidate_dependency_graph_errors,
    read_bounded_manifest,
)
from core.plugins.lifecycle import (
    PluginLifecycleLockError,
    PluginLifecyclePathError,
    resolve_lifecycle_path,
)
from core.plugins.manager import PluginManager
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PendingAction, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.version import CORE_VERSION, is_core_compatible


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
        self.lifecycle_lock = plugin_manager.lifecycle_lock

    def remove(
        self,
        plugin_id: str,
        security_mode: SecurityMode,
    ) -> MaintenanceResult:
        try:
            with self.lifecycle_lock.hold():
                return self._remove_locked(plugin_id, security_mode)
        except PluginLifecycleLockError:
            return MaintenanceResult(False, ("plugin lifecycle is busy",))

    def _remove_locked(
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
        try:
            source = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                plugin_id,
            )
            destination = self._removed_path(plugin_id, record.installed_version)
        except PluginLifecyclePathError:
            return MaintenanceResult(False, ("plugin lifecycle path is unsafe",))
        if not source.is_dir():
            return MaintenanceResult(False, ("installed plugin directory is missing",))
        if destination.exists():
            return MaintenanceResult(False, ("removed plugin archive already exists",))
        disable = self.plugin_manager.set_enabled(plugin_id, False, security_mode)
        if not disable.successful:
            return MaintenanceResult(False, disable.errors)
        self.registry.set_enabled(plugin_id, False)
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
        try:
            with self.lifecycle_lock.hold():
                return self._restore_locked(plugin_id, security_mode)
        except PluginLifecycleLockError:
            return MaintenanceResult(False, ("plugin lifecycle is busy",))

    def _restore_locked(
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
        try:
            source = self._removed_path(plugin_id, record.installed_version)
            destination = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                plugin_id,
            )
        except PluginLifecyclePathError:
            return MaintenanceResult(False, ("plugin lifecycle path is unsafe",))
        if not source.is_dir():
            return MaintenanceResult(False, ("removed plugin archive is missing",))
        if destination.exists():
            return MaintenanceResult(False, ("plugin installation target already exists",))
        candidate = replace(
            record,
            enabled=False,
            pending_action=PendingAction.NONE,
        )
        errors = self.plugin_manager.verify_directory(
            source,
            candidate,
            refresh_trust_store=True,
        )
        if errors:
            return MaintenanceResult(False, errors)
        try:
            manifest = PluginManifest.from_dict(
                json.loads(read_bounded_manifest(source / "plugin.json"))
            )
        except (OSError, TypeError, ValueError, ManifestError) as error:
            return MaintenanceResult(
                False,
                (f"removed plugin manifest is invalid: {error}",),
            )
        if not is_core_compatible(
            manifest.minimum_core_version,
            manifest.maximum_core_version,
        ):
            return MaintenanceResult(
                False,
                (f"plugin is incompatible with core {CORE_VERSION}",),
            )
        graph_errors = candidate_dependency_graph_errors(
            self.mod_root,
            self.registry,
            manifest,
        )
        if graph_errors:
            return MaintenanceResult(False, graph_errors)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, destination)
            post_move_errors = self.plugin_manager.verify_directory(
                destination,
                candidate,
                refresh_trust_store=True,
            )
            if post_move_errors:
                os.replace(destination, source)
                return MaintenanceResult(False, post_move_errors)
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
        return resolve_lifecycle_path(
            self.mod_root,
            "quarantine",
            "removed",
            plugin_id,
            version,
        )
