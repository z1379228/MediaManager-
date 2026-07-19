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
    assert not context.features.is_enabled("media-ad-trim")
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
    assert not hasattr(context, "plugin_supervisor")
    assert (
        context.plugin_manager.lifecycle_lock
        is context.publisher_manager.lifecycle_lock
        is context.plugin_installer.lifecycle_lock
        is context.plugin_cleanup.lifecycle_lock
        is context.plugin_recovery.lifecycle_lock
        is context.plugin_maintenance.lifecycle_lock
        is context.plugin_updater.lifecycle_lock
        is context.plugin_rollback.lifecycle_lock
    )
    providers = {
        status.provider_id: status for status in context.download_providers.statuses()
    }
    assert providers["youtube"].enabled
    assert not providers["generic-ytdlp"].enabled
    assert not providers["bilibili"].enabled
    assert not providers["facebook"].enabled
    assert not providers["mega"].enabled
    assert not providers["direct-http"].enabled
    assert set(providers) == {
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "facebook",
        "mega",
        "direct-http",
    }
    assert (
        context.download_providers.matching_provider_id(
            "https://music.youtube.com/watch?v=zqMOLz9q7Ig&list=PLexample"
        )
        == "youtube"
    )
    assert (
        context.download_providers.matching_provider_id(
            "https://www.facebook.com/reel/123456"
        )
        == "facebook"
    )
    assert not context.download_providers.is_enabled("facebook")
    context.download_providers.set_enabled("facebook", True)
    context.download_providers.set_enabled("mega", True)
    context.download_providers.set_enabled("direct-http", True)
    assert (
        context.download_providers.matching_provider_id(
            "https://www.facebook.com/reel/123456"
        )
        == "facebook"
    )
    assert (
        context.download_providers.matching_provider_id(
            "https://mega.nz/file/AbCdEf12#abcdefghijklmnop"
        )
        == "mega"
    )
    assert (
        context.download_providers.matching_provider_id(
            "https://downloads.example.org/release.zip"
        )
        == "direct-http"
    )
    assert (
        context.download_providers.matching_provider_id(
            "https://www.youtube.com/media/release.zip"
        )
        == "youtube"
    )
    assert {status.provider_id for status in context.discovery.statuses()} == {
        "youtube-search",
        "bilibili-search",
        "ani-gamer-search",
        "ani-gamer-episodes",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
    }
    assert context.discovery.is_enabled("youtube-search")
    assert not context.discovery.is_enabled("bilibili-search")
    assert not context.discovery.is_enabled("ani-gamer-search")
    assert not context.discovery.is_enabled("ani-gamer-episodes")
    assert {status.provider_id for status in context.features.statuses()} == {
        "ani-gamer",
        "ani-gamer-offline",
        "ani-gamer-player",
        "bilibili-danmaku",
        "instagram",
        "instagram-page",
        "instagram-export",
        "threads",
        "threads-page",
        "threads-export",
        "twitter",
        "twitter-page",
        "twitter-export",
        "media-convert",
        "media-ad-trim",
        "speech-to-text",
        "automation",
    }
    assert not context.features.is_enabled("instagram")
    assert not context.features.is_enabled("ani-gamer-offline")
    assert not context.features.is_enabled("instagram-page")
    assert not context.features.is_enabled("threads")
    assert not context.features.is_enabled("threads-page")
    assert not context.features.is_enabled("twitter")
    assert not context.features.is_enabled("twitter-page")
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


def test_bootstrap_invalid_settings_starts_with_read_only_status(
    tmp_path, monkeypatch
) -> None:
    import json

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    paths.settings.mkdir(parents=True, exist_ok=True)
    settings_path = paths.settings / "settings.json"
    original = json.dumps(
        {
            "schema_version": 1,
            "language": "ja",
            "log_level": [],
        }
    ).encode("utf-8")
    settings_path.write_bytes(original)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    context = Bootstrap(portable=True).initialize(start_background=False)
    try:
        assert context.settings.language == "ja"
        assert context.settings.log_level == "INFO"
        assert context.settings_load.state == "invalid"
        assert not context.settings_load.writable
        assert context.settings_load.diagnostics == ("invalid_type:log_level",)
        assert settings_path.read_bytes() == original

        audit_entries = [
            json.loads(line)
            for line in (paths.logs / "audit.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        event = next(
            entry for entry in audit_entries if entry["event"] == "settings.loaded"
        )
        assert event["details"] == {
            "state": "invalid",
            "writable": False,
            "diagnostic_codes": ["invalid_type:log_level"],
        }
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
        assert not context.features.is_enabled("ani-gamer")
        assert not context.features.is_enabled("ani-gamer-offline")
        assert not context.features.is_enabled("ani-gamer-player")
        assert not context.features.is_enabled("bilibili-danmaku")
        assert not context.features.is_enabled("media-convert")
        assert not context.features.is_enabled("media-ad-trim")
        assert not context.features.is_enabled("speech-to-text")
        assert not context.features.is_enabled("automation")
    finally:
        context.lifecycle.shutdown()




