from pathlib import Path
from io import StringIO
import sys
from types import SimpleNamespace

import main
import pytest
from core.security.safe_mode import SecurityMode


def test_verify_only_does_not_start_background_workers(monkeypatch) -> None:
    calls: list[str] = []

    class FakeBootstrap:
        def __init__(self, *, portable: bool = False) -> None:
            assert not portable

        def verify_only(self):
            calls.append("verify_only")
            return SimpleNamespace(
                mode=SecurityMode.SAFE_MODE,
                reason="development build",
            )

        def initialize(self):
            raise AssertionError("verify-only must not initialize runtime services")

    monkeypatch.setattr(main, "Bootstrap", FakeBootstrap)
    assert main.main(["--verify-only"]) == 0
    assert calls == ["verify_only"]


def test_plugin_host_entrypoint_routes_without_bootstrap(
    tmp_path, monkeypatch
) -> None:
    import plugin_host.main as plugin_main

    captured = []

    def run_plugin(plugin_id, plugin_root, entry_point, nonce):
        captured.append((plugin_id, plugin_root, entry_point, nonce))
        return 7

    monkeypatch.setattr(plugin_main, "run_plugin", run_plugin)
    result = main.main(
        [
            "--plugin-host",
            "--plugin-id",
            "example.plugin",
            "--plugin-root",
            str(tmp_path),
            "--entry-point",
            "plugin.py",
            "--nonce",
            "n" * 24,
        ]
    )

    assert result == 7
    assert captured == [
        ("example.plugin", str(tmp_path), "plugin.py", "n" * 24)
    ]


def test_source_host_stdio_restoration_is_a_noop() -> None:
    from plugin_host.stdio import (
        restore_frozen_cli_stdio,
        restore_frozen_host_stdio,
    )

    assert restore_frozen_host_stdio()
    assert restore_frozen_cli_stdio()


def test_frozen_cli_stdio_does_not_require_stdin(monkeypatch) -> None:
    import plugin_host.stdio as stdio

    stdout = StringIO()
    stderr = StringIO()
    original_streams = (sys.stdout, sys.__stdout__, sys.stderr, sys.__stderr__)
    monkeypatch.setattr(stdio.os, "name", "nt")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        stdio,
        "_windows_stream",
        lambda identifier, _mode: stdout if identifier == -11 else stderr,
    )
    try:
        assert stdio.restore_frozen_cli_stdio()
        assert sys.stdout is stdout
        assert sys.stderr is stderr
    finally:
        sys.stdout, sys.__stdout__, sys.stderr, sys.__stderr__ = original_streams


def test_version_prepares_frozen_cli_output_before_argparse(
    monkeypatch, capsys
) -> None:
    import plugin_host.stdio as stdio

    calls = []
    monkeypatch.setattr(
        stdio,
        "restore_frozen_cli_stdio",
        lambda: calls.append("restore") or True,
    )
    with pytest.raises(SystemExit) as raised:
        main.main(["--version"])

    assert raised.value.code == 0
    assert calls == ["restore"]
    assert "MediaManager 開發版 9.1" in capsys.readouterr().out


def test_provider_host_routes_with_explicit_builtin_root(
    tmp_path, monkeypatch
) -> None:
    import plugin_host.external_provider as external_provider

    provider_root = tmp_path / "builtin-mod"
    provider = provider_root / "youtube" / "provider.py"
    captured = []

    def run_provider(path, application_root, *, provider_root):
        captured.append((path, application_root, provider_root))
        return 9

    monkeypatch.setattr(external_provider, "run_provider", run_provider)

    assert (
        main.main(
            [
                "--provider-host",
                str(provider),
                "--provider-root",
                str(provider_root),
            ]
        )
        == 9
    )
    assert captured == [
        (provider, Path(main.__file__).resolve().parent, provider_root)
    ]


def test_provider_host_rejects_missing_builtin_root(tmp_path) -> None:
    assert main.main(["--provider-host", str(tmp_path / "provider.py")]) == 2
