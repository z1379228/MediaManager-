"""Local-only Gopeed REST bridge and explicit P2P handoff feature."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from pathlib import Path
import re
import shutil
from threading import RLock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.downloads.direct_http_policy import direct_http_url_candidate
from core.transfers.policy import (
    GopeedBridgeConfig,
    P2PTransferPolicy,
    TransportBoundaryError,
    default_gopeed_bridge_config,
    default_p2p_transfer_policy,
    validate_gopeed_bridge_config,
    validate_p2p_transfer_policy,
)


MAX_GOPEED_RESPONSE_BYTES = 1024 * 1024
MAX_TRANSFER_URL_LENGTH = 4096
_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_TERMINAL_STATUSES = frozenset({"done", "error"})


class GopeedProtocolError(RuntimeError):
    """Stable error for a rejected or invalid local Gopeed response."""


Transport = Callable[[Request, int], bytes]


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _download_root(value: Path | str) -> Path:
    unresolved = Path(value).expanduser()
    if not unresolved.is_absolute() or _is_linklike(unresolved):
        raise TransportBoundaryError("download folder must be an ordinary absolute path")
    resolved = unresolved.resolve()
    if not resolved.is_dir():
        raise TransportBoundaryError("download folder must already exist")
    return resolved


def _http_url(value: object) -> str:
    if not direct_http_url_candidate(value):
        raise TransportBoundaryError(
            "Gopeed Bridge accepts only explicit HTTPS direct-file URLs outside "
            "existing website MOD domains"
        )
    return str(value)


def _p2p_url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TRANSFER_URL_LENGTH:
        raise TransportBoundaryError("P2P URL is invalid")
    lowered = value.casefold()
    if lowered.startswith("magnet:?") and "xt=urn:btih:" in lowered:
        return value
    if lowered.startswith("ed2k://|file|") and lowered.endswith("|/"):
        return value
    raise TransportBoundaryError("P2P Transfer accepts only explicit magnet or ed2k links")


def _safe_name(value: object) -> str:
    if value in {None, ""}:
        return ""
    if (
        not isinstance(value, str)
        or len(value) > 240
        or value in {".", ".."}
        or Path(value).name != value
        or any(character in value for character in '<>:"/\\|?*')
        or any(ord(character) < 32 for character in value)
    ):
        raise TransportBoundaryError("download name is invalid")
    return value


def _default_transport(request: Request, timeout: int) -> bytes:
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - endpoint validated localhost-only
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise GopeedProtocolError(f"Gopeed local API returned HTTP {status}")
            return response.read(MAX_GOPEED_RESPONSE_BYTES + 1)
    except HTTPError as error:
        raise GopeedProtocolError(
            f"Gopeed local API returned HTTP {error.code}"
        ) from error
    except (TimeoutError, URLError, OSError) as error:
        raise GopeedProtocolError("Gopeed local API is unavailable") from error


class GopeedBridgeService:
    """A feature-gated REST adapter that never starts or configures Gopeed."""

    provider_id = "gopeed-transfer"
    display_name = "Gopeed Bridge"
    available = True

    def __init__(self, *, transport: Transport = _default_transport) -> None:
        self._transport = transport
        self._enabled = False
        self._config = default_gopeed_bridge_config()
        self._lock = RLock()

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def is_configured(self) -> bool:
        with self._lock:
            return self._enabled and self._config.enabled

    @property
    def config(self) -> GopeedBridgeConfig:
        with self._lock:
            return self._config

    def set_enabled(self, enabled: bool) -> int:
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be boolean")
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._config = default_gopeed_bridge_config()
        # External Gopeed tasks are never cancelled implicitly.
        return 0

    def configure(self, value: object) -> None:
        config = validate_gopeed_bridge_config(value)
        with self._lock:
            if not self._enabled:
                raise RuntimeError("Gopeed Bridge MOD is disabled")
            self._config = config

    def close(self) -> None:
        self.set_enabled(False)

    def info(self) -> Mapping[str, Any]:
        data = self._request("GET", "/api/v1/info")
        if not isinstance(data, dict):
            raise GopeedProtocolError("Gopeed info response is invalid")
        return dict(data)

    def list_tasks(self) -> tuple[Mapping[str, Any], ...]:
        data = self._request("GET", "/api/v1/tasks")
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise GopeedProtocolError("Gopeed task list response is invalid")
        return tuple(dict(item) for item in data)

    def create_download(
        self,
        url: str,
        output_dir: Path | str,
        *,
        name: str = "",
    ) -> str:
        source = _http_url(url)
        output = _download_root(output_dir)
        self._ensure_capacity()
        return self._create_direct(source, output, _safe_name(name), "mediamanager-gopeed")

    def resolve_p2p(
        self,
        url: str,
        output_dir: Path | str,
        *,
        name: str = "",
    ) -> tuple[str, int]:
        source = _p2p_url(url)
        output = _download_root(output_dir)
        self._ensure_capacity()
        data = self._request(
            "POST",
            "/api/v1/resolve",
            {
                "req": self._request_model(source, "mediamanager-p2p"),
                "opts": self._options_model(output, _safe_name(name)),
            },
        )
        if not isinstance(data, dict) or not isinstance(data.get("id"), str):
            raise GopeedProtocolError("Gopeed resolve response is invalid")
        resolve_id = data["id"]
        if not _TASK_ID.fullmatch(resolve_id):
            raise GopeedProtocolError("Gopeed resolve id is invalid")
        resource = data.get("res")
        size = self._resource_size(resource)
        if size <= 0:
            raise GopeedProtocolError("Gopeed did not report a bounded P2P resource size")
        return resolve_id, size

    def create_resolved(self, resolve_id: str) -> str:
        if not isinstance(resolve_id, str) or not _TASK_ID.fullmatch(resolve_id):
            raise TransportBoundaryError("Gopeed resolve id is invalid")
        data = self._request("POST", "/api/v1/tasks", {"rid": resolve_id})
        return self._task_id(data)

    def pause_task(self, task_id: str) -> None:
        self._task_action(task_id, "pause")

    def continue_task(self, task_id: str) -> None:
        self._task_action(task_id, "continue")

    def delete_task(self, task_id: str) -> None:
        safe_id = self._validated_task_id(task_id)
        self._request(
            "DELETE",
            f"/api/v1/tasks/{quote(safe_id, safe='')}?force=false",
        )

    def _task_action(self, task_id: str, action: str) -> None:
        safe_id = self._validated_task_id(task_id)
        self._request(
            "PUT",
            f"/api/v1/tasks/{quote(safe_id, safe='')}/{action}",
        )

    def _create_direct(
        self, source: str, output: Path, name: str, source_label: str
    ) -> str:
        data = self._request(
            "POST",
            "/api/v1/tasks",
            {
                "req": self._request_model(source, source_label),
                "opts": self._options_model(output, name),
            },
        )
        return self._task_id(data)

    @staticmethod
    def _request_model(source: str, label: str) -> dict[str, object]:
        return {
            "url": source,
            "labels": {"source": label},
        }

    @staticmethod
    def _options_model(output: Path, name: str) -> dict[str, object]:
        return {"path": str(output), "name": name}

    @staticmethod
    def _resource_size(resource: object) -> int:
        if not isinstance(resource, dict):
            return 0
        size = resource.get("size", 0)
        if isinstance(size, int) and not isinstance(size, bool) and size > 0:
            return size
        files = resource.get("files", ())
        if not isinstance(files, list):
            return 0
        sizes = [
            item.get("size", 0)
            for item in files
            if isinstance(item, dict)
        ]
        if not sizes or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in sizes
        ):
            return 0
        return sum(sizes)

    def _ensure_capacity(self) -> None:
        with self._lock:
            limit = self._config.max_tasks
        active = sum(
            str(item.get("status", "")).casefold() not in _TERMINAL_STATUSES
            for item in self.list_tasks()
        )
        if active >= limit:
            raise TransportBoundaryError("Gopeed active task limit has been reached")

    @staticmethod
    def _validated_task_id(value: object) -> str:
        if not isinstance(value, str) or not _TASK_ID.fullmatch(value):
            raise TransportBoundaryError("Gopeed task id is invalid")
        return value

    @staticmethod
    def _task_id(value: object) -> str:
        if not isinstance(value, str) or not _TASK_ID.fullmatch(value):
            raise GopeedProtocolError("Gopeed task id response is invalid")
        return value

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
    ) -> object:
        with self._lock:
            if not self._enabled:
                raise RuntimeError("Gopeed Bridge MOD is disabled")
            config = self._config
        if not config.enabled:
            raise RuntimeError("Gopeed Bridge is not configured")
        body = None
        headers = {
            "Accept": "application/json",
            "X-Api-Token": config.token,
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            headers["Content-Type"] = "application/json"
        request = Request(
            config.endpoint + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            raw = self._transport(request, config.request_timeout_seconds)
        except GopeedProtocolError:
            raise
        except Exception as error:
            raise GopeedProtocolError("Gopeed local API request failed") from error
        if not isinstance(raw, bytes) or len(raw) > MAX_GOPEED_RESPONSE_BYTES:
            raise GopeedProtocolError("Gopeed response is too large")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as error:
            raise GopeedProtocolError("Gopeed response is not valid JSON") from error
        if (
            not isinstance(document, dict)
            or set(document) - {"code", "msg", "data"}
            or not isinstance(document.get("code"), int)
            or isinstance(document.get("code"), bool)
            or not isinstance(document.get("msg", ""), str)
        ):
            raise GopeedProtocolError("Gopeed response schema is invalid")
        if document["code"] != 0:
            message = " ".join(document.get("msg", "").split())[:240]
            if config.token:
                message = message.replace(config.token, "[REDACTED]")
            raise GopeedProtocolError(
                f"Gopeed API rejected the request ({document['code']})"
                + (f": {message}" if message else "")
            )
        return document.get("data")


class P2PTransferService:
    """Explicit magnet/ed2k workflow delegated to a configured Gopeed bridge."""

    provider_id = "p2p-transfer"
    display_name = "P2P Transfer"
    available = True

    def __init__(self, bridge: GopeedBridgeService) -> None:
        self.bridge = bridge
        self._enabled = False
        self._policy = default_p2p_transfer_policy()
        self._lock = RLock()

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def is_configured(self) -> bool:
        with self._lock:
            return self._enabled and self._policy.enabled

    @property
    def policy(self) -> P2PTransferPolicy:
        with self._lock:
            return self._policy

    def set_enabled(self, enabled: bool) -> int:
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be boolean")
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._policy = default_p2p_transfer_policy()
        return 0

    def configure(self, value: object) -> None:
        policy = validate_p2p_transfer_policy(value)
        with self._lock:
            if not self._enabled:
                raise RuntimeError("P2P Transfer MOD is disabled")
            self._policy = policy

    def submit(self, url: str, *, name: str = "") -> str:
        with self._lock:
            if not self._enabled:
                raise RuntimeError("P2P Transfer MOD is disabled")
            policy = self._policy
        if not policy.enabled or policy.storage_root is None:
            raise RuntimeError("P2P Transfer is not configured")
        resolve_id, size = self.bridge.resolve_p2p(
            url,
            policy.storage_root,
            name=name,
        )
        if size > policy.max_storage_bytes:
            raise TransportBoundaryError("P2P resource exceeds the configured storage limit")
        if shutil.disk_usage(policy.storage_root).free < size:
            raise TransportBoundaryError("P2P destination does not have enough free space")
        return self.bridge.create_resolved(resolve_id)

    def close(self) -> None:
        self.set_enabled(False)
