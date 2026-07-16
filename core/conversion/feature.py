"""Feature gate for optional conversion capabilities."""

from __future__ import annotations

from core.conversion.service import ConversionService


class MediaAdTrimFeature:
    """Expose local ad-segment trimming as a separately disabled child MOD."""

    provider_id = "media-ad-trim"
    display_name = "Local Ad Segment Trim"

    def __init__(self, conversion: ConversionService) -> None:
        self.conversion = conversion
        self._enabled = False

    @property
    def available(self) -> bool:
        return self.conversion.available

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> int:
        if enabled and not self.available:
            raise RuntimeError("FFmpeg is required before Local Ad Trim can be enabled")
        self._enabled = enabled
        return 0 if enabled else self.conversion.cancel_preset("ad-trim-h264")

    def close(self) -> None:
        self.set_enabled(False)
