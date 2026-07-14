"""Capability declarations for bundled download MODs."""

from contracts.download_capability_v2 import DownloadCapabilityV2
from contracts.media_options_v1 import FORMAT_PRESET_IDS_V1, SUBTITLE_MODES_V1


def builtin_download_capability(provider_id: str) -> DownloadCapabilityV2:
    sites = {
        "youtube": ("youtube",),
        "generic-ytdlp": ("generic", "facebook", "instagram", "threads"),
        "bilibili": ("bilibili",),
    }
    if provider_id not in sites:
        raise KeyError(provider_id)
    timed_comments = ("none", "source", "ass") if provider_id == "bilibili" else ("none",)
    return DownloadCapabilityV2(
        provider_id=provider_id,
        sites=sites[provider_id],
        format_presets=tuple(sorted(FORMAT_PRESET_IDS_V1)),
        subtitle_modes=tuple(sorted(SUBTITLE_MODES_V1)),
        timed_comments=timed_comments,
        supports_playlist=True,
        supports_segments=True,
        supports_resume=True,
        max_batch_size=500,
    )
