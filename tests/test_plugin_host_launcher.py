from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.plugins.host_launcher import HostLauncher


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
