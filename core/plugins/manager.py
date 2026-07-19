"""Security-gated plugin enable and disable operations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.plugins.dependency_graph import (
    DependencyGraphSnapshot,
    dependency_graph_errors,
    read_bounded_manifest,
    snapshot_dependency_graph,
)
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.supervisor import PluginSupervisor
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureVerifier
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION, is_core_compatible

_METADATA = frozenset({"plugin.json", "files.json", "plugin.sig"})


@dataclass(frozen=True, slots=True)
class PluginOperationResult:
    successful: bool
    errors: tuple[str, ...] = ()


class PluginManager:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        supervisor: PluginSupervisor,
        trust_store: TrustStore,
        *,
        signature_verifier: SignatureVerifier | None = None,
        allow_executable_plugins: bool = True,
        lifecycle_lock: PluginLifecycleLock | None = None,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self._supervisor = supervisor
        self.trust_store = trust_store
        self.signature_verifier = signature_verifier or SignatureVerifier()
        self.allow_executable_plugins = allow_executable_plugins
        self.lifecycle_lock = lifecycle_lock or PluginLifecycleLock(self.mod_root)

    def set_enabled(
        self,
        plugin_id: str,
        enabled: bool,
        security_mode: SecurityMode,
    ) -> PluginOperationResult:
        try:
            with self.lifecycle_lock.hold():
                return self._set_enabled_locked(plugin_id, enabled, security_mode)
        except PluginLifecycleLockError:
            return PluginOperationResult(False, ("plugin lifecycle is busy",))
        except sqlite3.Error:
            return PluginOperationResult(
                False,
                ("plugin registry operation failed",),
            )

    def start_enabled(
        self,
        security_mode: SecurityMode,
    ) -> tuple[tuple[str, PluginOperationResult], ...]:
        """Start enabled plugins once, dependency-first, with branch containment."""

        if security_mode is not SecurityMode.NORMAL:
            return ()
        try:
            with self.lifecycle_lock.hold():
                return self._start_enabled_locked(security_mode)
        except PluginLifecycleLockError:
            error = PluginOperationResult(False, ("plugin lifecycle is busy",))
        except sqlite3.Error:
            error = PluginOperationResult(
                False,
                ("plugin registry operation failed",),
            )
        try:
            plugin_ids = tuple(
                sorted(record.plugin_id for record in self.registry.list_enabled())
            )
        except sqlite3.Error:
            return ()
        return tuple((plugin_id, error) for plugin_id in plugin_ids)

    def _start_enabled_locked(
        self,
        security_mode: SecurityMode,
    ) -> tuple[tuple[str, PluginOperationResult], ...]:
        enabled = {
            record.plugin_id: record for record in self.registry.list_enabled()
        }
        if not enabled:
            return ()
        snapshot = snapshot_dependency_graph(self.mod_root, self.registry)
        graph_errors = dependency_graph_errors(snapshot)
        if graph_errors:
            rejected = PluginOperationResult(False, graph_errors)
            return tuple(
                (plugin_id, rejected) for plugin_id in sorted(enabled)
            )

        outcomes: list[tuple[str, PluginOperationResult]] = []
        failed: set[str] = set()
        visited: set[str] = set()
        for plugin_id in snapshot.dependency_order:
            if plugin_id not in enabled:
                continue
            visited.add(plugin_id)
            blockers = tuple(
                dependency_id
                for dependency_id in snapshot.transitive_dependencies(plugin_id)
                if dependency_id in failed
            )
            if blockers:
                result = PluginOperationResult(
                    False,
                    (
                        "plugin startup blocked by failed dependencies: "
                        f"{', '.join(blockers)}",
                    ),
                )
            else:
                result = self._set_enabled_locked(
                    plugin_id,
                    True,
                    security_mode,
                )
            outcomes.append((plugin_id, result))
            if not result.successful:
                failed.add(plugin_id)

        missing = tuple(sorted(set(enabled) - visited))
        if missing:
            result = PluginOperationResult(
                False,
                ("plugin dependency graph omitted an enabled plugin",),
            )
            outcomes.extend((plugin_id, result) for plugin_id in missing)
        return tuple(outcomes)

    def _set_enabled_locked(
        self,
        plugin_id: str,
        enabled: bool,
        security_mode: SecurityMode,
    ) -> PluginOperationResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return PluginOperationResult(False, ("plugin is not installed",))
        if record.pending_action is not PendingAction.NONE:
            return PluginOperationResult(
                False,
                (
                    "plugin lifecycle has pending action: "
                    f"{record.pending_action.value}",
                ),
            )
        if enabled and security_mode is not SecurityMode.NORMAL:
            return PluginOperationResult(
                False,
                ("plugins can only be enabled in NORMAL security mode",),
            )
        if enabled:
            try:
                self.trust_store.load()
            except (OSError, TypeError, ValueError):
                return self._reject_enable(
                    record,
                    ("publisher trust store could not be refreshed",),
                )
            publisher = self.trust_store.get(record.publisher_id)
            if publisher is None:
                return self._reject_enable(
                    record,
                    ("publisher is no longer trusted",),
                )
        dependency_snapshot = snapshot_dependency_graph(
            self.mod_root,
            self.registry,
        )
        graph_errors = dependency_graph_errors(dependency_snapshot)
        if not enabled:
            if graph_errors:
                return self._contain_invalid_graph_disable(record, graph_errors)
            enabled_dependents = self._enabled_transitive_dependents(
                dependency_snapshot,
                record.plugin_id,
            )
            if enabled_dependents:
                return PluginOperationResult(
                    False,
                    (
                        "plugin has enabled transitive dependents: "
                        f"{', '.join(enabled_dependents)}",
                    ),
                )
            return self._disable_locked(record)
        if graph_errors:
            return PluginOperationResult(False, graph_errors)
        dependency_errors = self._dependency_readiness_errors(
            dependency_snapshot,
            record.plugin_id,
        )
        if dependency_errors:
            return PluginOperationResult(False, dependency_errors)
        errors = self.verify_directory(
            self.mod_root / "installed" / record.plugin_id, record
        )
        if errors:
            return self._reject_enable(record, errors)
        try:
            manifest = PluginManifest.from_dict(
                json.loads(
                    read_bounded_manifest(
                        self.mod_root
                        / "installed"
                        / record.plugin_id
                        / "plugin.json"
                    )
                )
            )
            if not is_core_compatible(
                manifest.minimum_core_version,
                manifest.maximum_core_version,
            ):
                return self._reject_enable(
                    record,
                    (f"plugin is incompatible with core {CORE_VERSION}",),
                )
            if manifest.executable and not manifest.execution_ready:
                return PluginOperationResult(
                    False,
                    ("legacy executable MOD must be repackaged with manifest v2",),
                )
            if manifest.executable and not self.allow_executable_plugins:
                return PluginOperationResult(
                    False,
                    (
                        "external executable MOD runtime is disabled until "
                        "OS-level isolation is available",
                    ),
                )
            if not set(record.approved_permissions).issubset(manifest.permissions):
                return PluginOperationResult(
                    False, ("approved capabilities exceed the signed manifest",)
                )
        except (OSError, RuntimeError, TimeoutError, ValueError, ManifestError) as error:
            return self._reject_enable(
                record,
                (f"plugin failed to start: {error}",),
            )
        return self._enable_locked(record, manifest)

    def _contain_invalid_graph_disable(
        self,
        record: PluginRecord,
        graph_errors: tuple[str, ...],
    ) -> PluginOperationResult:
        if not self.registry.claim_lifecycle(record, PendingAction.DISABLE):
            return PluginOperationResult(
                False,
                graph_errors + self._lifecycle_conflict().errors,
            )
        try:
            self._supervisor.stop(record.plugin_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            containment_error = (
                f"plugin runtime containment could not be confirmed: {error}; "
                "dependency safety is unverified; DISABLE journal remains and "
                "recovery is required"
            )
        else:
            containment_error = (
                "plugin runtime stopped, but dependency safety could not be "
                "verified; DISABLE journal remains and recovery is required"
            )
        return PluginOperationResult(
            False,
            graph_errors + (containment_error,),
        )

    def _enable_locked(
        self,
        record: PluginRecord,
        manifest: PluginManifest,
    ) -> PluginOperationResult:
        if not self.registry.claim_lifecycle(record, PendingAction.ENABLE):
            return self._lifecycle_conflict()
        try:
            if manifest.executable:
                self._supervisor._start_claimed(record)
        except (OSError, RuntimeError, TimeoutError, ValueError, ManifestError) as error:
            recovery_error = self._rollback_failed_enable(record)
            errors = [f"plugin failed to start: {error}"]
            if recovery_error:
                errors.append(recovery_error)
            return PluginOperationResult(False, tuple(errors))
        try:
            finalized = self.registry.finish_lifecycle(
                record,
                PendingAction.ENABLE,
                enabled=True,
            )
        except sqlite3.Error:
            rollback_error = self._stop_after_finalize_failure(
                record.plugin_id,
                manifest.executable,
            )
            return self._finalization_failure("ENABLE", rollback_error)
        if not finalized:
            rollback_error = self._stop_after_finalize_failure(
                record.plugin_id,
                manifest.executable,
            )
            return self._finalization_failure("ENABLE", rollback_error)
        return PluginOperationResult(True)

    def _disable_locked(self, record: PluginRecord) -> PluginOperationResult:
        if not self.registry.claim_lifecycle(record, PendingAction.DISABLE):
            return self._lifecycle_conflict()
        try:
            self._supervisor.stop(record.plugin_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return PluginOperationResult(
                False,
                (
                    f"plugin failed to stop: {error}; "
                    "DISABLE rollback incomplete; recovery is required",
                ),
            )
        try:
            finalized = self.registry.finish_lifecycle(
                record,
                PendingAction.DISABLE,
                enabled=False,
            )
        except sqlite3.Error:
            return self._finalization_failure("DISABLE", None)
        if not finalized:
            return self._finalization_failure("DISABLE", None)
        return PluginOperationResult(True)

    def _reject_enable(
        self,
        record: PluginRecord,
        errors: tuple[str, ...],
    ) -> PluginOperationResult:
        if not record.enabled:
            return PluginOperationResult(False, errors)
        disabled = self._disable_locked(record)
        return PluginOperationResult(False, errors + disabled.errors)

    def _rollback_failed_enable(self, record: PluginRecord) -> str:
        try:
            self._supervisor.stop(record.plugin_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return (
                "plugin start rollback incomplete: "
                f"plugin failed to stop: {error}; ENABLE recovery is required"
            )
        try:
            finalized = self.registry.finish_lifecycle(
                record,
                PendingAction.ENABLE,
                enabled=False,
            )
        except sqlite3.Error:
            return (
                "plugin start rollback incomplete: runtime is not running, but "
                "ENABLE journal state is unconfirmed"
            )
        if not finalized:
            return (
                "plugin start rollback incomplete: lifecycle state conflicted; "
                "ENABLE recovery is required"
            )
        return "plugin start rollback complete"

    def _stop_after_finalize_failure(
        self,
        plugin_id: str,
        executable: bool,
    ) -> str | None:
        if not executable:
            return None
        try:
            self._supervisor.stop(plugin_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return f"plugin failed to stop: {error}"
        return None

    def _stop_runtime_for_recovery(self, plugin_id: str) -> None:
        """Contain one runtime while a recovery caller holds the lifecycle lock."""

        self._supervisor.stop(plugin_id)

    def _stop_all_runtimes_for_trust_change(self) -> None:
        """Contain every runtime before a trust mutation is finalized."""

        self._supervisor.stop_all()

    def _contain_runtimes_for_trust_revocation(
        self,
        records: tuple[PluginRecord, ...],
    ) -> tuple[str, ...]:
        """Stop every runtime, then disable revoked records without graph bypass risk."""

        try:
            self._supervisor.stop_all()
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return (f"emergency plugin shutdown could not be confirmed: {error}",)
        errors: list[str] = []
        for expected in records:
            try:
                current = self.registry.get(expected.plugin_id)
            except sqlite3.Error:
                errors.append(
                    f"{expected.plugin_id}: plugin registry state could not be read"
                )
                continue
            if current is None or current.publisher_id != expected.publisher_id:
                errors.append(
                    f"{expected.plugin_id}: plugin registry identity changed"
                )
                continue
            if not current.enabled:
                continue
            if current.pending_action is not PendingAction.NONE:
                errors.append(
                    f"{current.plugin_id}: plugin lifecycle has pending action: "
                    f"{current.pending_action.value}"
                )
                continue
            result = self._disable_locked(current)
            errors.extend(
                f"{current.plugin_id}: {error}" for error in result.errors
            )
        return tuple(errors)

    @staticmethod
    def _lifecycle_conflict() -> PluginOperationResult:
        return PluginOperationResult(
            False,
            ("plugin lifecycle state changed; retry from a fresh snapshot",),
        )

    @staticmethod
    def _finalization_failure(
        action: str,
        rollback_error: str | None,
    ) -> PluginOperationResult:
        rollback_detail = (
            f"{rollback_error}; {action} journal state is unconfirmed"
            if rollback_error
            else f"runtime is not running; {action} journal state is unconfirmed"
        )
        return PluginOperationResult(
            False,
            (
                f"plugin {action} finalization failed; recovery is required",
                f"plugin {action} rollback incomplete: {rollback_detail}",
            ),
        )

    def _dependency_readiness_errors(
        self,
        snapshot: DependencyGraphSnapshot,
        plugin_id: str,
    ) -> tuple[str, ...]:
        for dependency_id in snapshot.transitive_dependencies(plugin_id):
            dependency = self.registry.get(dependency_id)
            if dependency is None:
                return (
                    f"plugin dependency is missing: {dependency_id}",
                )
            if dependency.pending_action is not PendingAction.NONE:
                return (
                    "plugin dependency has pending action: "
                    f"{dependency_id} ({dependency.pending_action.value})",
                )
            if not dependency.enabled:
                return (
                    f"plugin dependency is disabled: {dependency_id}",
                )
            errors = self.verify_directory(
                self.mod_root / "installed" / dependency_id,
                dependency,
            )
            if errors:
                return tuple(
                    f"plugin dependency {dependency_id} verification failed: "
                    f"{error}"
                    for error in errors
                )
        return ()

    @staticmethod
    def _enabled_transitive_dependents(
        snapshot: DependencyGraphSnapshot,
        plugin_id: str,
    ) -> tuple[str, ...]:
        nodes = {node.plugin_id: node for node in snapshot.nodes}
        return tuple(
            dependent_id
            for dependent_id in snapshot.transitive_dependents(plugin_id)
            if nodes[dependent_id].enabled
        )

    def verify_directory(
        self,
        root: Path,
        record: PluginRecord,
        *,
        allow_disabled_publisher: bool = False,
        refresh_trust_store: bool = False,
    ) -> tuple[str, ...]:
        if refresh_trust_store:
            try:
                self.trust_store.load()
            except (OSError, TypeError, ValueError):
                return ("publisher trust store could not be refreshed",)
        publisher = (
            self.trust_store.find(record.publisher_id)
            if allow_disabled_publisher
            else self.trust_store.get(record.publisher_id)
        )
        if publisher is None:
            return ("publisher is no longer trusted",)
        root = root.resolve()
        if not root.is_relative_to(self.mod_root) or not root.is_dir():
            return ("installed plugin directory is missing or unsafe",)
        try:
            manifest_bytes = read_bounded_manifest(root / "plugin.json")
            files_bytes = (root / "files.json").read_bytes()
            signature_bytes = (root / "plugin.sig").read_bytes()
            if hashlib.sha256(manifest_bytes).hexdigest() != record.manifest_hash:
                return ("installed plugin manifest was modified",)
            signature = self.signature_verifier.verify(
                signed_payload(manifest_bytes, files_bytes),
                signature_bytes,
                publisher.public_key,
            )
            if not signature.valid:
                return (f"installed plugin signature rejected: {signature.reason}",)
            manifest = PluginManifest.from_dict(json.loads(manifest_bytes))
            if (
                manifest.id != record.plugin_id
                or manifest.version != record.installed_version
            ):
                return ("installed plugin identity does not match registry",)
            files = json.loads(files_bytes)
            declared = files.get("files") if isinstance(files, dict) else None
            if not isinstance(declared, dict):
                return ("installed files manifest is invalid",)
            errors: list[str] = []
            declared_names = {str(name).replace("\\", "/") for name in declared}
            actual_names: set[str] = set()
            for path in root.rglob("*"):
                relative_name = path.relative_to(root).as_posix()
                if path.is_symlink():
                    errors.append(
                        f"installed symbolic link is forbidden: {relative_name}"
                    )
                elif path.is_file():
                    actual_names.add(relative_name)
            unexpected = actual_names - declared_names - _METADATA
            if unexpected:
                errors.append(f"undeclared installed files: {sorted(unexpected)}")
            missing_metadata = _METADATA - actual_names
            if missing_metadata:
                errors.append(f"installed metadata missing: {sorted(missing_metadata)}")
            for name, expected in declared.items():
                relative = PurePosixPath(str(name).replace("\\", "/"))
                target = root.joinpath(*relative.parts).resolve()
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not target.is_relative_to(root)
                    or not target.is_file()
                    or target.is_symlink()
                ):
                    errors.append(f"installed file is missing or unsafe: {name}")
                    continue
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual.lower() != str(expected).removeprefix("sha256:").lower():
                    errors.append(f"installed file hash mismatch: {name}")
            return tuple(errors)
        except (OSError, ValueError, TypeError, ManifestError) as error:
            return (f"installed plugin verification failed: {error}",)
