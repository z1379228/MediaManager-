from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

import core.plugins.lifecycle as lifecycle_module
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.lifecycle import PluginLifecyclePathError, resolve_lifecycle_path
from core.settings import SettingsWriteBlockedError


def test_lifecycle_lock_is_reentrant_for_one_shared_owner(tmp_path: Path) -> None:
    lock = PluginLifecycleLock(tmp_path / "mod")

    with lock.hold():
        with lock.hold():
            pass


def test_lifecycle_lock_maps_bounded_file_lock_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def blocked_lock(*_args: object, **_kwargs: object) -> Iterator[None]:
        raise SettingsWriteBlockedError("busy")
        yield

    monkeypatch.setattr(lifecycle_module, "settings_file_lock", blocked_lock)
    lock = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)

    with pytest.raises(PluginLifecycleLockError, match="unavailable"):
        with lock.hold():
            pass


def test_lifecycle_lock_rejects_unbounded_timeout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite"):
        PluginLifecycleLock(tmp_path / "mod", timeout_seconds=float("inf"))

    with pytest.raises(ValueError, match="platform maximum"):
        PluginLifecycleLock(
            tmp_path / "mod",
            timeout_seconds=threading.TIMEOUT_MAX + 1,
        )


def test_lifecycle_lock_serializes_independent_instances(tmp_path: Path) -> None:
    first = PluginLifecycleLock(tmp_path / "mod")
    second = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)

    with first.hold():
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with second.hold():
                pass


def test_lifecycle_lock_maps_path_creation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def denied_lock(*_args: object, **_kwargs: object) -> Iterator[None]:
        raise OSError("access denied")
        yield

    monkeypatch.setattr(lifecycle_module, "settings_file_lock", denied_lock)
    lock = PluginLifecycleLock(tmp_path / "mod")

    with pytest.raises(PluginLifecycleLockError, match="unavailable") as error:
        with lock.hold():
            pass

    assert isinstance(error.value.__cause__, OSError)


def test_lifecycle_path_rejects_traversal(tmp_path: Path) -> None:
    mod_root = tmp_path / "mod"
    mod_root.mkdir()

    with pytest.raises(PluginLifecyclePathError, match="unsafe parts"):
        resolve_lifecycle_path(mod_root, "installed", "..", "outside")


def test_lifecycle_path_rejects_existing_reparse_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod_root = tmp_path / "mod"
    installed = mod_root / "installed"
    installed.mkdir(parents=True)
    original = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path == installed or original(path),
    )

    with pytest.raises(PluginLifecyclePathError, match="reparse point"):
        resolve_lifecycle_path(mod_root, "installed", "example.plugin")
