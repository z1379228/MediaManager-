"""Capability declarations for bundled download MODs."""

from contracts.download_capability_v2 import DownloadCapabilityV2
from contracts.media_options_v1 import FORMAT_PRESET_IDS_V1, SUBTITLE_MODES_V1
from contracts.provider_capability_v1 import ProviderCapabilityV1

_VIDEO_ONLY_PRESETS = ("best", "video-1080", "video-720", "video-480")
_GENERIC_PRESETS = (
    "best",
    "video-1080",
    "video-720",
    "video-480",
    "audio-m4a",
    "audio-mp3",
)


def builtin_download_capability(provider_id: str) -> DownloadCapabilityV2:
    sites = {
        "youtube": ("youtube",),
        # Keep this provider generic until individual sites have their own
        # verified capability declarations.  The provider URL allowlist does
        # not currently accept Facebook, Instagram, or Threads.
        "generic-ytdlp": ("generic",),
        "bilibili": ("bilibili",),
        "facebook": ("facebook",),
        "mega": ("mega",),
        "direct-http": ("direct-http",),
    }
    if provider_id not in sites:
        raise KeyError(provider_id)
    timed_comments = ("none", "source", "ass") if provider_id == "bilibili" else ("none",)
    if provider_id in {"mega", "direct-http"}:
        format_presets = ("best",)
    elif provider_id == "facebook":
        format_presets = _VIDEO_ONLY_PRESETS
    elif provider_id == "generic-ytdlp":
        format_presets = _GENERIC_PRESETS
    else:
        format_presets = tuple(sorted(FORMAT_PRESET_IDS_V1))
    subtitle_modes = (
        ("none",)
        if provider_id in {"facebook", "mega", "direct-http"}
        else tuple(sorted(SUBTITLE_MODES_V1))
    )
    return DownloadCapabilityV2(
        provider_id=provider_id,
        sites=sites[provider_id],
        format_presets=format_presets,
        subtitle_modes=subtitle_modes,
        timed_comments=timed_comments,
        supports_playlist=provider_id in {"youtube", "generic-ytdlp", "bilibili"},
        supports_segments=provider_id not in {"facebook", "mega", "direct-http"},
        supports_resume=True,
        max_batch_size=(
            50 if provider_id == "mega" else 100 if provider_id == "direct-http" else 500
        ),
    )


def builtin_provider_capability(provider_id: str) -> ProviderCapabilityV1:
    """Return the safe, declarative capability matrix for a built-in provider."""

    declarations = {
        "youtube": ("youtube", ("search", "preview", "download", "playlist", "subtitles", "offline-archive"), False, False, True, 500),
        "generic-ytdlp": ("generic", ("preview", "download", "playlist", "subtitles", "offline-archive"), False, False, True, 100),
        "bilibili": ("bilibili", ("search", "preview", "download", "playlist", "subtitles", "timed-comments", "offline-archive"), False, False, True, 500),
        "facebook": ("facebook", ("preview", "download"), True, False, False, 100),
        "mega": ("mega", ("download", "offline-archive"), False, False, True, 50),
        "direct-http": ("direct-http", ("download", "offline-archive"), False, False, True, 100),
    }
    try:
        site, operations, official, local, archive, batch = declarations[provider_id]
    except KeyError as error:
        raise KeyError(provider_id) from error
    return ProviderCapabilityV1(
        provider_id=provider_id,
        sites=(site,),
        operations=operations,
        requires_official_page=official,
        supports_local_playback=local,
        supports_offline_archive=archive,
        max_batch_size=batch,
    )
