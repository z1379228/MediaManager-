"""Fail-closed download option negotiation and retry decisions."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.download_capability_v2 import DownloadCapabilityError, DownloadCapabilityV2
from contracts.provider_failure_v1 import ProviderFailureV1
from core.downloads.models import DownloadRequest


@dataclass(frozen=True, slots=True)
class DownloadNegotiation:
    provider_id: str
    resumable: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    delay_seconds: int
    reason: str


def negotiate_download(
    request: DownloadRequest, capability: DownloadCapabilityV2
) -> DownloadNegotiation:
    if request.format_preset not in capability.format_presets:
        raise DownloadCapabilityError("download MOD does not support this format")
    if request.subtitle_mode not in capability.subtitle_modes:
        raise DownloadCapabilityError("download MOD does not support this subtitle mode")
    if request.timed_comment_mode not in capability.timed_comments:
        raise DownloadCapabilityError(
            "download MOD does not support this timed-comment mode"
        )
    segmented = request.start_time is not None or request.end_time is not None
    if segmented and not capability.supports_segments:
        raise DownloadCapabilityError("download MOD does not support media segments")
    warnings = () if capability.supports_resume else ("download MOD cannot resume",)
    return DownloadNegotiation(
        capability.provider_id, capability.supports_resume, warnings
    )


def retry_decision(
    failure: ProviderFailureV1, *, attempt: int, max_attempts: int = 3
) -> RetryDecision:
    if attempt < 1 or max_attempts < 1:
        raise ValueError("retry attempt is invalid")
    if not failure.retryable:
        return RetryDecision(False, 0, "failure is not retryable")
    if attempt >= max_attempts:
        return RetryDecision(False, 0, "retry limit reached")
    delays = (2, 8, 30)
    return RetryDecision(
        True,
        delays[min(attempt - 1, len(delays) - 1)],
        "temporary provider failure",
    )
