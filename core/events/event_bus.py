"""Small synchronous event bus for trusted core components."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event].append(handler)

    def publish(self, event: str, payload: Any = None) -> None:
        for handler in tuple(self._handlers[event]):
            handler(payload)

