from __future__ import annotations

from unittest.mock import patch

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.builtin import (
    BuiltinProviderIntegrityError,
    ensure_builtin_provider,
)
from core.downloads.provider_registry import ProviderUnavailableError
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



def test_bootstrap_isolates_tampered_optional_builtin_provider(tmp_path) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    long_reason = "bilibili/provider.py " + "tampered " * 80

    def ensure_one(preferred_root, provider_id, cache_root=None):
        if provider_id == "bilibili":
            raise BuiltinProviderIntegrityError(long_reason)
        return ensure_builtin_provider(
            preferred_root,
            provider_id,
            cache_root,
        )

    with (
        patch("core.bootstrap.bootstrap.AppPaths.discover", return_value=paths),
        patch(
            "core.bootstrap.bootstrap.ensure_builtin_provider",
            side_effect=ensure_one,
        ),
    ):
        context = Bootstrap(portable=True).initialize()
    try:
        assert context.security.mode is SecurityMode.BLOCKED
        assert set(context.builtin_mod_errors) == {"bilibili"}
        assert context.builtin_mod_errors["bilibili"].startswith(
            "bilibili/provider.py"
        )
        assert len(context.builtin_mod_errors["bilibili"]) == 240
        statuses = {
            status.provider_id: status
            for status in context.download_providers.statuses()
        }
        assert statuses["youtube"].available
        assert statuses["youtube"].enabled
        assert statuses["generic-ytdlp"].available
        assert not statuses["bilibili"].available
        assert statuses["bilibili"].reason == context.builtin_mod_errors["bilibili"]
        assert context.download_providers.provider_for(
            "https://music.youtube.com/watch?v=example"
        ).provider_id == "youtube"
    finally:
        context.lifecycle.shutdown()


def test_bootstrap_reports_failed_youtube_initialization_for_its_hosts(
    tmp_path,
) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)

    def ensure_one(preferred_root, provider_id, cache_root=None):
        if provider_id == "youtube":
            raise BuiltinProviderIntegrityError("integrity mismatch: provider.py")
        return ensure_builtin_provider(
            preferred_root,
            provider_id,
            cache_root,
        )

    with (
        patch("core.bootstrap.bootstrap.AppPaths.discover", return_value=paths),
        patch(
            "core.bootstrap.bootstrap.ensure_builtin_provider",
            side_effect=ensure_one,
        ),
    ):
        context = Bootstrap(portable=True).initialize(start_background=False)
    try:
        assert context.download_providers.matching_provider_id(
            "https://music.youtube.com/playlist?list=example"
        ) == "youtube"
        with pytest.raises(
            ProviderUnavailableError,
            match="YouTube MOD 初始化失敗.*integrity mismatch",
        ):
            context.download_providers.provider_for(
                "https://music.youtube.com/playlist?list=example"
            )
        assert {
            status.provider_id
            for status in context.download_providers.statuses()
            if status.available
        } == {"generic-ytdlp", "bilibili", "facebook", "mega", "direct-http"}
    finally:
        context.lifecycle.shutdown()
