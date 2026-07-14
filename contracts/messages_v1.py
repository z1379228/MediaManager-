"""IPC v1 message contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestV1:
    protocol_version: str
    request_id: str
    plugin_id: str
    method: str
    timestamp: str
    payload: dict[str, Any]
    capability_token: str

