from pathlib import Path
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


def test_frozen_cli_stdio_uses_null_device_without_stdin(monkeypatch) -> None:
    import plugin_host.stdio as stdio

    original_streams = (sys.stdout, sys.__stdout__, sys.stderr, sys.__stderr__)
    monkeypatch.setattr(stdio.os, "name", "nt")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    try:
        assert not stdio.restore_frozen_cli_stdio()
        stdout = sys.stdout
        stderr = sys.stderr
        assert stdout is not None
        assert stderr is not None
        assert stdout.writable()
        assert stderr.writable()
        stdio.close_frozen_cli_stdio()
        assert stdout.closed
        assert stderr.closed
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
    monkeypatch.setattr(
        stdio,
        "close_frozen_cli_stdio",
        lambda: calls.append("close"),
    )
    with pytest.raises(SystemExit) as raised:
        main.main(["--version"])

    assert raised.value.code == 0
    assert calls == ["restore", "close"]
    assert "MediaManager 開發版 25.0" in capsys.readouterr().out


def test_frozen_windowed_cli_uses_hard_process_exit(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(main, "main", lambda argv: 7)
    monkeypatch.setattr(main.os, "_exit", calls.append)

    main._script_entry(["--headless"])

    assert calls == [7]


def test_frozen_version_converts_argparse_exit_to_hard_exit(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    def raise_version_exit(argv):
        raise SystemExit(0)

    monkeypatch.setattr(main, "main", raise_version_exit)
    monkeypatch.setattr(main.os, "_exit", calls.append)

    main._script_entry(["--version"])

    assert calls == [0]


def test_source_script_entry_keeps_normal_system_exit(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(main, "main", lambda argv: 3)

    with pytest.raises(SystemExit) as raised:
        main._script_entry(["--headless"])

    assert raised.value.code == 3


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
