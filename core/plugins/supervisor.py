"""Plugin discovery and process supervision."""

from __future__ import annotations

import secrets
import subprocess
import threading
from dataclasses import replace
from pathlib import Path

from core.plugins.capability_manager import CapabilityManager
from core.plugins.host_launcher import HostLauncher, PluginLaunchError, PluginProcess
from core.plugins.manifest import PluginManifest
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry


class PluginSupervisor:
    def __init__(
        self,
        root: Path,
        registry: PluginRegistry,
        launcher: HostLauncher | None = None,
        capability_manager: CapabilityManager | None = None,
    ) -> None:
        self.root, self.registry = root, registry
        self.launcher = launcher or HostLauncher()
        self.capability_manager = capability_manager or CapabilityManager()
        self.processes: dict[str, PluginProcess] = {}
        self._capability_tokens: dict[str, str] = {}
        self._ready: set[str] = set()
        self._ownership_lock = threading.RLock()

    def _start_claimed(self, record: PluginRecord) -> None:
        """Start only the exact registry identity claimed by PluginManager."""

        with self._ownership_lock:
            if record.pending_action is not PendingAction.NONE:
                raise RuntimeError("plugin start requires a pre-claim registry snapshot")
            claimed = self.registry.get(record.plugin_id)
            if claimed != replace(record, pending_action=PendingAction.ENABLE):
                raise RuntimeError("plugin ENABLE lifecycle claim is missing or stale")
            self._start_locked(record)

    def _start_locked(self, record: PluginRecord) -> None:
        existing = self.processes.get(record.plugin_id)
        if existing is not None:
            if existing.process.poll() is None:
                if record.plugin_id in self._ready:
                    return
                raise RuntimeError("plugin process cleanup is pending")
            self.stop(record.plugin_id)
        plugin_root = (self.root / "installed" / record.plugin_id).resolve()
        manifest = PluginManifest.load(plugin_root / "plugin.json")
        if manifest.id != record.plugin_id or manifest.version != record.installed_version:
            raise ValueError("installed manifest does not match registry")
        if not manifest.execution_ready:
            raise ValueError("plugin manifest is not executable under protocol v2")
        if not set(record.approved_permissions).issubset(manifest.permissions):
            raise ValueError("approved capabilities exceed the signed manifest")
        try:
            process = self.launcher.launch(
                manifest.id,
                plugin_root,
                manifest.entry_point,
                secrets.token_urlsafe(24),
            )
        except PluginLaunchError as error:
            self.processes[manifest.id] = error.plugin_process
            raise
        self.processes[manifest.id] = process
        try:
            token = self.capability_manager.issue(
                manifest.id,
                process.process.pid,
                record.approved_permissions,
            )
            self._capability_tokens[manifest.id] = token
            self.launcher.initialize(
                process,
                capability_token=token,
                capabilities=record.approved_permissions,
                protocol_version=manifest.runtime_protocol,
            )
        except Exception as primary_error:
            try:
                self._stop_locked(manifest.id)
            except Exception as cleanup_error:
                raise RuntimeError(
                    "plugin initialization failed: "
                    f"{primary_error}; cleanup could not be confirmed: "
                    f"{cleanup_error}"
                ) from primary_error
            raise
        self._ready.add(manifest.id)

    def stop(self, plugin_id: str) -> None:
        with self._ownership_lock:
            self._stop_locked(plugin_id)

    def _stop_locked(self, plugin_id: str) -> None:
        plugin = self.processes.get(plugin_id)
        if plugin is None:
            return
        self._ready.discard(plugin_id)
        token = self._capability_tokens.pop(plugin_id, None)
        if token is not None:
            self.capability_manager.revoke(token)
        try:
            self.launcher.stop(plugin)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            raise RuntimeError(
                f"plugin process stop could not be confirmed: {error}"
            ) from error
        if self.processes.get(plugin_id) is plugin:
            self.processes.pop(plugin_id, None)

    def stop_all(self) -> None:
        with self._ownership_lock:
            failures: list[str] = []
            for plugin_id in tuple(self.processes):
                try:
                    self._stop_locked(plugin_id)
                except (OSError, RuntimeError, TimeoutError, ValueError):
                    failures.append(plugin_id)
        if failures:
            failed = ", ".join(sorted(failures))
            raise RuntimeError(
                f"plugin shutdown could not be confirmed: {failed}"
            )
