"""Bounded coordinator shared by external plugin lifecycle operations."""

from __future__ import annotations

import math
import os
import stat
import threading
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Iterator

from core.settings import SettingsWriteBlockedError, settings_file_lock

PLUGIN_LIFECYCLE_LOCK_TIMEOUT_SECONDS = 2.0


class PluginLifecycleLockError(RuntimeError):
    """Raised before lifecycle mutation when the shared lock is unavailable."""


class PluginLifecyclePathError(RuntimeError):
    """Raised before mutation when a lifecycle path is not root-owned."""


def resolve_lifecycle_path(mod_root: Path, *parts: str) -> Path:
    """Resolve one root-owned path while rejecting traversal and reparse aliases."""

    root = Path(os.path.abspath(mod_root))
    if any(
        not part
        or part in {".", ".."}
        or bool(Path(part).drive)
        or bool(Path(part).root)
        or len(Path(part).parts) != 1
        or Path(part).name != part
        for part in parts
    ):
        raise PluginLifecyclePathError("plugin lifecycle path contains unsafe parts")
    candidate = root.joinpath(*parts)
    current = root
    try:
        if _is_reparse_point(current):
            raise PluginLifecyclePathError(
                "plugin lifecycle path contains a reparse point"
            )
        for part in parts:
            current /= part
            if _is_reparse_point(current):
                raise PluginLifecyclePathError(
                    "plugin lifecycle path contains a reparse point"
                )
            if not current.exists():
                break
        resolved_root = root.resolve()
        resolved_candidate = candidate.resolve()
    except PluginLifecyclePathError:
        raise
    except OSError as error:
        raise PluginLifecyclePathError(
            "plugin lifecycle path could not be verified"
        ) from error
    if not resolved_candidate.is_relative_to(resolved_root):
        raise PluginLifecyclePathError("plugin lifecycle path escapes the MOD root")
    return resolved_candidate


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


class PluginLifecycleLock:
    """Hold one reentrant process lock plus the shared on-disk OS lock."""

    def __init__(
        self,
        mod_root: Path,
        *,
        timeout_seconds: float = PLUGIN_LIFECYCLE_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        timeout = float(timeout_seconds)
        if (
            not math.isfinite(timeout)
            or timeout < 0
            or timeout > threading.TIMEOUT_MAX
        ):
            raise ValueError(
                "plugin lifecycle lock timeout must be finite, non-negative, and within "
                "the platform maximum"
            )
        self.timeout_seconds = timeout
        self._sentinel = Path(os.path.abspath(mod_root)) / "plugin-lifecycle"
        self._thread_lock = threading.RLock()
        self._local = threading.local()

    @contextmanager
    def hold(self) -> Iterator[None]:
        """Acquire within the configured deadline and release after the operation."""

        deadline = time.monotonic() + self.timeout_seconds
        if not self._thread_lock.acquire(timeout=self.timeout_seconds):
            raise PluginLifecycleLockError("plugin lifecycle lock timed out")
        try:
            depth = int(getattr(self._local, "depth", 0))
            if depth:
                self._local.depth = depth + 1
                try:
                    yield
                finally:
                    self._local.depth = depth
                return

            remaining = max(0.0, deadline - time.monotonic())
            stack = ExitStack()
            try:
                stack.enter_context(
                    settings_file_lock(
                        self._sentinel,
                        timeout_seconds=remaining,
                    )
                )
            except (SettingsWriteBlockedError, OSError) as error:
                stack.close()
                raise PluginLifecycleLockError(
                    "plugin lifecycle lock is unavailable"
                ) from error
            with stack:
                self._local.depth = 1
                try:
                    yield
                finally:
                    self._local.depth = 0
        finally:
            self._thread_lock.release()
