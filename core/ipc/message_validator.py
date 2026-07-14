"""Schema, replay, timestamp, method and capability validation."""

from __future__ import annotations

from datetime import UTC, datetime
import threading
from typing import Any
from uuid import UUID

from contracts.messages_v1 import RequestV1
from core.ipc.errors import IPCValidationError
from core.ipc.protocol import METHOD_CAPABILITIES, PROTOCOL_VERSION
from core.ipc.rate_limiter import RateLimiter
from core.plugins.capability_manager import CapabilityManager


class MessageValidator:
    def __init__(self, capabilities: CapabilityManager, *, max_payload_chars: int = 1_000_000) -> None:
        self.capabilities, self.max_payload_chars = capabilities, max_payload_chars
        self.rate_limiter = RateLimiter()
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def validate(self, raw: dict[str, Any], *, process_id: int) -> RequestV1:
        required = set(RequestV1.__dataclass_fields__)
        if set(raw) != required:
            raise IPCValidationError("message fields invalid")
        try:
            request = RequestV1(**raw)
            UUID(request.request_id)
            timestamp = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
        except (TypeError, ValueError) as error:
            raise IPCValidationError("invalid request id or timestamp") from error
        if request.protocol_version != PROTOCOL_VERSION or request.method not in METHOD_CAPABILITIES:
            raise IPCValidationError("protocol or method not allowed")
        if not isinstance(request.payload, dict) or len(repr(request.payload)) > self.max_payload_chars:
            raise IPCValidationError("payload invalid or too large")
        now = datetime.now(UTC)
        if timestamp.tzinfo is None or abs((now - timestamp).total_seconds()) > 60:
            raise IPCValidationError("stale request")
        capability = METHOD_CAPABILITIES[request.method]
        if not self.capabilities.verify(request.capability_token, plugin_id=request.plugin_id, process_id=process_id, capability=capability):
            raise IPCValidationError("capability denied")
        with self._lock:
            if request.request_id in self._seen:
                raise IPCValidationError("replayed request")
            identity = f"{request.plugin_id}:{process_id}"
            if not self.rate_limiter.allow(identity):
                raise IPCValidationError("rate limit exceeded")
            self._seen[request.request_id] = now.timestamp()
            self._seen = {
                key: seen
                for key, seen in self._seen.items()
                if now.timestamp() - seen < 120
            }
        return request
