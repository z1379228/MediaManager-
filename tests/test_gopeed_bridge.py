from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

import pytest

from core.transfers import (
    GopeedBridgeService,
    GopeedProtocolError,
    MAX_GOPEED_RESPONSE_BYTES,
    P2PTransferService,
    TransportBoundaryError,
)


class RecordingTransport:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[Request, int]] = []

    def __call__(self, request: Request, timeout: int) -> bytes:
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, bytes):
            return response
        return json.dumps(response).encode("utf-8")


def configured_bridge(transport: RecordingTransport) -> GopeedBridgeService:
    bridge = GopeedBridgeService(transport=transport)
    bridge.set_enabled(True)
    bridge.configure(
        {
            "enabled": True,
            "endpoint": "http://127.0.0.1:9999",
            "token": "A" * 32,
            "max_tasks": 4,
        }
    )
    return bridge


def request_payload(request: Request) -> dict[str, object]:
    return json.loads((request.data or b"{}").decode("utf-8"))


def test_gopeed_bridge_has_no_startup_network_or_token_persistence() -> None:
    transport = RecordingTransport()
    bridge = GopeedBridgeService(transport=transport)

    assert bridge.is_enabled is False
    assert bridge.is_configured is False
    assert transport.requests == []

    bridge.set_enabled(True)
    bridge.configure(
        {
            "enabled": True,
            "endpoint": "http://localhost:9999",
            "token": "B" * 32,
        }
    )
    bridge.set_enabled(False)

    assert bridge.is_configured is False
    assert bridge.config.token == ""
    assert transport.requests == []


def test_gopeed_bridge_uses_official_local_api_contract(tmp_path: Path) -> None:
    transport = RecordingTransport(
        {"code": 0, "msg": "", "data": []},
        {"code": 0, "msg": "", "data": "task-123"},
    )
    bridge = configured_bridge(transport)

    task_id = bridge.create_download(
        "https://downloads.example.org/archive.zip",
        tmp_path,
        name="archive.zip",
    )

    assert task_id == "task-123"
    list_request, create_request = (item[0] for item in transport.requests)
    assert list_request.full_url == "http://127.0.0.1:9999/api/v1/tasks"
    assert create_request.full_url == "http://127.0.0.1:9999/api/v1/tasks"
    assert create_request.method == "POST"
    assert create_request.get_header("X-api-token") == "A" * 32
    assert request_payload(create_request) == {
        "req": {
            "url": "https://downloads.example.org/archive.zip",
            "labels": {"source": "mediamanager-gopeed"},
        },
        "opts": {"path": str(tmp_path.resolve()), "name": "archive.zip"},
    }


def test_gopeed_bridge_bounds_and_redacts_errors() -> None:
    oversized = b"{" + b"x" * MAX_GOPEED_RESPONSE_BYTES + b"}"
    bridge = configured_bridge(RecordingTransport(oversized))
    with pytest.raises(GopeedProtocolError, match="response is too large"):
        bridge.info()

    token = "A" * 32
    bridge = configured_bridge(
        RecordingTransport({"code": 1001, "msg": f"bad {token}", "data": None})
    )
    with pytest.raises(GopeedProtocolError) as error:
        bridge.info()
    assert token not in str(error.value)


@pytest.mark.parametrize(
    "url",
    (
        "file:///C:/secret.txt",
        "http://downloads.example.org/file.zip",
        "https://user:pass@example.org/file.zip",
        "https://127.0.0.1/file.zip",
        "https://ani.gamer.com.tw/file.zip",
        "https://downloads.example.org/page",
        "magnet:?xt=urn:btih:abcdef",
    ),
)
def test_gopeed_http_download_reuses_direct_file_security_boundary(
    tmp_path: Path, url: str
) -> None:
    bridge = configured_bridge(RecordingTransport())
    with pytest.raises(TransportBoundaryError):
        bridge.create_download(url, tmp_path)


def test_p2p_transfer_resolves_size_before_creating_task(tmp_path: Path) -> None:
    transport = RecordingTransport(
        {"code": 0, "msg": "", "data": []},
        {
            "code": 0,
            "msg": "",
            "data": {"id": "resolve-1", "res": {"size": 4096, "files": []}},
        },
        {"code": 0, "msg": "", "data": "p2p-task"},
    )
    bridge = configured_bridge(transport)
    p2p = P2PTransferService(bridge)
    p2p.set_enabled(True)
    p2p.configure(
        {
            "enabled": True,
            "storage_root": str(tmp_path),
            "max_storage_bytes": 1024**3,
            "max_download_bps": 10 * 1024**2,
            "max_upload_bps": 1024**2,
            "legal_use_confirmed": True,
            "upload_enabled": True,
        }
    )

    assert p2p.submit("magnet:?xt=urn:btih:abcdef", name="example") == "p2p-task"
    _, resolve_request, create_request = (item[0] for item in transport.requests)
    assert resolve_request.full_url.endswith("/api/v1/resolve")
    assert request_payload(resolve_request)["req"] == {
        "url": "magnet:?xt=urn:btih:abcdef",
        "labels": {"source": "mediamanager-p2p"},
    }
    assert request_payload(create_request) == {"rid": "resolve-1"}


def test_p2p_transfer_requires_explicit_upload_and_capacity(tmp_path: Path) -> None:
    bridge = configured_bridge(RecordingTransport())
    p2p = P2PTransferService(bridge)
    p2p.set_enabled(True)
    base = {
        "enabled": True,
        "storage_root": str(tmp_path),
        "max_storage_bytes": 1024**3,
        "max_download_bps": 1024,
        "legal_use_confirmed": True,
    }
    with pytest.raises(TransportBoundaryError, match="upload"):
        p2p.configure(base)

    transport = RecordingTransport(
        {"code": 0, "msg": "", "data": []},
        {
            "code": 0,
            "msg": "",
            "data": {"id": "resolve-1", "res": {"size": 2 * 1024**3}},
        },
    )
    bridge = configured_bridge(transport)
    p2p = P2PTransferService(bridge)
    p2p.set_enabled(True)
    p2p.configure(
        {
            **base,
            "max_upload_bps": 1024,
            "upload_enabled": True,
        }
    )
    with pytest.raises(TransportBoundaryError, match="storage limit"):
        p2p.submit("ed2k://|file|example.bin|123|hash|/")


def test_gopeed_task_controls_never_force_delete_files() -> None:
    bridge = configured_bridge(
        RecordingTransport({"code": 0, "msg": "", "data": None})
    )
    bridge.delete_task("task_123")
    request = bridge._transport.requests[0][0]
    assert request.method == "DELETE"
    assert request.full_url.endswith("/api/v1/tasks/task_123?force=false")
