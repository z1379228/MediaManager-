"""Plugin discovery and process supervision."""

from __future__ import annotations

import secrets
from pathlib import Path

from core.plugins.capability_manager import CapabilityManager
from core.plugins.host_launcher import HostLauncher, PluginProcess
from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode


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

    def start_enabled(self, security_mode: SecurityMode) -> tuple[str, ...]:
        if security_mode is not SecurityMode.NORMAL:
            return ()
        started: list[str] = []
        for record in self.registry.list_enabled():
            try:
                self.start(record)
                started.append(record.plugin_id)
            except (OSError, RuntimeError, TimeoutError, ValueError, ManifestError):
                continue
        return tuple(started)

    def start(self, record: PluginRecord) -> None:
        existing = self.processes.get(record.plugin_id)
        if existing is not None:
            if existing.process.poll() is None:
                return
            self.processes.pop(record.plugin_id, None)
        plugin_root = (self.root / "installed" / record.plugin_id).resolve()
        manifest = PluginManifest.load(plugin_root / "plugin.json")
        if manifest.id != record.plugin_id or manifest.version != record.installed_version:
            raise ValueError("installed manifest does not match registry")
        if not manifest.execution_ready:
            raise ValueError("plugin manifest is not executable under protocol v2")
        if not set(record.approved_permissions).issubset(manifest.permissions):
            raise ValueError("approved capabilities exceed the signed manifest")
        process = self.launcher.launch(
            manifest.id,
            plugin_root,
            manifest.entry_point,
            secrets.token_urlsafe(24),
        )
        token = self.capability_manager.issue(
            manifest.id,
            process.process.pid,
            record.approved_permissions,
        )
        self.launcher.initialize(
            process,
            capability_token=token,
            capabilities=record.approved_permissions,
            protocol_version=manifest.runtime_protocol,
        )
        self.processes[manifest.id] = process

    def stop(self, plugin_id: str) -> None:
        plugin = self.processes.pop(plugin_id, None)
        if plugin is not None:
            self.launcher.stop(plugin)

    def stop_all(self) -> None:
        for plugin in tuple(self.processes.values()):
            self.launcher.stop(plugin)
        self.processes.clear()
