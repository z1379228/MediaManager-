"""Startup reconciliation for interrupted plugin filesystem transactions."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path

from core.plugins.cleanup import PluginCleanupManager
from core.plugins.dependency_graph import (
    DependencyGraphSnapshot,
    dependency_graph_errors,
    read_bounded_manifest,
    snapshot_dependency_graph,
)
from core.plugins.lifecycle import PluginLifecycleLockError
from core.plugins.lifecycle import PluginLifecyclePathError, resolve_lifecycle_path
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
        self.lifecycle_lock = plugin_manager.lifecycle_lock
        self.cleanup = PluginCleanupManager(
            self.mod_root,
            registry,
            lifecycle_lock=self.lifecycle_lock,
        )

    def recover_all(self) -> RecoveryReport:
        try:
            with self.lifecycle_lock.hold():
                return self._recover_all_locked()
        except PluginLifecycleLockError:
            return RecoveryReport(errors=("plugin lifecycle is busy",))
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            return RecoveryReport(
                errors=(f"plugin transaction recovery failed: {error}",)
            )

    def _recover_all_locked(self) -> RecoveryReport:
        recovered: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        records = self.registry.list_all()
        active_purge_paths = {
            self.cleanup.purge_staging_path(record.plugin_id)
            for record in records
            if record.pending_action is PendingAction.PURGE
        }
        transaction_records = tuple(
            record
            for record in records
            if record.pending_action
            in {PendingAction.UPDATE, PendingAction.ROLLBACK}
        )
        for record in records:
            if record.pending_action is PendingAction.REMOVE:
                restored_layout, error = self._recover_interrupted_restore(record)
                if error:
                    errors.append(f"{record.plugin_id}: {error}")
                elif restored_layout:
                    recovered.append(record.plugin_id)
                continue
            if record.pending_action in {
                PendingAction.NONE,
                PendingAction.ENABLE,
                PendingAction.DISABLE,
                PendingAction.UPDATE,
                PendingAction.ROLLBACK,
            }:
                continue
            if record.pending_action is PendingAction.PURGE:
                error = self._recover_purge(record)
            else:
                error = f"unsupported pending action {record.pending_action}"
            if error:
                errors.append(f"{record.plugin_id}: {error}")
            else:
                recovered.append(record.plugin_id)

        recovery_order, recovery_snapshot, plan_errors = (
            self._plan_transaction_recovery(transaction_records)
        )
        errors.extend(plan_errors)
        failed_transactions: set[str] = set()
        if recovery_snapshot is not None:
            for record in recovery_order:
                blockers = tuple(
                    dependency_id
                    for dependency_id in recovery_snapshot.transitive_dependencies(
                        record.plugin_id
                    )
                    if dependency_id in failed_transactions
                )
                if blockers:
                    errors.append(
                        f"{record.plugin_id}: transaction recovery blocked by "
                        f"failed dependencies: {', '.join(blockers)}"
                    )
                    failed_transactions.add(record.plugin_id)
                    continue
                error = self._recover_record(record)
                if error:
                    errors.append(f"{record.plugin_id}: {error}")
                    failed_transactions.add(record.plugin_id)
                else:
                    recovered.append(record.plugin_id)

        refreshed_records = self.registry.list_all()
        toggle_records = {
            record.plugin_id: record
            for record in refreshed_records
            if record.pending_action
            in {PendingAction.ENABLE, PendingAction.DISABLE}
        }
        if toggle_records:
            snapshot = snapshot_dependency_graph(self.mod_root, self.registry)
            graph_errors = dependency_graph_errors(snapshot)
            if graph_errors:
                errors.extend(graph_errors)
                toggle_order = ()
            else:
                toggle_order = tuple(
                    plugin_id
                    for plugin_id in reversed(snapshot.dependency_order)
                    if plugin_id in toggle_records
                )
                toggle_order += tuple(
                    sorted(set(toggle_records) - set(toggle_order), reverse=True)
                )
            failed_stops: set[str] = set()
            for plugin_id in toggle_order:
                record = toggle_records[plugin_id]
                live_dependents = tuple(
                    failed_plugin_id
                    for failed_plugin_id in sorted(failed_stops)
                    if plugin_id
                    in snapshot.transitive_dependencies(failed_plugin_id)
                )
                if live_dependents:
                    errors.append(
                        f"{plugin_id}: lifecycle recovery blocked by live "
                        "dependents: " + ", ".join(live_dependents)
                    )
                    continue
                error, stop_unconfirmed = self._recover_toggle(record)
                if error:
                    errors.append(f"{plugin_id}: {error}")
                    if stop_unconfirmed:
                        failed_stops.add(plugin_id)
                else:
                    recovered.append(plugin_id)
        try:
            purge_root = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "purge",
            )
        except PluginLifecyclePathError:
            warnings.append("cannot finish committed purges: unsafe purge root")
        else:
            if purge_root.is_dir():
                for entry in purge_root.iterdir():
                    try:
                        path = resolve_lifecycle_path(
                            self.mod_root,
                            "quarantine",
                            "purge",
                            entry.name,
                        )
                    except PluginLifecyclePathError:
                        warnings.append(
                            f"cannot finish committed purge {entry.name}: "
                            "unsafe purge path"
                        )
                        continue
                    if path in active_purge_paths or not path.is_dir():
                        continue
                    try:
                        shutil.rmtree(path)
                    except OSError as error:
                        warnings.append(
                            f"cannot finish committed purge {path.name}: {error}"
                        )
        return RecoveryReport(tuple(recovered), tuple(warnings), tuple(errors))

    def _plan_transaction_recovery(
        self,
        records: tuple[PluginRecord, ...],
    ) -> tuple[
        tuple[PluginRecord, ...],
        DependencyGraphSnapshot | None,
        tuple[str, ...],
    ]:
        if not records:
            return (), None, ()
        candidates: list[PluginManifest] = []
        by_id: dict[str, PluginRecord] = {}
        errors: list[str] = []
        for record in records:
            source, source_error = self._registered_recovery_source(record)
            if source_error:
                errors.append(f"{record.plugin_id}: {source_error}")
                continue
            assert source is not None
            candidate_record = replace(
                record,
                enabled=False,
                pending_action=PendingAction.NONE,
            )
            verification_errors = self.plugin_manager.verify_directory(
                source,
                candidate_record,
                allow_disabled_publisher=True,
                refresh_trust_store=True,
            )
            if verification_errors:
                errors.extend(
                    f"{record.plugin_id}: {error}"
                    for error in verification_errors
                )
                continue
            try:
                manifest = PluginManifest.from_dict(
                    json.loads(read_bounded_manifest(source / "plugin.json"))
                )
            except (OSError, TypeError, ValueError, ManifestError) as error:
                errors.append(
                    f"{record.plugin_id}: registered recovery manifest is "
                    f"invalid: {error}"
                )
                continue
            candidates.append(manifest)
            by_id[record.plugin_id] = record
        if errors:
            return (), None, tuple(errors)

        snapshot = snapshot_dependency_graph(self.mod_root, self.registry)
        recovery_snapshot = snapshot.with_verified_recovery_candidates(
            tuple(candidates)
        )
        graph_errors = dependency_graph_errors(recovery_snapshot)
        if graph_errors:
            return (), None, graph_errors
        order = tuple(
            by_id[plugin_id]
            for plugin_id in recovery_snapshot.dependency_order
            if plugin_id in by_id
        )
        missing = tuple(sorted(set(by_id) - {record.plugin_id for record in order}))
        if missing:
            return (
                (),
                None,
                tuple(
                    f"{plugin_id}: recovery graph omitted a transaction record"
                    for plugin_id in missing
                ),
            )
        return order, recovery_snapshot, ()

    def _registered_recovery_source(
        self,
        record: PluginRecord,
    ) -> tuple[Path | None, str | None]:
        try:
            installed = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                record.plugin_id,
            )
            old_backup = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                record.plugin_id,
                record.installed_version,
            )
        except PluginLifecyclePathError:
            return None, "transaction paths escape the MOD root"
        installed_version = self._directory_version(installed, record.plugin_id)
        if installed_version == record.installed_version:
            if old_backup.exists():
                return None, "both installed and backup contain the registered version"
            return installed, None
        if not old_backup.is_dir():
            return None, "registered version is absent from installed and backups"
        return old_backup, None

    def _recover_toggle(
        self,
        record: PluginRecord,
    ) -> tuple[str | None, bool]:
        try:
            self.plugin_manager._stop_runtime_for_recovery(record.plugin_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return (
                f"{record.pending_action.value} runtime stop could not be "
                f"confirmed; lifecycle journal remains: {error}",
                True,
            )
        try:
            finalized = self.registry.finish_lifecycle(
                record,
                record.pending_action,
                enabled=False,
            )
        except sqlite3.Error as error:
            return (
                f"runtime stopped, but {record.pending_action.value} lifecycle "
                f"journal could not be cleared: {error}",
                False,
            )
        if not finalized:
            return (
                f"runtime stopped, but {record.pending_action.value} lifecycle "
                "state changed; journal remains",
                False,
            )
        return None, False

    def _recover_purge(self, record: PluginRecord) -> str | None:
        staging_key = self.cleanup.purge_staging_key(record.plugin_id)
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
            removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "removed",
                record.plugin_id,
                record.installed_version,
            )
            backups = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                record.plugin_id,
            )
        except PluginLifecyclePathError:
            return "purge recovery path is unsafe"
        try:
            if staging.is_dir():
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
                staging = resolve_lifecycle_path(
                    self.mod_root,
                    "quarantine",
                    "purge",
                    staging_key,
                )
                shutil.rmtree(staging)
            self.registry.set_pending(record.plugin_id, PendingAction.REMOVE)
            return None
        except (
            OSError,
            KeyError,
            sqlite3.Error,
            PluginLifecyclePathError,
        ) as error:
            return f"purge recovery failed: {error}"

    def _recover_record(self, record: PluginRecord) -> str | None:
        try:
            installed = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                record.plugin_id,
            )
            old_backup = resolve_lifecycle_path(
                self.mod_root,
                "backups",
                record.plugin_id,
                record.installed_version,
            )
        except PluginLifecyclePathError:
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
                refresh_trust_store=True,
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
            refresh_trust_store=True,
        )
        if errors:
            return "; ".join(errors)
        if installed.exists():
            if installed_version is None:
                return "interrupted replacement has an unreadable installed version"
            try:
                interrupted_backup = resolve_lifecycle_path(
                    self.mod_root,
                    "backups",
                    record.plugin_id,
                    installed_version,
                )
            except PluginLifecyclePathError:
                return "transaction paths escape the MOD root"
            if interrupted_backup.exists():
                return "backup destination for interrupted version already exists"
        else:
            interrupted_backup = None
        try:
            if interrupted_backup is not None:
                os.replace(installed, interrupted_backup)
            os.replace(old_backup, installed)
            post_move_errors = self.plugin_manager.verify_directory(
                installed,
                old_record,
                allow_disabled_publisher=True,
                refresh_trust_store=True,
            )
            if post_move_errors:
                os.replace(installed, old_backup)
                if interrupted_backup is not None:
                    os.replace(interrupted_backup, installed)
                return "; ".join(post_move_errors)
            try:
                self.registry.upsert(old_record)
            except (KeyError, sqlite3.Error):
                os.replace(installed, old_backup)
                if interrupted_backup is not None:
                    os.replace(interrupted_backup, installed)
                raise
            return None
        except (OSError, KeyError, sqlite3.Error) as error:
            return f"transaction recovery failed: {error}"

    def _recover_interrupted_restore(
        self,
        record: PluginRecord,
    ) -> tuple[bool, str | None]:
        """Return a stranded restore candidate to quarantine, keeping REMOVE."""

        try:
            installed = resolve_lifecycle_path(
                self.mod_root,
                "installed",
                record.plugin_id,
            )
            removed = resolve_lifecycle_path(
                self.mod_root,
                "quarantine",
                "removed",
                record.plugin_id,
                record.installed_version,
            )
        except PluginLifecyclePathError:
            return False, "transaction paths escape the MOD root"
        if removed.exists():
            if installed.exists():
                return False, "both removed archive and installed directory exist"
            return False, None
        if not installed.exists():
            return False, None
        if self._directory_version(installed, record.plugin_id) != record.installed_version:
            return False, "stranded restore identity does not match the registry"
        try:
            removed.parent.mkdir(parents=True, exist_ok=True)
            os.replace(installed, removed)
        except OSError as error:
            return False, f"stranded restore containment failed: {error}"
        return True, None

    @staticmethod
    def _directory_version(path: Path, plugin_id: str) -> str | None:
        if not path.is_dir():
            return None
        try:
            raw = json.loads(read_bounded_manifest(path / "plugin.json"))
            if not isinstance(raw, dict):
                return None
            manifest = PluginManifest.from_dict(raw)
            return manifest.version if manifest.id == plugin_id else None
        except (OSError, ValueError, TypeError, ManifestError):
            return None



