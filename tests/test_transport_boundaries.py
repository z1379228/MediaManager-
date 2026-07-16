from __future__ import annotations

from pathlib import Path

import pytest

from core.transfers import (
    TransportBoundaryError,
    default_gopeed_bridge_config,
    default_p2p_transfer_policy,
    validate_gopeed_bridge_config,
    validate_p2p_transfer_policy,
)


def test_optional_transports_are_disabled_without_side_effects() -> None:
    gopeed = default_gopeed_bridge_config()
    p2p = default_p2p_transfer_policy()

    assert not gopeed.enabled
    assert not gopeed.auto_start
    assert not gopeed.allow_remote
    assert gopeed.token == ""
    assert not p2p.enabled
    assert p2p.storage_root is None
    assert not p2p.upload_enabled
    assert not p2p.seeding_enabled
    assert not p2p.search_enabled
    assert not p2p.auto_port_forward


def test_gopeed_requires_local_endpoint_and_ephemeral_explicit_token() -> None:
    token = "A" * 32
    config = validate_gopeed_bridge_config(
        {
            "enabled": True,
            "endpoint": "http://127.0.0.1:9999/",
            "token": token,
            "max_tasks": 4,
        }
    )

    assert config.enabled
    assert config.endpoint == "http://127.0.0.1:9999"
    assert config.token == token
    assert config.max_tasks == 4


@pytest.mark.parametrize(
    "value",
    (
        {"enabled": True, "endpoint": "http://192.168.1.5:9999", "token": "A" * 32},
        {"enabled": True, "endpoint": "http://127.0.0.1:9999", "token": "short"},
        {"enabled": True, "endpoint": "http://127.0.0.1:9999", "token": "A" * 32, "auto_start": True},
        {"enabled": True, "endpoint": "http://127.0.0.1:9999", "token": "A" * 32, "allow_remote": True},
        {"enabled": False, "token": "A" * 32},
    ),
)
def test_gopeed_rejects_remote_autostart_or_persisted_disabled_token(value) -> None:
    with pytest.raises(TransportBoundaryError):
        validate_gopeed_bridge_config(value)


def test_p2p_requires_legal_confirmation_and_bounded_storage(tmp_path: Path) -> None:
    policy = validate_p2p_transfer_policy(
        {
            "enabled": True,
            "storage_root": str(tmp_path),
            "max_storage_bytes": 2 * 1024**3,
            "max_download_bps": 10 * 1024**2,
            "legal_use_confirmed": True,
            "listen_port": 51413,
        }
    )

    assert policy.enabled
    assert policy.storage_root == tmp_path.resolve()
    assert policy.max_storage_bytes == 2 * 1024**3
    assert policy.max_upload_bps == 0
    assert policy.listen_port == 51413


@pytest.mark.parametrize(
    "value",
    (
        {
            "enabled": True,
            "storage_root": "relative",
            "max_storage_bytes": 2 * 1024**3,
            "max_download_bps": 1,
            "legal_use_confirmed": True,
        },
        {
            "enabled": True,
            "storage_root": "C:/downloads",
            "max_storage_bytes": 2 * 1024**3,
            "max_download_bps": 1,
            "legal_use_confirmed": False,
        },
        {"enabled": True, "search_enabled": True},
        {"enabled": True, "auto_port_forward": True},
        {"enabled": False, "seeding_enabled": True},
    ),
)
def test_p2p_rejects_unbounded_or_implicit_network_behavior(value) -> None:
    with pytest.raises(TransportBoundaryError):
        validate_p2p_transfer_policy(value)


def test_p2p_seeding_requires_explicit_upload_limit(tmp_path: Path) -> None:
    base = {
        "enabled": True,
        "storage_root": str(tmp_path),
        "max_storage_bytes": 1024**3,
        "max_download_bps": 1024,
        "legal_use_confirmed": True,
        "upload_enabled": True,
        "seeding_enabled": True,
    }
    with pytest.raises(TransportBoundaryError, match="upload limit"):
        validate_p2p_transfer_policy(base)

    policy = validate_p2p_transfer_policy({**base, "max_upload_bps": 1024})
    assert policy.seeding_enabled
