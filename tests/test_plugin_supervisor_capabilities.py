from __future__ import annotations

import json
import threading
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.plugins.capability_manager import CapabilityManager
from core.plugins.host_launcher import PluginLaunchError, PluginProcess
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.supervisor import PluginSupervisor


def _setup_supervisor(
    tmp_path: Path,
    *,
    plugin_id: str = "example.plugin",
    process_id: int = 321,
) -> tuple[PluginSupervisor, PluginRecord, Mock, PluginProcess]:
    root = tmp_path / "mod" / "installed" / plugin_id
    root.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "id": plugin_id,
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
    record = PluginRecord(
        plugin_id,
        "2.0.0",
        False,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "example.publisher",
        ("media.read",),
        "manifest-hash",
    )
    process = SimpleNamespace(pid=process_id, poll=lambda: None)
    launched = PluginProcess(plugin_id, process, Mock())
    launcher = Mock()
    launcher.launch.return_value = launched
    registry = Mock(spec=PluginRegistry)
    registry.get.return_value = replace(
        record,
        pending_action=PendingAction.ENABLE,
    )
    supervisor = PluginSupervisor(
        tmp_path / "mod",
        registry,
        launcher=launcher,
        capability_manager=CapabilityManager(b"k" * 32),
    )
    return supervisor, record, launcher, launched


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
    registry.upsert(replace(record, pending_action=PendingAction.ENABLE))
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
    supervisor._start_claimed(record)
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


def test_supervisor_rejects_missing_or_stale_enable_claim(tmp_path: Path) -> None:
    supervisor, record, launcher, _ = _setup_supervisor(tmp_path)
    assert not hasattr(supervisor, "start")
    assert not hasattr(supervisor, "start_enabled")
    for claimed in (
        None,
        record,
        replace(
            record,
            pending_action=PendingAction.ENABLE,
            manifest_hash="stale-manifest-hash",
        ),
    ):
        supervisor.registry.get.return_value = claimed
        with pytest.raises(RuntimeError, match="claim is missing or stale"):
            supervisor._start_claimed(record)

    claimed = replace(record, pending_action=PendingAction.ENABLE)
    supervisor.registry.get.return_value = claimed
    with pytest.raises(RuntimeError, match="pre-claim registry snapshot"):
        supervisor._start_claimed(claimed)

    launcher.launch.assert_not_called()


