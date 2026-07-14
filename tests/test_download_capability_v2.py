from pathlib import Path

import pytest

from contracts.download_capability_v2 import (
    DownloadCapabilityError,
    DownloadCapabilityV2,
)
from contracts.provider_failure_v1 import ProviderFailureCode, ProviderFailureV1
from core.downloads.models import DownloadRequest
from core.downloads.capabilities import builtin_download_capability
from core.downloads.negotiation import negotiate_download, retry_decision


def _capability(*, segments: bool = True) -> DownloadCapabilityV2:
    return DownloadCapabilityV2.from_dict(
        {
            "provider_id": "youtube",
            "sites": ["youtube"],
            "format_presets": ["best", "audio-mp3"],
            "subtitle_modes": ["none", "selected"],
            "timed_comments": ["none"],
            "supports_playlist": True,
            "supports_segments": segments,
            "supports_resume": True,
            "max_batch_size": 100,
        }
    )


def test_download_negotiation_accepts_supported_request(tmp_path: Path) -> None:
    result = negotiate_download(
        DownloadRequest("https://youtube.com/watch?v=one", tmp_path),
        _capability(),
    )
    assert result.provider_id == "youtube"
    assert result.resumable


def test_download_negotiation_rejects_unsupported_segment(tmp_path: Path) -> None:
    request = DownloadRequest(
        "https://youtube.com/watch?v=one", tmp_path, start_time=10, end_time=20
    )
    with pytest.raises(DownloadCapabilityError, match="segments"):
        negotiate_download(request, _capability(segments=False))


def test_retry_policy_is_bounded() -> None:
    temporary = ProviderFailureV1(ProviderFailureCode.TEMPORARY, "offline", True)
    permanent = ProviderFailureV1(ProviderFailureCode.CONTENT_REMOVED, "gone", False)
    assert retry_decision(temporary, attempt=1).delay_seconds == 2
    assert not retry_decision(temporary, attempt=3).retry
    assert not retry_decision(permanent, attempt=1).retry


def test_direct_download_capability_construction_is_validated() -> None:
    with pytest.raises(DownloadCapabilityError):
        DownloadCapabilityV2(
            "youtube", (), ("best",), ("none",), ("none",), True, True, True, 1
        )


def test_generic_provider_does_not_claim_unverified_social_sites() -> None:
    capability = builtin_download_capability("generic-ytdlp")

    assert capability.sites == ("generic",)
    assert not {"facebook", "instagram", "threads"}.intersection(capability.sites)
