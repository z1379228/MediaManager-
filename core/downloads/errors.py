"""Download service exceptions and stable provider error classification."""

from contracts.provider_failure_v1 import (
    ProviderFailureCode,
    ProviderFailureV1,
)


class DownloadCancelled(RuntimeError):
    pass


class ProviderFailure(RuntimeError):
    def __init__(self, failure: ProviderFailureV1) -> None:
        self.failure = failure
        super().__init__(f"[{failure.code}] {failure.message}")


def classify_provider_failure(value: object) -> ProviderFailureV1:
    if isinstance(value, dict):
        try:
            return ProviderFailureV1.from_dict(value)
        except (TypeError, ValueError):
            pass
    message = " ".join(str(value or "provider failed").split())[:1000]
    lowered = message.casefold()
    patterns = (
        (
            ProviderFailureCode.RATE_LIMITED,
            ("http error 429", "too many requests", "rate limit"),
            True,
        ),
        (
            ProviderFailureCode.REGION_RESTRICTED,
            ("geo", "region", "not available in your country"),
            False,
        ),
        (
            ProviderFailureCode.LOGIN_REQUIRED,
            ("login required", "sign in", "cookies", "private video"),
            False,
        ),
        (
            ProviderFailureCode.CONTENT_REMOVED,
            ("removed", "deleted", "video unavailable", "no longer available"),
            False,
        ),
        (
            ProviderFailureCode.UNSUPPORTED,
            ("unsupported url", "no suitable extractor", "not supported"),
            False,
        ),
        (
            ProviderFailureCode.TEMPORARY,
            (
                "timed out",
                "timeout",
                "temporarily",
                "connection",
                "network",
                "http error 500",
                "domain not found",
            ),
            True,
        ),
    )
    for code, signals, retryable in patterns:
        if any(signal in lowered for signal in signals):
            return ProviderFailureV1(code, message, retryable)
    return ProviderFailureV1(
        ProviderFailureCode.PROVIDER_ERROR,
        message,
        False,
    )
