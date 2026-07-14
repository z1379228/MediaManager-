"""Transport-neutral IPC dispatch boundary.

The Windows Named Pipe transport will call this service after obtaining the
client process identity from the pipe. No localhost TCP listener is used.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.ipc.message_validator import MessageValidator


class IPCServer:
    def __init__(self, validator: MessageValidator) -> None:
        self.validator = validator
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(self, method: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self._handlers[method] = handler

    def dispatch(self, message: dict[str, Any], *, process_id: int) -> Any:
        request = self.validator.validate(message, process_id=process_id)
        handler = self._handlers.get(request.method)
        if handler is None:
            raise LookupError(request.method)
        return handler(request.payload)

