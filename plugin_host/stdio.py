"""Restore redirected standard streams for the windowed frozen host entry."""

from __future__ import annotations

import ctypes
import os
import sys
from typing import TextIO


def _windows_stream(identifier: int, mode: str) -> TextIO | None:
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.DuplicateHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.GetStdHandle(wintypes.DWORD(identifier))
    value = int(handle or 0)
    if value in {0, int(ctypes.c_void_p(-1).value or -1)}:
        return None
    duplicate = wintypes.HANDLE()
    if not kernel32.DuplicateHandle(
        kernel32.GetCurrentProcess(),
        wintypes.HANDLE(value),
        kernel32.GetCurrentProcess(),
        ctypes.byref(duplicate),
        0,
        False,
        0x00000002,
    ):
        return None
    flags = os.O_BINARY | (os.O_RDONLY if mode == "r" else os.O_WRONLY)
    try:
        descriptor = msvcrt.open_osfhandle(int(duplicate.value), flags)
    except OSError:
        kernel32.CloseHandle(duplicate)
        return None
    return os.fdopen(
        descriptor,
        mode,
        buffering=-1 if mode == "r" else 1,
        encoding="utf-8",
        errors="replace",
        newline="",
    )


def restore_frozen_host_stdio() -> bool:
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return True
    stdin = _windows_stream(-10, "r")
    stdout = _windows_stream(-11, "w")
    stderr = _windows_stream(-12, "w")
    if stdin is None or stdout is None or stderr is None:
        for stream in (stdin, stdout, stderr):
            if stream is not None:
                stream.close()
        return False
    sys.stdin = sys.__stdin__ = stdin
    sys.stdout = sys.__stdout__ = stdout
    sys.stderr = sys.__stderr__ = stderr
    return True


def restore_frozen_cli_stdio() -> bool:
    """Restore output pipes for frozen windowed CLI modes.

    PyInstaller's windowed executable may expose ``sys.stdout`` and
    ``sys.stderr`` as ``None`` even when a caller supplied redirected Windows
    handles. CLI-only modes do not need stdin, so requiring all three host
    streams would incorrectly turn ``--version`` and verification commands
    into a windowed traceback. Missing output handles fall back to the null
    device so those commands still terminate cleanly when launched without a
    console.
    """

    if os.name != "nt" or not getattr(sys, "frozen", False):
        return True
    stdout = _windows_stream(-11, "w")
    stderr = _windows_stream(-12, "w")
    real_output = stdout is not None and stderr is not None
    if stdout is None:
        stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if stderr is None:
        stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    sys.stdout = sys.__stdout__ = stdout
    sys.stderr = sys.__stderr__ = stderr
    return real_output
