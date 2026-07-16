from __future__ import annotations

import pytest

from contracts.provider_failure_v1 import ProviderFailureCode, ProviderFailureV1
from core.downloads.errors import ProviderFailure, classify_provider_failure


@pytest.mark.parametrize(
    ("message", "code", "retryable"),
    [
        ("HTTP Error 429: Too Many Requests", ProviderFailureCode.RATE_LIMITED, True),
        ("This video is not available in your country", ProviderFailureCode.REGION_RESTRICTED, False),
        ("Login required; sign in to continue", ProviderFailureCode.LOGIN_REQUIRED, False),
        ("Video unavailable: uploader removed this video", ProviderFailureCode.CONTENT_REMOVED, False),
        ("Unsupported URL", ProviderFailureCode.UNSUPPORTED, False),
        ("Connection timed out", ProviderFailureCode.TEMPORARY, True),
        ("HTTP Error 500: Domain Not Found", ProviderFailureCode.TEMPORARY, True),
        ("MEGA transfer quota exceeded", ProviderFailureCode.RATE_LIMITED, True),
        ("MEGA service unavailable; connection reset", ProviderFailureCode.TEMPORARY, True),
    ],
)
def test_provider_failures_have_stable_codes(
    message: str, code: ProviderFailureCode, retryable: bool
) -> None:
    failure = classify_provider_failure(message)
    assert failure.code is code
    assert failure.retryable is retryable
    assert str(ProviderFailure(failure)).startswith(f"[{code}]")


def test_structured_provider_failure_round_trip() -> None:
    failure = classify_provider_failure(
        {"code": "LOGIN_REQUIRED", "message": "Sign in", "retryable": False}
    )
    assert failure == ProviderFailureV1(
        ProviderFailureCode.LOGIN_REQUIRED, "Sign in", False
    )
