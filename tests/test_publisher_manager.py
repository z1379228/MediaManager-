from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import Mock

from core.plugins.manager import PluginOperationResult
from core.security.publisher_manager import PublisherManager, public_key_fingerprint
from core.security.safe_mode import SecurityMode
from core.security.trust_store import TrustStore


def public_key(byte: bytes = b"p") -> str:
    return "ed25519:" + base64.b64encode(byte * 32).decode("ascii")


def test_blocked_mode_cannot_add_publisher(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    manager = PublisherManager(store, Mock(), Mock())
    result = manager.add("publisher.example", public_key(), SecurityMode.BLOCKED)
    assert not result.successful
    assert store.list_all() == ()


def test_safe_mode_can_prepare_trust_without_running_plugins(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    plugin_manager = Mock()
    manager = PublisherManager(store, Mock(), plugin_manager)
    result = manager.add("publisher.example", public_key(), SecurityMode.SAFE_MODE)
    assert result.successful
    assert result.publisher == store.get("publisher.example")
    plugin_manager.assert_not_called()


def test_disabling_publisher_stops_its_enabled_plugins(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("publisher.example", public_key())
    registry = Mock()
    registry.list_all.return_value = (
        SimpleNamespace(
            plugin_id="example.plugin",
            publisher_id="publisher.example",
            enabled=True,
        ),
        SimpleNamespace(
            plugin_id="other.plugin",
            publisher_id="other.example",
            enabled=True,
        ),
    )
    plugin_manager = Mock()
    plugin_manager.set_enabled.return_value = PluginOperationResult(True)
    manager = PublisherManager(store, registry, plugin_manager)
    result = manager.set_enabled(
        "publisher.example", False, SecurityMode.SAFE_MODE
    )
    assert result.successful
    assert store.get("publisher.example") is None
    plugin_manager.set_enabled.assert_called_once_with(
        "example.plugin", False, SecurityMode.SAFE_MODE
    )


def test_public_key_fingerprint_is_stable() -> None:
    assert public_key_fingerprint(public_key()) == public_key_fingerprint(
        public_key().removeprefix("ed25519:")
    )
