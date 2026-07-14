from __future__ import annotations

from unittest.mock import patch

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.builtin import BuiltinProviderIntegrityError
from core.plugins.recovery import RecoveryReport
from core.security.safe_mode import SecurityMode
from core.storage.paths import AppPaths


def test_bootstrap_blocks_when_transaction_recovery_fails(tmp_path) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    with (
        patch("core.bootstrap.bootstrap.AppPaths.discover", return_value=paths),
        patch("core.bootstrap.bootstrap.PluginTransactionRecovery") as recovery_type,
    ):
        recovery_type.return_value.recover_all.return_value = RecoveryReport(
            errors=("example.plugin: unresolved transaction",)
        )
        context = Bootstrap(portable=True).initialize()
    assert context.security.mode is SecurityMode.BLOCKED
    assert context.security.reason == "example.plugin: unresolved transaction"
    context.lifecycle.shutdown()



def test_bootstrap_blocks_and_skips_tampered_builtin_provider(tmp_path) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    with (
        patch("core.bootstrap.bootstrap.AppPaths.discover", return_value=paths),
        patch(
            "core.bootstrap.bootstrap.ensure_builtin_providers",
            side_effect=BuiltinProviderIntegrityError("youtube/provider.py"),
        ),
    ):
        context = Bootstrap(portable=True).initialize()
    assert context.security.mode is SecurityMode.BLOCKED
    assert "built-in download MOD invalid" in context.security.reason
    assert context.download_providers.statuses() == ()
    context.lifecycle.shutdown()
