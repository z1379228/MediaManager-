"""Ordered, fail-closed core bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from core.builtin_mod_catalog import (
    BUILTIN_MOD_CHILDREN,
    builtin_default_enabled,
    builtin_mod_descriptor,
)
from core.bootstrap.lifecycle import Lifecycle
from core.bootstrap.startup_state import StartupPhase, StartupState
from core.downloads.builtin import (
    BuiltinProviderIntegrityError,
    ensure_builtin_provider,
)
from core.dependency_health import find_executable, find_javascript_runtime
from core.dependency_snapshot import DependencySnapshotService
from core.builtin_mod_snapshot import BuiltinModSnapshot
from core.discovery.service import DiscoveryService
from core.downloads.capabilities import builtin_download_capability
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.downloads.provider_registry import DownloadProviderRegistry
from core.downloads.queue import DownloadQueue
from core.downloads.subprocess_provider import SubprocessDownloadProvider
from core.events.event_bus import EventBus
from core.features import DeclarativeFeatureGate, FeatureModRegistry
from core.conversion import ConversionService, MediaAdTrimFeature
from core.transcription import SpeechModelManager, TranscriptionService
from core.automation import AutomationCandidate, AutomationDuplicate, AutomationRule, AutomationService
from core.downloads.archive import DuplicateDownloadError
from core.downloads.models import DownloadRequest
from core.logging.audit_log import AuditLog
from core.logging.logger import configure_logging
from core.library import LibraryService
from core.plugins.cleanup import PluginCleanupManager
from core.plugins.installer import PluginInstaller
from core.plugins.manager import PluginManager
from core.plugins.maintenance import PluginMaintenanceManager
from core.plugins.recovery import PluginTransactionRecovery
from core.plugins.registry import PluginRegistry
from core.plugins.rollback import PluginRollbackManager
from core.plugins.supervisor import PluginSupervisor
from core.plugins.ui_descriptor import PluginUIService
from core.plugins.updater import PluginUpdater
from core.security.integrity_verifier import IntegrityVerifier
from core.security.publisher_manager import PublisherManager
from core.security.release_key import RELEASE_KEY_ID, RELEASE_PUBLIC_KEY
from core.security.safe_mode import SafeMode, SecurityMode
from core.security.trust_store import TrustStore
from core.settings import (
    Settings,
    SettingsLoadResult,
    SettingsService,
    normalized_download_workers,
    normalized_language,
)
from core.storage.paths import AppPaths
from core.updates.offline_bundle import OfflineUpdateInstaller
from core.version import BUILD_CHANNEL


_BUILTIN_DOWNLOAD_DETAILS = {
    "youtube": (
        "YouTube",
        (
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "www.youtube-nocookie.com",
        ),
    ),
    "generic-ytdlp": (
        "其他網站 Beta",
        (
            "vimeo.com",
            "www.vimeo.com",
            "player.vimeo.com",
            "dailymotion.com",
            "www.dailymotion.com",
            "dai.ly",
            "soundcloud.com",
            "www.soundcloud.com",
            "on.soundcloud.com",
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            "vm.tiktok.com",
            "twitch.tv",
            "www.twitch.tv",
            "m.twitch.tv",
            "clips.twitch.tv",
        ),
    ),
    "bilibili": (
        "Bilibili",
        (
            "bilibili.com",
            "www.bilibili.com",
            "m.bilibili.com",
            "space.bilibili.com",
            "b23.tv",
        ),
    ),
    "facebook": (
        "Facebook",
        ("facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"),
    ),
    "mega": (
        "MEGA",
        ("mega.nz", "www.mega.nz"),
    ),
    "direct-http": (
        "Direct HTTP",
        ("direct-http.invalid",),
    ),
}
_BuiltinT = TypeVar("_BuiltinT")


@dataclass(slots=True)
class AppContext:
    settings: Settings
    settings_load: SettingsLoadResult
    paths: AppPaths
    logger: object
    events: EventBus
    security: SafeMode
    trust_store: TrustStore
    audit: AuditLog
    lifecycle: Lifecycle
    download_queue: DownloadQueue
    download_providers: DownloadProviderRegistry
    discovery: DiscoveryService
    plugin_registry: PluginRegistry
    plugin_installer: PluginInstaller
    plugin_supervisor: PluginSupervisor
    plugin_manager: PluginManager
    plugin_cleanup: PluginCleanupManager
    plugin_maintenance: PluginMaintenanceManager
    plugin_recovery: PluginTransactionRecovery
    plugin_updater: PluginUpdater
    plugin_rollback: PluginRollbackManager
    plugin_ui: PluginUIService
    publisher_manager: PublisherManager
    offline_updates: OfflineUpdateInstaller
    library: LibraryService
    features: FeatureModRegistry
    builtin_mod_errors: dict[str, str]
    conversion: ConversionService | None
    transcription: TranscriptionService | None
    automation: AutomationService | None
    dependencies: DependencySnapshotService
    builtin_mod_snapshot: BuiltinModSnapshot | None = None


class Bootstrap:
    def __init__(self, *, portable: bool = False) -> None:
        self.portable = portable
        self.state = StartupState()

    @staticmethod
    def _security_state(paths: AppPaths) -> tuple[SafeMode, TrustStore]:
        security = SafeMode()
        trust_store = TrustStore(paths.security / "trust-store.json")
        try:
            trust_store.load()
        except (OSError, ValueError, TypeError) as error:
            security.block(f"trust store invalid: {error}")
        manifest = paths.release_security / "release-manifest.json"
        if manifest.exists():
            result = IntegrityVerifier(
                paths.application,
                public_key=RELEASE_PUBLIC_KEY,
                key_id=RELEASE_KEY_ID,
            ).verify(manifest)
            if not result.valid:
                security.block("; ".join(result.errors))
        else:
            security.enter_safe_mode(
                f"{BUILD_CHANNEL} build has no signed release manifest"
            )
        return security, trust_store

    def verify_only(self) -> SafeMode:
        """Verify security inputs without starting or mutating runtime services."""
        paths = AppPaths.discover(portable=self.portable)
        security, _ = self._security_state(paths)
        for provider_id in sorted(BUILTIN_PROVIDER_HASHES):
            try:
                ensure_builtin_provider(paths.builtin_mod, provider_id)
            except BuiltinProviderIntegrityError as error:
                security.block(
                    f"built-in MOD invalid ({provider_id}): {error}"
                )
        return security

    def initialize(self, *, start_background: bool = True) -> AppContext:
        paths = AppPaths.discover(portable=self.portable)
        paths.migrate_legacy_user_data()
        paths.migrate_legacy_mod_state()
        paths.ensure_runtime_directories()
        dependencies = DependencySnapshotService(paths.application, paths.data)
        self.state.advance(StartupPhase.PATHS_READY, "runtime paths ready")
        settings_service = SettingsService(paths.settings / "settings.json")
        settings_load = settings_service.load_with_status()
        settings = settings_load.settings
        settings.portable_mode = self.portable
        settings.language = normalized_language(settings.language)
        settings.download_workers = normalized_download_workers(
            settings.download_workers
        )
        self.state.advance(StartupPhase.SETTINGS_READY, "settings loaded")
        logger = configure_logging(paths.logs, settings.log_level)
        audit = AuditLog(paths.logs / "audit.jsonl")
        audit.write(
            "settings.loaded",
            state=settings_load.state,
            writable=settings_load.writable,
            diagnostic_codes=settings_load.diagnostics,
        )
        self.state.advance(StartupPhase.LOGGING_READY, "secure logging ready")
        security, trust_store = self._security_state(paths)
        audit.write("security.bootstrap", mode=security.mode, reason=security.reason)

        lifecycle = Lifecycle()
        library = LibraryService(
            paths.data / "library.sqlite3",
            paths.cache / "artwork",
        )
        download_providers = DownloadProviderRegistry(
            paths.mod / "provider-state.json"
        )
        features = FeatureModRegistry(paths.mod / "feature-state.json")
        conversion: ConversionService | None = None
        transcription: TranscriptionService | None = None
        automation: AutomationService | None = None
        builtin_mod_errors: dict[str, str] = {}
        discovery = DiscoveryService(paths.mod / "discovery-state.json")
        javascript_runtime = find_javascript_runtime(paths.application)

        def record_builtin_failure(provider_id: str, error: Exception) -> None:
            reason = " ".join(str(error).split())[:240]
            if not reason:
                reason = error.__class__.__name__
            builtin_mod_errors[provider_id] = reason
            security.block(f"built-in MOD invalid ({provider_id}): {reason}")
            audit.write(
                "downloads.builtin_provider_invalid",
                provider_id=provider_id,
                error=reason,
            )
            download_details = _BUILTIN_DOWNLOAD_DETAILS.get(provider_id)
            if download_details is not None:
                display_name, hosts = download_details
                download_providers.register_unavailable(
                    provider_id,
                    display_name,
                    reason,
                    hosts=hosts,
                )

        def load_builtin(
            provider_id: str,
            factory: Callable[[Path], _BuiltinT],
        ) -> _BuiltinT | None:
            try:
                provider_root = ensure_builtin_provider(
                    paths.builtin_mod,
                    provider_id,
                    paths.cache / "builtin-mod",
                )
                return factory(provider_root)
            except Exception as error:
                record_builtin_failure(provider_id, error)
                return None

        youtube = load_builtin(
            "youtube",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube"],
                preview_root=paths.temp / "youtube-auto-split",
                runtime_home=paths.temp / "provider-runtime" / "youtube",
            ),
        )
        if youtube is not None:
            download_providers.register(
                youtube, enabled=builtin_default_enabled("youtube")
            )
            download_providers.register_capability(
                builtin_download_capability("youtube")
            )

        generic_ytdlp = load_builtin(
            "generic-ytdlp",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["generic-ytdlp"],
                runtime_home=paths.temp / "provider-runtime" / "generic-ytdlp",
            ),
        )
        if generic_ytdlp is not None:
            download_providers.register(
                generic_ytdlp,
                enabled=builtin_default_enabled("generic-ytdlp"),
            )
            download_providers.register_capability(
                builtin_download_capability("generic-ytdlp")
            )

        bilibili = load_builtin(
            "bilibili",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["bilibili"],
                runtime_home=paths.temp / "provider-runtime" / "bilibili",
            ),
        )
        if bilibili is not None:
            download_providers.register(
                bilibili, enabled=builtin_default_enabled("bilibili")
            )
            download_providers.register_capability(
                builtin_download_capability("bilibili")
            )

        facebook = load_builtin(
            "facebook",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["facebook"],
                runtime_home=paths.temp / "provider-runtime" / "facebook",
            ),
        )
        if facebook is not None:
            download_providers.register(
                facebook, enabled=builtin_default_enabled("facebook")
            )
            download_providers.register_capability(
                builtin_download_capability("facebook")
            )

        mega_get = find_executable(paths.application, "mega-get")
        mega_speedlimit = find_executable(paths.application, "mega-speedlimit")
        mega_tools = {
            name: path
            for name, path in (
                ("mega-get", mega_get),
                ("mega-speedlimit", mega_speedlimit),
            )
            if path
        }
        mega = load_builtin(
            "mega",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                external_tools=mega_tools,
                expected_hashes=BUILTIN_PROVIDER_HASHES["mega"],
                download_timeout=86_400,
                idle_timeout=900,
                runtime_home=paths.temp / "provider-runtime" / "mega",
            ),
        )
        if mega is not None:
            download_providers.register(
                mega, enabled=builtin_default_enabled("mega")
            )
            download_providers.register_capability(
                builtin_download_capability("mega")
            )

        direct_http = load_builtin(
            "direct-http",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["direct-http"],
                download_timeout=86_400,
                idle_timeout=300,
                runtime_home=paths.temp / "provider-runtime" / "direct-http",
            ),
        )
        if direct_http is not None:
            download_providers.register(
                direct_http, enabled=builtin_default_enabled("direct-http")
            )
            download_providers.register_capability(
                builtin_download_capability("direct-http")
            )

        youtube_search = load_builtin(
            "youtube-search",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-search"],
                runtime_home=paths.temp / "provider-runtime" / "youtube-search",
            ),
        )
        if youtube_search is not None:
            discovery.register(
                youtube_search,
                enabled=builtin_default_enabled("youtube-search"),
            )

        bilibili_search = load_builtin(
            "bilibili-search",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["bilibili-search"],
                runtime_home=paths.temp / "provider-runtime" / "bilibili-search",
            ),
        )
        if bilibili_search is not None:
            discovery.register(
                bilibili_search,
                enabled=builtin_default_enabled("bilibili-search"),
            )

        ani_gamer_search = load_builtin(
            "ani-gamer-search",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["ani-gamer-search"],
                runtime_home=paths.temp / "provider-runtime" / "ani-gamer-search",
            ),
        )
        if ani_gamer_search is not None:
            discovery.register(
                ani_gamer_search,
                enabled=builtin_default_enabled("ani-gamer-search"),
            )

        ani_gamer_episodes = load_builtin(
            "ani-gamer-episodes",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["ani-gamer-episodes"],
                runtime_home=paths.temp / "provider-runtime" / "ani-gamer-episodes",
            ),
        )
        if ani_gamer_episodes is not None:
            discovery.register(
                ani_gamer_episodes,
                enabled=builtin_default_enabled("ani-gamer-episodes"),
            )

        for feature_id in ("ani-gamer", "ani-gamer-offline", "ani-gamer-player"):
            ani_gamer_feature = load_builtin(
                feature_id,
                lambda provider_root: DeclarativeFeatureGate.from_file(
                    provider_root / "feature.json"
                ),
            )
            if ani_gamer_feature is not None:
                features.register(
                    ani_gamer_feature,
                    enabled=builtin_default_enabled(feature_id),
                )

        for feature_id in (
            "instagram",
            "instagram-page",
            "instagram-export",
            "threads",
            "threads-page",
            "threads-export",
            "twitter",
            "twitter-page",
            "twitter-export",
        ):
            social_feature = load_builtin(
                feature_id,
                lambda provider_root: DeclarativeFeatureGate.from_file(
                    provider_root / "feature.json"
                ),
            )
            if social_feature is not None:
                features.register(
                    social_feature,
                    enabled=builtin_default_enabled(feature_id),
                )

        bilibili_danmaku = load_builtin(
            "bilibili-danmaku",
            lambda provider_root: DeclarativeFeatureGate.from_file(
                provider_root / "feature.json"
            ),
        )
        if bilibili_danmaku is not None:
            features.register(
                bilibili_danmaku,
                enabled=builtin_default_enabled("bilibili-danmaku"),
            )

        youtube_player = load_builtin(
            "youtube-player",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                js_runtime=javascript_runtime,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-player"],
                preview_root=paths.temp / "youtube-player",
                runtime_home=paths.temp / "provider-runtime" / "youtube-player",
            ),
        )
        if youtube_player is not None:
            discovery.register_video_preview(
                youtube_player,
                enabled=builtin_default_enabled("youtube-player"),
            )

        youtube_history = load_builtin(
            "youtube-history",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-history"],
                history_state_path=paths.data / "youtube-history.json",
                runtime_home=paths.temp / "provider-runtime" / "youtube-history",
            ),
        )
        if youtube_history is not None:
            discovery.register_history(
                youtube_history,
                enabled=builtin_default_enabled("youtube-history"),
            )

        youtube_recovery = load_builtin(
            "youtube-recovery",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-recovery"],
                runtime_home=paths.temp / "provider-runtime" / "youtube-recovery",
            ),
        )
        if youtube_recovery is not None:
            discovery.register_recovery(
                youtube_recovery,
                enabled=builtin_default_enabled("youtube-recovery"),
            )

        youtube_similar = load_builtin(
            "youtube-similar",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-similar"],
                runtime_home=paths.temp / "provider-runtime" / "youtube-similar",
            ),
        )
        if youtube_similar is not None:
            discovery.register_similar(
                youtube_similar,
                enabled=builtin_default_enabled("youtube-similar"),
            )

        youtube_auto_split = load_builtin(
            "youtube-auto-split",
            lambda provider_root: SubprocessDownloadProvider(
                provider_root,
                application_root=paths.application,
                ffmpeg_location=find_executable(paths.application, "ffmpeg"),
                expected_hashes=BUILTIN_PROVIDER_HASHES["youtube-auto-split"],
                analysis_root=paths.temp / "youtube-auto-split",
                runtime_home=paths.temp / "provider-runtime" / "youtube-auto-split",
            ),
        )
        if youtube_auto_split is not None:
            discovery.register_split(
                youtube_auto_split,
                enabled=builtin_default_enabled("youtube-auto-split"),
            )

        conversion = load_builtin(
            "media-convert",
            lambda provider_root: ConversionService(
                find_executable(paths.application, "ffmpeg"),
                provider_root / "presets.json",
                paths.temp / "media-convert",
            ),
        )
        if conversion is not None:
            features.register(
                conversion,
                enabled=builtin_default_enabled("media-convert"),
            )
            media_ad_trim = load_builtin(
                "media-ad-trim",
                lambda _provider_root: MediaAdTrimFeature(conversion),
            )
            if media_ad_trim is not None:
                features.register(
                    media_ad_trim,
                    enabled=builtin_default_enabled("media-ad-trim"),
                )

        transcription = load_builtin(
            "speech-to-text",
            lambda _provider_root: TranscriptionService(
                find_executable(paths.application, "whisper-cli"),
                SpeechModelManager(paths.data / "models" / "speech-to-text"),
                paths.temp / "speech-to-text",
            ),
        )
        if transcription is not None:
            features.register(
                transcription,
                enabled=builtin_default_enabled("speech-to-text"),
            )
        automation_root = load_builtin("automation", lambda provider_root: provider_root)
        download_queue = DownloadQueue(
            download_providers,
            workers=settings.download_workers,
            state_path=paths.data / "download-queue.json",
            archive_path=paths.data / "download-archive.json",
        )
        if start_background:
            download_queue.start()
        plugin_registry = PluginRegistry(paths.plugin_registry)
        plugin_installer = PluginInstaller(paths.mod, plugin_registry, trust_store)
        plugin_supervisor = PluginSupervisor(paths.mod, plugin_registry)
        plugin_manager = PluginManager(
            paths.mod,
            plugin_registry,
            plugin_supervisor,
            trust_store,
            allow_executable_plugins=False,
        )
        if automation_root is not None:
            def dispatch_automation(
                rule: AutomationRule, candidate: AutomationCandidate
            ) -> str:
                preset = rule.preset
                action = str(preset["action"])
                output_dir = Path(str(preset.get("output_dir", paths.downloads)))
                if action == "download":
                    requests: list[DownloadRequest] = []
                    if bool(preset.get("playlist", False)):
                        entries = download_providers.playlist(
                            candidate.source, limit=rule.rate_limit
                        )
                        requests.extend(
                            DownloadRequest(
                                entry.url,
                                output_dir,
                                source_video_id=entry.entry_id,
                                source_title=entry.title,
                                source_artist=entry.artist,
                                source_category="automation-playlist",
                                format_preset=str(preset.get("format_preset", "best")),
                            )
                            for entry in entries[: rule.rate_limit]
                            if entry.available
                        )
                    else:
                        requests.append(
                            DownloadRequest(
                                candidate.source,
                                output_dir,
                                source_category="automation",
                                format_preset=str(preset.get("format_preset", "best")),
                            )
                        )
                    task_ids = []
                    for request in requests:
                        try:
                            task_ids.append(download_queue.add(request))
                        except DuplicateDownloadError:
                            continue
                    if not task_ids:
                        raise AutomationDuplicate("all discovered downloads are already queued or archived")
                    return ",".join(task_ids)
                if action == "media-convert":
                    if conversion is None or not features.is_enabled("media-convert"):
                        raise RuntimeError("Media Convert MOD must be enabled")
                    from core.conversion import ConversionRequest

                    source = Path(candidate.source)
                    conversion_preset = str(preset.get("conversion_preset", "remux-copy"))
                    suffixes = {
                        "audio-mp3": ".mp3",
                        "audio-flac": ".flac",
                        "subtitle-srt": ".srt",
                        "video-h264": ".mp4",
                        "compress-h265": ".mkv",
                    }
                    suffix = suffixes.get(conversion_preset, source.suffix)
                    target = output_dir / f"{source.stem}.converted{suffix}"
                    if target.exists():
                        raise AutomationDuplicate(f"automation output already exists: {target}")
                    return conversion.submit(
                        ConversionRequest((source,), target, conversion_preset)
                    )
                if action == "speech-to-text":
                    if transcription is None or not features.is_enabled("speech-to-text"):
                        raise RuntimeError("Speech to Text MOD must be enabled")
                    from core.transcription import TranscriptionRequest

                    formats = tuple(str(value) for value in preset.get("formats", ("txt", "srt", "vtt")))
                    return transcription.submit(
                        TranscriptionRequest(
                            Path(candidate.source),
                            str(preset.get("model_id", "")),
                            output_dir,
                            formats,
                            str(preset.get("language", "auto")),
                        )
                    )
                raise RuntimeError("unsupported automation action")

            try:
                automation = AutomationService(
                    paths.data / "automation.sqlite3",
                    dispatch_automation,
                )
                features.register(
                    automation,
                    enabled=builtin_default_enabled("automation"),
                )
            except Exception as error:
                record_builtin_failure("automation", error)
                automation = None

        # Flat-MOD builds allowed saved child states to outlive a disabled
        # parent. Reconcile every registry after all feature gates are
        # registered and before any trusted UI is created.
        def builtin_registry(provider_id: str) -> object:
            kind = builtin_mod_descriptor(provider_id).kind
            return {
                "download": download_providers,
                "discovery": discovery,
                "feature": features,
            }[kind]

        for parent_id, child_ids in BUILTIN_MOD_CHILDREN.items():
            try:
                parent_enabled = builtin_registry(parent_id).is_enabled(parent_id)
            except (AttributeError, KeyError, RuntimeError):
                parent_enabled = False
            if parent_enabled:
                continue
            for child_id in child_ids:
                child_registry = builtin_registry(child_id)
                try:
                    child_enabled = child_registry.is_enabled(child_id)
                except (AttributeError, KeyError, RuntimeError):
                    child_enabled = False
                if child_enabled:
                    child_registry.set_enabled(child_id, False)
        plugin_cleanup = PluginCleanupManager(paths.mod, plugin_registry)
        plugin_recovery = PluginTransactionRecovery(
            paths.mod, plugin_registry, plugin_manager
        )
        recovery_report = plugin_recovery.recover_all()
        if recovery_report.recovered:
            audit.write(
                "plugins.transactions_recovered",
                plugin_ids=recovery_report.recovered,
            )
        if recovery_report.warnings:
            audit.write(
                "plugins.transaction_recovery_warning",
                warnings=recovery_report.warnings,
            )
        if recovery_report.errors:
            security.block("; ".join(recovery_report.errors))
            audit.write(
                "plugins.transaction_recovery_failed",
                errors=recovery_report.errors,
            )
        self.state.advance(
            StartupPhase.SECURITY_CHECKED, f"security mode: {security.mode}"
        )
        publisher_manager = PublisherManager(
            trust_store, plugin_registry, plugin_manager
        )
        version_root = (
            paths.application.parent
            if (paths.application / "release-info.json").is_file()
            else paths.application / "Version"
        )
        offline_updates = OfflineUpdateInstaller(
            version_root,
            public_key=RELEASE_PUBLIC_KEY,
            key_id=RELEASE_KEY_ID,
        )
        plugin_maintenance = PluginMaintenanceManager(
            paths.mod, plugin_registry, plugin_manager
        )
        plugin_updater = PluginUpdater(
            paths.mod, plugin_registry, plugin_installer, plugin_manager
        )
        plugin_rollback = PluginRollbackManager(
            paths.mod, plugin_registry, plugin_manager
        )
        plugin_ui = PluginUIService(
            paths.mod,
            plugin_registry,
            plugin_manager,
            locale=settings.language,
        )
        lifecycle.on_shutdown(plugin_registry.close)
        lifecycle.on_shutdown(plugin_supervisor.stop_all)
        lifecycle.on_shutdown(download_providers.close)
        lifecycle.on_shutdown(discovery.close)
        lifecycle.on_shutdown(download_queue.shutdown)
        lifecycle.on_shutdown(library.close)
        lifecycle.on_shutdown(features.close)
        started_plugins: list[str] = []
        if security.mode is SecurityMode.NORMAL:
            for record in plugin_registry.list_enabled():
                result = plugin_manager.set_enabled(
                    record.plugin_id, True, security.mode
                )
                if result.successful:
                    started_plugins.append(record.plugin_id)
                else:
                    audit.write(
                        "plugin.start_rejected",
                        plugin_id=record.plugin_id,
                        errors=result.errors,
                    )
        audit.write("plugins.started", plugin_ids=started_plugins)
        builtin_mod_snapshot = BuiltinModSnapshot.capture(
            download_providers,
            discovery,
            features,
            builtin_mod_errors,
        )
        context = AppContext(
            settings=settings,
            settings_load=settings_load,
            paths=paths,
            logger=logger,
            events=EventBus(),
            security=security,
            trust_store=trust_store,
            audit=audit,
            lifecycle=lifecycle,
            download_queue=download_queue,
            download_providers=download_providers,
            discovery=discovery,
            plugin_registry=plugin_registry,
            plugin_installer=plugin_installer,
            plugin_supervisor=plugin_supervisor,
            plugin_manager=plugin_manager,
            plugin_cleanup=plugin_cleanup,
            plugin_maintenance=plugin_maintenance,
            plugin_recovery=plugin_recovery,
            plugin_updater=plugin_updater,
            plugin_rollback=plugin_rollback,
            plugin_ui=plugin_ui,
            publisher_manager=publisher_manager,
            offline_updates=offline_updates,
            library=library,
            features=features,
            builtin_mod_errors=builtin_mod_errors,
            conversion=conversion,
            transcription=transcription,
            automation=automation,
            dependencies=dependencies,
            builtin_mod_snapshot=builtin_mod_snapshot,
        )
        self.state.advance(StartupPhase.READY, "core ready")
        return context

    def run(self, *, headless: bool = False, verify_only: bool = False) -> int:
        if verify_only:
            security = self.verify_only()
            print(f"MediaManager security mode: {security.mode}")
            if security.reason:
                print(security.reason)
            return 2 if security.mode == "BLOCKED" else 0
        context = self.initialize()
        if headless:
            print(f"MediaManager ready ({context.security.mode})")
            return 2 if context.security.mode == "BLOCKED" else 0
        from trusted_ui.security_window import run_security_ui

        return run_security_ui(context)












