"""Fail-closed policy contracts for the optional Gopeed and P2P MODs.

This module deliberately contains no network client, torrent engine, process
launcher, port opener, or token persistence. It validates the runtime MOD
configuration before an explicit user action may contact localhost Gopeed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


class TransportBoundaryError(ValueError):
    """Raised when an optional transport configuration crosses its boundary."""


_GOPEED_KEYS = frozenset(
    {
        "enabled",
        "endpoint",
        "token",
        "request_timeout_seconds",
        "max_tasks",
        "auto_start",
        "allow_remote",
    }
)
_P2P_KEYS = frozenset(
    {
        "enabled",
        "storage_root",
        "max_storage_bytes",
        "max_download_bps",
        "max_upload_bps",
        "legal_use_confirmed",
        "upload_enabled",
        "seeding_enabled",
        "search_enabled",
        "auto_port_forward",
        "listen_port",
    }
)
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MAX_TOKEN_LENGTH = 512
_MIN_TOKEN_LENGTH = 32
_MAX_REQUEST_TIMEOUT = 60
_MAX_TASKS = 16
_MIN_STORAGE_BYTES = 1 * 1024 * 1024
_MAX_STORAGE_BYTES = 1 * 1024**4
_MAX_BANDWIDTH = 10 * 1024**3


@dataclass(frozen=True, slots=True)
class GopeedBridgeConfig:
    """A local-only, user-started Gopeed API bridge configuration."""

    enabled: bool = False
    endpoint: str = "http://127.0.0.1:9999"
    token: str = field(default="", repr=False)
    request_timeout_seconds: int = 10
    max_tasks: int = 1
    auto_start: bool = False
    allow_remote: bool = False


@dataclass(frozen=True, slots=True)
class P2PTransferPolicy:
    """Bounded policy data for the separately gated P2P runtime MOD."""

    enabled: bool = False
    storage_root: Path | None = None
    max_storage_bytes: int = 0
    max_download_bps: int = 0
    max_upload_bps: int = 0
    legal_use_confirmed: bool = False
    upload_enabled: bool = False
    seeding_enabled: bool = False
    search_enabled: bool = False
    auto_port_forward: bool = False
    listen_port: int | None = None


def _mapping(value: object, keys: frozenset[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TransportBoundaryError(f"{name} configuration must be an object")
    if set(value) - keys:
        raise TransportBoundaryError(f"{name} configuration contains unknown fields")
    return value


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise TransportBoundaryError(f"{field} must be boolean")
    return value


def _bounded_int(value: object, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TransportBoundaryError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise TransportBoundaryError(f"{field} is outside the allowed range")
    return value


def _local_endpoint(value: object) -> str:
    if not isinstance(value, str) or len(value) > 256:
        raise TransportBoundaryError("Gopeed endpoint is invalid")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise TransportBoundaryError("Gopeed endpoint is invalid") from error
    if (
        parsed.scheme not in {"http", "https"}
        or (parsed.hostname or "").casefold() not in _LOCAL_HOSTS
        or port is None
        or not 1 <= port <= 65535
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise TransportBoundaryError(
            "Gopeed endpoint must be an explicit localhost URL with no credentials"
        )
    host = "[::1]" if parsed.hostname == "::1" else parsed.hostname
    return f"{parsed.scheme}://{host}:{port}"


def _token(value: object) -> str:
    if not isinstance(value, str) or not _MIN_TOKEN_LENGTH <= len(value) <= _MAX_TOKEN_LENGTH:
        raise TransportBoundaryError("Gopeed API token length is invalid")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise TransportBoundaryError("Gopeed API token contains unsafe characters")
    return value


def default_gopeed_bridge_config() -> GopeedBridgeConfig:
    """Return the safe default: disabled, local-only, and never auto-started."""

    return GopeedBridgeConfig()


def validate_gopeed_bridge_config(value: object) -> GopeedBridgeConfig:
    """Validate a Gopeed bridge config without connecting to Gopeed."""

    raw = _mapping(value, _GOPEED_KEYS, "Gopeed")
    enabled = _bool(raw.get("enabled", False), "Gopeed enabled")
    endpoint = _local_endpoint(raw.get("endpoint", "http://127.0.0.1:9999"))
    token_value = raw.get("token", "")
    token = _token(token_value) if enabled else ""
    timeout = _bounded_int(
        raw.get("request_timeout_seconds", 10),
        "Gopeed request_timeout_seconds",
        1,
        _MAX_REQUEST_TIMEOUT,
    )
    max_tasks = _bounded_int(raw.get("max_tasks", 1), "Gopeed max_tasks", 1, _MAX_TASKS)
    auto_start = _bool(raw.get("auto_start", False), "Gopeed auto_start")
    allow_remote = _bool(raw.get("allow_remote", False), "Gopeed allow_remote")
    if auto_start:
        raise TransportBoundaryError("Gopeed auto-start is disabled by policy")
    if allow_remote:
        raise TransportBoundaryError("Gopeed remote endpoints are disabled by policy")
    if not enabled and token_value not in {"", None}:
        raise TransportBoundaryError("disabled Gopeed bridge must not retain an API token")
    return GopeedBridgeConfig(
        enabled,
        endpoint,
        token,
        timeout,
        max_tasks,
        auto_start,
        allow_remote,
    )


def _storage_root(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise TransportBoundaryError("P2P storage_root is required")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise TransportBoundaryError("P2P storage_root must be absolute")
    resolved = path.resolve()
    if resolved.exists() and resolved.is_symlink():
        raise TransportBoundaryError("P2P storage_root cannot be a symlink")
    if resolved.exists() and not resolved.is_dir():
        raise TransportBoundaryError("P2P storage_root must be a directory")
    return resolved


def default_p2p_transfer_policy() -> P2PTransferPolicy:
    """Return the safe default: disabled and with no network side effects."""

    return P2PTransferPolicy()


def validate_p2p_transfer_policy(value: object) -> P2PTransferPolicy:
    """Validate P2P limits and explicit legal/network choices.

    This does not start an engine.  It rejects built-in search and automatic
    port forwarding; the runtime MOD therefore exposes only explicit,
    user-supplied links through its trusted UI.
    """

    raw = _mapping(value, _P2P_KEYS, "P2P")
    enabled = _bool(raw.get("enabled", False), "P2P enabled")
    search_enabled = _bool(raw.get("search_enabled", False), "P2P search_enabled")
    auto_port_forward = _bool(
        raw.get("auto_port_forward", False), "P2P auto_port_forward"
    )
    if search_enabled:
        raise TransportBoundaryError("P2P built-in torrent search is disabled by policy")
    if auto_port_forward:
        raise TransportBoundaryError("P2P automatic port forwarding is disabled by policy")
    if not enabled:
        if any(
            raw.get(field, False)
            for field in ("legal_use_confirmed", "upload_enabled", "seeding_enabled")
        ):
            raise TransportBoundaryError("disabled P2P policy cannot enable transfers")
        return P2PTransferPolicy(
            search_enabled=False,
            auto_port_forward=False,
        )
    storage_root = _storage_root(raw.get("storage_root"))
    storage_limit = _bounded_int(
        raw.get("max_storage_bytes"),
        "P2P max_storage_bytes",
        _MIN_STORAGE_BYTES,
        _MAX_STORAGE_BYTES,
    )
    download_limit = _bounded_int(
        raw.get("max_download_bps"),
        "P2P max_download_bps",
        1,
        _MAX_BANDWIDTH,
    )
    upload_limit = _bounded_int(
        raw.get("max_upload_bps", 0),
        "P2P max_upload_bps",
        0,
        _MAX_BANDWIDTH,
    )
    legal_use_confirmed = _bool(
        raw.get("legal_use_confirmed", False), "P2P legal_use_confirmed"
    )
    upload_enabled = _bool(raw.get("upload_enabled", False), "P2P upload_enabled")
    seeding_enabled = _bool(raw.get("seeding_enabled", False), "P2P seeding_enabled")
    if not legal_use_confirmed:
        raise TransportBoundaryError("P2P requires explicit legal-use confirmation")
    if not upload_enabled or upload_limit <= 0:
        raise TransportBoundaryError(
            "P2P requires explicit upload acknowledgement and a positive upload limit"
        )
    if seeding_enabled and (not upload_enabled or upload_limit <= 0):
        raise TransportBoundaryError("P2P seeding requires an upload limit")
    listen_port_value = raw.get("listen_port")
    listen_port = (
        None
        if listen_port_value is None
        else _bounded_int(listen_port_value, "P2P listen_port", 1024, 65535)
    )
    return P2PTransferPolicy(
        enabled,
        storage_root,
        storage_limit,
        download_limit,
        upload_limit,
        legal_use_confirmed,
        upload_enabled,
        seeding_enabled,
        False,
        False,
        listen_port,
    )
