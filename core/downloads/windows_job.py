"""Windows Job Object containment for provider process trees."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


class ProviderJobError(RuntimeError):
    pass


if os.name == "nt":
    ULONG_PTR = ctypes.c_size_t
    SIZE_T = ctypes.c_size_t

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", SIZE_T),
            ("MaximumWorkingSetSize", SIZE_T),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ULONG_PTR),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", SIZE_T),
            ("JobMemoryLimit", SIZE_T),
            ("PeakProcessMemoryUsed", SIZE_T),
            ("PeakJobMemoryUsed", SIZE_T),
        ]


class ProviderJob:
    _ACTIVE_PROCESS = 0x00000008
    _PROCESS_MEMORY = 0x00000100
    _KILL_ON_CLOSE = 0x00002000
    _EXTENDED_LIMIT_INFORMATION = 9

    def __init__(
        self,
        *,
        active_process_limit: int = 4,
        process_memory_limit: int = 2 * 1024**3,
    ) -> None:
        self._handle: int | None = None
        if os.name != "nt":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise ProviderJobError(f"CreateJobObject failed: {ctypes.get_last_error()}")
        information = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        information.BasicLimitInformation.LimitFlags = (
            self._ACTIVE_PROCESS | self._PROCESS_MEMORY | self._KILL_ON_CLOSE
        )
        information.BasicLimitInformation.ActiveProcessLimit = max(
            1, active_process_limit
        )
        information.ProcessMemoryLimit = max(256 * 1024**2, process_memory_limit)
        if not kernel32.SetInformationJobObject(
            handle,
            self._EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(information),
            ctypes.sizeof(information),
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise ProviderJobError(f"SetInformationJobObject failed: {error}")
        self._handle = int(handle)

    def assign(self, process_handle: int) -> None:
        if self._handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel32.AssignProcessToJobObject(
            wintypes.HANDLE(self._handle), wintypes.HANDLE(process_handle)
        ):
            raise ProviderJobError(
                f"AssignProcessToJobObject failed: {ctypes.get_last_error()}"
            )

    def close(self) -> None:
        if self._handle is None:
            return
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(
            wintypes.HANDLE(self._handle)
        )
        self._handle = None

    def __enter__(self) -> "ProviderJob":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
