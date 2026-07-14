from __future__ import annotations

import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.ipc.errors import IPCValidationError
from core.ipc.message_validator import MessageValidator
from core.ipc.rate_limiter import RateLimiter
from core.plugins.capability_manager import CapabilityManager


def request(token: str, *, request_id: str | None = None) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "request_id": request_id or str(uuid4()),
        "plugin_id": "example.plugin",
        "method": "media.analyze",
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": {},
        "capability_token": token,
    }


def test_invalid_tokens_do_not_consume_authenticated_rate_limit() -> None:
    capabilities = CapabilityManager(b"k" * 32)
    validator = MessageValidator(capabilities)
    validator.rate_limiter = RateLimiter(limit=1, window_seconds=60)

    with pytest.raises(IPCValidationError, match="capability denied"):
        validator.validate(request("invalid"), process_id=10)

    token = capabilities.issue("example.plugin", 10, ("task.propose",))
    assert validator.validate(request(token), process_id=10).plugin_id == "example.plugin"


def test_concurrent_replay_allows_exactly_one_request() -> None:
    barrier = threading.Barrier(2)

    class BarrierCapabilities:
        def verify(self, *args, **kwargs):
            barrier.wait(timeout=2)
            return object()

    validator = MessageValidator(BarrierCapabilities())  # type: ignore[arg-type]
    raw = request("accepted", request_id=str(uuid4()))
    results: list[str] = []

    def validate() -> None:
        try:
            validator.validate(raw, process_id=10)
            results.append("accepted")
        except IPCValidationError as error:
            results.append(str(error))

    threads = [threading.Thread(target=validate) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(results) == ["accepted", "replayed request"]
