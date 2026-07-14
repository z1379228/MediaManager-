from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from core.plugins.capability_manager import CapabilityManager
from core.plugins.host_launcher import PluginProcess
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.supervisor import PluginSupervisor


def test_supervisor_initializes_host_with_pid_bound_capabilities(
    tmp_path: Path,
) -> None:
    root = tmp_path / "mod" / "installed" / "example.plugin"
    root.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "id": "example.plugin",
        "name": "Example",
        "version": "2.0.0",
        "publisher": "example.publisher",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "2.0.0",
        "maximum_core_version": "2.9.9",
        "permissions": ["media.read"],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
        "runtime": "python-subprocess",
        "runtime_protocol": "1.0",
        "ui_descriptor": "",
    }
    (root / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    record = PluginRecord(
        "example.plugin",
        "2.0.0",
        False,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "example.publisher",
        ("media.read",),
        "manifest-hash",
    )
    registry.upsert(record)
    process = SimpleNamespace(pid=321, poll=lambda: None)
    launched = PluginProcess("example.plugin", process, Mock())
    launcher = Mock()
    launcher.launch.return_value = launched
    capabilities = CapabilityManager(b"k" * 32)
    supervisor = PluginSupervisor(
        tmp_path / "mod",
        registry,
        launcher=launcher,
        capability_manager=capabilities,
    )
    supervisor.start(record)
    token = launcher.initialize.call_args.kwargs["capability_token"]
    assert capabilities.verify(
        token,
        plugin_id="example.plugin",
        process_id=321,
        capability="media.read",
    ) is not None
    launcher.initialize.assert_called_once_with(
        launched,
        capability_token=token,
        capabilities=("media.read",),
        protocol_version="1.0",
    )
    registry.close()
