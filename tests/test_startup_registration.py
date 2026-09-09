from __future__ import annotations

from pathlib import Path
import subprocess

from core.startup_registration import (
    StartupRegistration,
    build_startup_command,
    startup_registration_supported,
)


class MemoryRunKey:
    def __init__(self) -> None:
        self.value: str | None = None

    def read(self, name: str) -> str | None:
        assert name == "MediaManager"
        return self.value

    def write(self, name: str, value: str) -> None:
        assert name == "MediaManager"
        self.value = value

    def delete(self, name: str) -> None:
        assert name == "MediaManager"
        self.value = None


def test_frozen_startup_command_uses_the_executable_directly(tmp_path: Path) -> None:
    executable = tmp_path / "Media Manager.exe"

    command = build_startup_command(executable, frozen=True)

    assert command == subprocess.list2cmdline(
        [str(executable.resolve()), "--start-minimized"]
    )


def test_source_startup_command_prefers_pythonw(tmp_path: Path) -> None:
    executable = tmp_path / "python.exe"
    pythonw = tmp_path / "pythonw.exe"
    pythonw.write_bytes(b"")
    script = tmp_path / "Media Manager" / "main.py"

    command = build_startup_command(
        executable,
        frozen=False,
        application_script=script,
    )

    assert command == subprocess.list2cmdline(
        [str(pythonw.resolve()), str(script.resolve()), "--start-minimized"]
    )


def test_portable_startup_command_preserves_the_data_mode(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "MediaManager.exe"

    command = build_startup_command(
        executable,
        frozen=True,
        portable=True,
    )

    assert command == subprocess.list2cmdline(
        [str(executable.resolve()), "--portable", "--start-minimized"]
    )


def test_registration_is_idempotent_and_restorable() -> None:
    backend = MemoryRunKey()
    registration = StartupRegistration(
        '"C:\\MediaManager.exe" --start-minimized',
        backend,
    )

    assert registration.registered_command() is None
    assert not registration.is_enabled()

    registration.set_enabled(True)
    assert registration.is_enabled()
    saved = registration.registered_command()

    registration.set_enabled(False)
    assert registration.registered_command() is None

    registration.restore(saved)
    assert registration.is_enabled()


def test_startup_registration_is_windows_only() -> None:
    assert startup_registration_supported("nt")
    assert not startup_registration_supported("posix")
