from core.bootstrap.bootstrap import Bootstrap
from core.discovery.service import DiscoveryService
from core.downloads.queue import DownloadQueue
from core.library import LibraryService
from core.features import FeatureModRegistry
from core.plugins.cleanup import PluginCleanupManager
from core.plugins.maintenance import PluginMaintenanceManager
from core.plugins.recovery import PluginTransactionRecovery
from core.plugins.rollback import PluginRollbackManager
from core.plugins.updater import PluginUpdater
from core.storage.paths import AppPaths
from core.settings import Settings, SettingsService


def test_bootstrap_plugin_service_types_are_wired_by_name(
    tmp_path, monkeypatch
) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize()
    assert isinstance(context.download_queue, DownloadQueue)
    assert isinstance(context.library, LibraryService)
    assert isinstance(context.features, FeatureModRegistry)
    assert context.conversion is not None
    assert not context.features.is_enabled("media-convert")
    assert context.transcription is not None
    assert not context.features.is_enabled("speech-to-text")
    assert context.automation is not None
    assert not context.features.is_enabled("automation")
    assert isinstance(context.discovery, DiscoveryService)
    assert isinstance(context.plugin_cleanup, PluginCleanupManager)
    assert isinstance(context.plugin_maintenance, PluginMaintenanceManager)
    assert isinstance(context.plugin_recovery, PluginTransactionRecovery)
    assert isinstance(context.plugin_updater, PluginUpdater)
    assert isinstance(context.plugin_rollback, PluginRollbackManager)
    providers = {
        status.provider_id: status for status in context.download_providers.statuses()
    }
    assert providers["youtube"].enabled
    assert not providers["generic-ytdlp"].enabled
    assert not providers["bilibili"].enabled
    assert set(providers) == {"youtube", "generic-ytdlp", "bilibili"}
    assert {status.provider_id for status in context.discovery.statuses()} == {
        "youtube-search",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
    }
    assert {status.provider_id for status in context.features.statuses()} == {
        "media-convert",
        "speech-to-text",
        "automation",
    }
    context.lifecycle.shutdown()


def test_bootstrap_applies_supported_language_to_mod_ui(tmp_path, monkeypatch) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    SettingsService(paths.settings / "settings.json").save(Settings(language="ja"))
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    try:
        assert context.settings.language == "ja"
        assert context.plugin_ui.locale == "ja"
    finally:
        context.lifecycle.shutdown()


def test_clean_bootstrap_starts_no_optional_provider_process(
    tmp_path, monkeypatch
) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    try:
        providers = list(context.download_providers._providers.values())
        discovery_groups = (
            context.discovery._providers,
            context.discovery._history_providers,
            context.discovery._recovery_providers,
            context.discovery._similar_providers,
            context.discovery._split_providers,
            context.discovery._video_preview_providers,
        )
        providers.extend(
            provider for group in discovery_groups for provider in group.values()
        )
        assert providers
        assert all(not provider._processes for provider in providers)
        assert not context.features.is_enabled("media-convert")
        assert not context.features.is_enabled("speech-to-text")
        assert not context.features.is_enabled("automation")
    finally:
        context.lifecycle.shutdown()




