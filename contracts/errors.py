"""Stable cross-process error identifiers."""

from enum import StrEnum


class ErrorCode(StrEnum):
    IPC_INVALID = "IPC_INVALID"
    PLUGIN_PERMISSION_DENIED = "PLUGIN_PERMISSION_DENIED"
    PLUGIN_TIMEOUT = "PLUGIN_TIMEOUT"
    PLUGIN_CRASHED = "PLUGIN_CRASHED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"

