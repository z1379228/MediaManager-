"""Lifecycle callback registry."""

from __future__ import annotations

from collections.abc import Callable


class Lifecycle:
    def __init__(self) -> None:
        self._shutdown_callbacks: list[Callable[[], None]] = []

    def on_shutdown(self, callback: Callable[[], None]) -> None:
        self._shutdown_callbacks.append(callback)

    def shutdown(self) -> None:
        for callback in reversed(self._shutdown_callbacks):
            callback()

