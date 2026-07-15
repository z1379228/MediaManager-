from pathlib import Path
from types import SimpleNamespace

import main
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
    from plugin_host.stdio import restore_frozen_host_stdio

    assert restore_frozen_host_stdio()


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
