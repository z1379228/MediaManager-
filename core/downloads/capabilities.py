"""Capability declarations for bundled download MODs."""

from contracts.download_capability_v2 import DownloadCapabilityV2
from contracts.media_options_v1 import FORMAT_PRESET_IDS_V1, SUBTITLE_MODES_V1


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
    }
    if provider_id not in sites:
        raise KeyError(provider_id)
    timed_comments = ("none", "source", "ass") if provider_id == "bilibili" else ("none",)
    format_presets = (
        ("best",)
        if provider_id == "mega"
        else tuple(sorted(FORMAT_PRESET_IDS_V1))
    )
    subtitle_modes = (
        ("none",)
        if provider_id == "mega"
        else tuple(sorted(SUBTITLE_MODES_V1))
    )
    return DownloadCapabilityV2(
        provider_id=provider_id,
        sites=sites[provider_id],
        format_presets=format_presets,
        subtitle_modes=subtitle_modes,
        timed_comments=timed_comments,
        supports_playlist=provider_id in {"youtube", "generic-ytdlp", "bilibili"},
        supports_segments=provider_id != "mega",
        supports_resume=True,
        max_batch_size=50 if provider_id == "mega" else 500,
    )