def test_supervisor_stops_launched_host_when_initialize_fails(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    launcher.initialize.side_effect = RuntimeError("initialization rejected")

    with pytest.raises(RuntimeError, match="initialization rejected"):
        supervisor._start_claimed(record)

    launcher.stop.assert_called_once_with(launched)
    assert record.plugin_id not in supervisor.processes
    token = launcher.initialize.call_args.kwargs["capability_token"]
    assert supervisor.capability_manager.verify(
        token,
        plugin_id=record.plugin_id,
        process_id=launched.process.pid,
        capability="media.read",
    ) is None


def test_supervisor_retains_primary_initialize_error_when_cleanup_fails(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    launcher.initialize.side_effect = RuntimeError("initialization rejected")
    launcher.stop.side_effect = RuntimeError("host did not stop")

    with pytest.raises(RuntimeError) as caught:
        supervisor._start_claimed(record)

    message = str(caught.value)
    assert "initialization rejected" in message
    assert "host did not stop" in message
    assert supervisor.processes[record.plugin_id] is launched
    token = launcher.initialize.call_args.kwargs["capability_token"]
    assert supervisor.capability_manager.verify(
        token,
        plugin_id=record.plugin_id,
        process_id=launched.process.pid,
        capability="media.read",
    ) is None


def test_supervisor_serializes_concurrent_starts_for_same_plugin(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    first_launch_entered = threading.Event()
    release_first_launch = threading.Event()
    second_launch_entered = threading.Event()
    launch_count = 0
    launch_count_lock = threading.Lock()

    def launch(*_args) -> PluginProcess:
        nonlocal launch_count
        with launch_count_lock:
            launch_count += 1
            current = launch_count
        if current == 1:
            first_launch_entered.set()
            assert release_first_launch.wait(timeout=2)
        else:
            second_launch_entered.set()
        return launched

    launcher.launch.side_effect = launch
    errors: list[BaseException] = []

    def start() -> None:
        try:
            supervisor._start_claimed(record)
        except BaseException as error:
            errors.append(error)

    first = threading.Thread(target=start)
    second = threading.Thread(target=start)
    first.start()
    assert first_launch_entered.wait(timeout=2)
    second.start()
    assert not second_launch_entered.wait(timeout=0.2)
    release_first_launch.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert launcher.launch.call_count == 1
    assert launcher.initialize.call_count == 1
    assert supervisor.processes[record.plugin_id] is launched


def test_supervisor_serializes_stop_against_in_progress_start(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    initialize_entered = threading.Event()
    release_initialize = threading.Event()
    stop_returned = threading.Event()
    errors: list[BaseException] = []

    def initialize(*_args, **_kwargs) -> None:
        initialize_entered.set()
        assert release_initialize.wait(timeout=2)

    launcher.initialize.side_effect = initialize

    def start() -> None:
        try:
            supervisor._start_claimed(record)
        except BaseException as error:
            errors.append(error)

    def stop() -> None:
        try:
            supervisor.stop(record.plugin_id)
        except BaseException as error:
            errors.append(error)
        finally:
            stop_returned.set()

    start_thread = threading.Thread(target=start)
    stop_thread = threading.Thread(target=stop)
    start_thread.start()
    assert initialize_entered.wait(timeout=2)
    stop_thread.start()
    assert not stop_returned.wait(timeout=0.2)
    release_initialize.set()
    start_thread.join(timeout=2)
    stop_thread.join(timeout=2)

    assert errors == []
    assert record.plugin_id not in supervisor.processes
    assert record.plugin_id not in supervisor._ready
    assert record.plugin_id not in supervisor._capability_tokens
    launcher.stop.assert_called_once_with(launched)


def test_supervisor_retains_cleanup_pending_handle_from_launch_failure(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    launcher.launch.side_effect = PluginLaunchError(
        launched,
        RuntimeError("invalid handshake"),
        RuntimeError("cleanup could not be confirmed"),
    )

    with pytest.raises(PluginLaunchError, match="cleanup could not be confirmed"):
        supervisor._start_claimed(record)

    assert supervisor.processes[record.plugin_id] is launched
    assert record.plugin_id not in supervisor._ready
    assert record.plugin_id not in supervisor._capability_tokens


def test_supervisor_revokes_capability_when_stopping_ready_host(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    supervisor._start_claimed(record)
    token = launcher.initialize.call_args.kwargs["capability_token"]

    supervisor.stop(record.plugin_id)

    assert supervisor.capability_manager.verify(
        token,
        plugin_id=record.plugin_id,
        process_id=launched.process.pid,
        capability="media.read",
    ) is None


def test_supervisor_retains_handle_when_stop_fails_until_retry_succeeds(
    tmp_path: Path,
) -> None:
    supervisor, record, launcher, launched = _setup_supervisor(tmp_path)
    supervisor._start_claimed(record)
    token = launcher.initialize.call_args.kwargs["capability_token"]
    launcher.stop.side_effect = [RuntimeError("host did not stop"), None]

    with pytest.raises(RuntimeError, match="host did not stop"):
        supervisor.stop(launched.plugin_id)

    assert supervisor.processes[launched.plugin_id] is launched
    assert supervisor.capability_manager.verify(
        token,
        plugin_id=record.plugin_id,
        process_id=launched.process.pid,
        capability="media.read",
    ) is None
    with pytest.raises(RuntimeError, match="cleanup is pending"):
        supervisor._start_claimed(record)

    supervisor.stop(launched.plugin_id)

    assert launched.plugin_id not in supervisor.processes
    launcher.launch.assert_called_once()
    assert launcher.stop.call_args_list == [
        ((launched,), {}),
        ((launched,), {}),
    ]


def test_supervisor_stop_all_attempts_every_host_and_retains_only_failures(
    tmp_path: Path,
) -> None:
    supervisor, _record, launcher, first = _setup_supervisor(
        tmp_path,
        plugin_id="plugin.first",
        process_id=101,
    )
    second = PluginProcess(
        "plugin.failed",
        SimpleNamespace(pid=202, poll=lambda: None),
        Mock(),
    )
    third = PluginProcess(
        "plugin.third",
        SimpleNamespace(pid=303, poll=lambda: None),
        Mock(),
    )
    supervisor.processes = {
        first.plugin_id: first,
        second.plugin_id: second,
        third.plugin_id: third,
    }

    def stop_host(plugin: PluginProcess) -> None:
        if plugin is second:
            raise RuntimeError("host did not stop")

    launcher.stop.side_effect = stop_host

    with pytest.raises(RuntimeError, match="plugin.failed"):
        supervisor.stop_all()

    assert [call.args[0] for call in launcher.stop.call_args_list] == [
        first,
        second,
        third,
    ]
    assert supervisor.processes == {second.plugin_id: second}
