from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import core.plugins.host_launcher as host_launcher
from core.plugins.host_launcher import HostLauncher, PluginLaunchError


def test_frozen_host_command_uses_canonical_executable_entrypoint(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    command = HostLauncher._command(
        "example.plugin", tmp_path, "plugin.py", "n" * 24
    )

    assert command[:2] == [sys.executable, "--plugin-host"]
    assert "-m" not in command


def test_source_plugin_host_requires_valid_handshake(tmp_path: Path) -> None:
    root = tmp_path / "example.plugin"
    root.mkdir()
    (root / "plugin.py").write_text(
        "def handle_request(request):\n    return request\n",
        encoding="utf-8",
    )
    launcher = HostLauncher(handshake_timeout=3)

    plugin = launcher.launch(
        "example.plugin", root, "plugin.py", "n" * 24
    )
    try:
        assert plugin.process.poll() is None
    finally:
        launcher.stop(plugin)


def test_plugin_host_rejects_module_without_handler(tmp_path: Path) -> None:
    root = tmp_path / "example.plugin"
    root.mkdir()
    (root / "plugin.py").write_text("value = 1\n", encoding="utf-8")
    launcher = HostLauncher(handshake_timeout=3)

    with pytest.raises(RuntimeError, match="rejected startup"):
        launcher.launch("example.plugin", root, "plugin.py", "n" * 24)


def test_launch_failure_exposes_handle_when_handshake_cleanup_is_unconfirmed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "example.plugin"
    root.mkdir()
    (root / "plugin.py").write_text("value = 1\n", encoding="utf-8")
    process = SimpleNamespace(
        _handle=17,
        pid=321,
        stdin=io.StringIO(),
        stdout=io.StringIO("not-json\n"),
        stderr=io.StringIO(),
    )
    process.poll = Mock(return_value=None)
    process.terminate = Mock(side_effect=OSError("terminate failed"))
    process.wait = Mock()
    process.kill = Mock()
    job = Mock()
    monkeypatch.setattr(host_launcher, "ProviderJob", lambda: job)
    monkeypatch.setattr(host_launcher.subprocess, "Popen", lambda *_a, **_k: process)
    launcher = HostLauncher(handshake_timeout=0.1)

    with pytest.raises(PluginLaunchError) as caught:
        launcher.launch("example.plugin", root, "plugin.py", "n" * 24)

    assert "invalid handshake" in str(caught.value)
    assert "terminate failed" in str(caught.value)
    assert caught.value.plugin_process.process is process
    assert caught.value.plugin_process.job is job
    assert "invalid handshake" in str(caught.value.startup_error)
    assert "terminate failed" in str(caught.value.cleanup_error)
    job.assign.assert_called_once_with(17)
