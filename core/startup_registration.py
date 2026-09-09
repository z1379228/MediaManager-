"""Optional per-user Windows startup registration without shell execution."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Protocol


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "MediaManager"
MAX_STARTUP_COMMAND_LENGTH = 4096


class StartupRegistrationError(OSError):
    """Raised when the per-user startup registration cannot be updated safely."""


class RunKeyBackend(Protocol):
    def read(self, name: str) -> str | None: ...

    def write(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class WindowsRunKey:
    """Narrow HKCU Run adapter; this never requests administrator access."""

    def read(self, name: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY_PATH,
                0,
                winreg.KEY_QUERY_VALUE,
            ) as key:
                value, value_type = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
        if value_type not in {winreg.REG_SZ, winreg.REG_EXPAND_SZ}:
            return None
        return value if isinstance(value, str) else None

    def write(self, name: str, value: str) -> None:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete(self, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            return


def startup_registration_supported(platform: str | None = None) -> bool:
    return (os.name if platform is None else platform) == "nt"


def build_startup_command(
    executable: Path,
    *,
    frozen: bool,
    application_script: Path | None = None,
    portable: bool = False,
) -> str:
    """Build one quoted command from trusted local application paths."""

    executable = executable.expanduser().resolve()
    if frozen:
        arguments = [str(executable)]
    else:
        if application_script is None:
            raise ValueError("source startup requires the application script")
        pythonw = executable.with_name("pythonw.exe")
        launcher = pythonw if pythonw.is_file() else executable
        arguments = [str(launcher), str(application_script.expanduser().resolve())]
    if portable:
        arguments.append("--portable")
    arguments.append("--start-minimized")
    command = subprocess.list2cmdline(arguments)
    if (
        not command
        or len(command) > MAX_STARTUP_COMMAND_LENGTH
        or "\x00" in command
        or "\n" in command
        or "\r" in command
    ):
        raise StartupRegistrationError("startup command is invalid or too long")
    return command


def current_application_startup_command(*, portable: bool = False) -> str:
    frozen = bool(getattr(sys, "frozen", False))
    script = None if frozen else Path(__file__).resolve().parents[1] / "main.py"
    return build_startup_command(
        Path(sys.executable),
        frozen=frozen,
        application_script=script,
        portable=portable,
    )


class StartupRegistration:
    def __init__(self, command: str, backend: RunKeyBackend) -> None:
        if (
            not command
            or len(command) > MAX_STARTUP_COMMAND_LENGTH
            or any(character in command for character in ("\x00", "\n", "\r"))
        ):
            raise StartupRegistrationError("startup command is invalid or too long")
        self.command = command
        self.backend = backend

    def registered_command(self) -> str | None:
        return self.backend.read(RUN_VALUE_NAME)

    def is_enabled(self) -> bool:
        return self.registered_command() == self.command

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.backend.write(RUN_VALUE_NAME, self.command)
        else:
            self.backend.delete(RUN_VALUE_NAME)

    def restore(self, command: str | None) -> None:
        if command is None:
            self.backend.delete(RUN_VALUE_NAME)
        else:
            self.backend.write(RUN_VALUE_NAME, command)


def create_startup_registration(
    *, portable: bool = False
) -> StartupRegistration | None:
    if not startup_registration_supported():
        return None
    return StartupRegistration(
        current_application_startup_command(portable=portable),
        WindowsRunKey(),
    )
