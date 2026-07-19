from __future__ import annotations

import base64
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.manager import PluginManager, PluginOperationResult
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.publisher_manager import PublisherManager, public_key_fingerprint
from core.security.safe_mode import SecurityMode
from core.security.trust_store import TrustStore


def public_key(byte: bytes = b"p") -> str:
    return "ed25519:" + base64.b64encode(byte * 32).decode("ascii")


def test_blocked_mode_cannot_add_publisher(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    plugin_manager = Mock()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    manager = PublisherManager(store, Mock(), plugin_manager)
    result = manager.add("publisher.example", public_key(), SecurityMode.BLOCKED)
    assert not result.successful
    assert store.list_all() == ()


def test_safe_mode_can_prepare_trust_without_running_plugins(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    plugin_manager = Mock()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
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
    plugin_manager._contain_runtimes_for_trust_revocation.return_value = ()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    manager = PublisherManager(store, registry, plugin_manager)
    result = manager.set_enabled(
        "publisher.example", False, SecurityMode.SAFE_MODE
    )
    assert result.successful
    assert store.get("publisher.example") is None
    plugin_manager._contain_runtimes_for_trust_revocation.assert_called_once_with(
        (registry.list_all.return_value[0],)
    )


def test_disabling_publisher_contains_cross_publisher_dependents(
    tmp_path,
) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("publisher.example", public_key())
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    revoked = PluginRecord(
        "dependency.plugin",
        "1.0.0",
        True,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "publisher.example",
        (),
        "a" * 64,
    )
    dependent = PluginRecord(
        "dependent.plugin",
        "1.0.0",
        True,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "other.example",
        (),
        "b" * 64,
    )
    registry.upsert(revoked)
    registry.upsert(dependent)
    supervisor = Mock()
    plugin_manager = PluginManager(
        mod_root,
        registry,
        supervisor,
        store,
        lifecycle_lock=PluginLifecycleLock(mod_root),
    )
    manager = PublisherManager(store, registry, plugin_manager)

    result = manager.set_enabled(
        "publisher.example",
        False,
        SecurityMode.SAFE_MODE,
    )

    assert result.successful
    assert store.get("publisher.example") is None
    supervisor.stop_all.assert_called_once_with()
    supervisor.stop.assert_called_once_with("dependency.plugin")
    assert not registry.get("dependency.plugin").enabled
    assert registry.get("dependent.plugin").enabled
    registry.close()


def test_publisher_disable_maps_registry_reconciliation_failure(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("publisher.example", public_key())
    registry = Mock()
    registry.list_all.side_effect = sqlite3.OperationalError(
        "simulated registry failure"
    )
    plugin_manager = Mock()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    manager = PublisherManager(store, registry, plugin_manager)

    result = manager.set_enabled(
        "publisher.example",
        False,
        SecurityMode.SAFE_MODE,
    )

    assert not result.successful
    assert result.publisher is not None and not result.publisher.enabled
    assert result.errors == (
        "publisher trust was updated, but plugin registry reconciliation failed",
    )
    assert store.find("publisher.example") == result.publisher
    plugin_manager.set_enabled.assert_not_called()
    plugin_manager._stop_all_runtimes_for_trust_change.assert_called_once_with()


def test_publisher_disable_reports_unconfirmed_emergency_shutdown(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("publisher.example", public_key())
    registry = Mock()
    registry.list_all.side_effect = sqlite3.OperationalError(
        "simulated registry failure"
    )
    plugin_manager = Mock()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    plugin_manager._stop_all_runtimes_for_trust_change.side_effect = OSError(
        "simulated shutdown failure"
    )
    manager = PublisherManager(store, registry, plugin_manager)

    result = manager.set_enabled(
        "publisher.example",
        False,
        SecurityMode.NORMAL,
    )

    assert not result.successful
    assert result.publisher is not None and not result.publisher.enabled
    assert result.errors == (
        "publisher trust was updated, but plugin registry reconciliation failed",
        "emergency plugin shutdown could not be confirmed",
    )


def test_public_key_fingerprint_is_stable() -> None:
    assert public_key_fingerprint(public_key()) == public_key_fingerprint(
        public_key().removeprefix("ed25519:")
    )


def test_publisher_disable_holds_plugin_lifecycle_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("publisher.example", public_key())
    plugin_manager = Mock()
    plugin_manager.lifecycle_lock = PluginLifecycleLock(tmp_path / "mod")
    registry = Mock()
    registry.list_all.return_value = ()
    manager = PublisherManager(store, registry, plugin_manager)
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_set_enabled = store.set_enabled
    checked = False

    def guarded_set_enabled(publisher_id: str, enabled: bool) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_set_enabled(publisher_id, enabled)

    monkeypatch.setattr(store, "set_enabled", guarded_set_enabled)

    result = manager.set_enabled(
        "publisher.example",
        False,
        SecurityMode.SAFE_MODE,
    )

    assert result.successful
    assert checked
    assert manager.lifecycle_lock is plugin_manager.lifecycle_lock


def test_stale_process_cannot_reenable_revoked_publisher_or_overwrite_it(
    tmp_path,
) -> None:
    trust_path = tmp_path / "trust-store.json"
    primary_store = TrustStore(trust_path)
    primary_store.add("publisher.example", public_key())
    stale_store = TrustStore(trust_path)
    stale_store.load()
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    registry.upsert(
        PluginRecord(
            "example.plugin",
            "1.0.0",
            False,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "publisher.example",
            (),
            "a" * 64,
        )
    )
    primary_plugin_manager = Mock()
    primary_plugin_manager.lifecycle_lock = PluginLifecycleLock(mod_root)
    primary_plugin_manager.set_enabled.return_value = PluginOperationResult(True)
    primary_registry = Mock()
    primary_registry.list_all.return_value = ()
    primary_manager = PublisherManager(
        primary_store,
        primary_registry,
        primary_plugin_manager,
    )
    assert primary_manager.set_enabled(
        "publisher.example",
        False,
        SecurityMode.SAFE_MODE,
    ).successful

    stale_plugin_manager = PluginManager(
        mod_root,
        registry,
        Mock(),
        stale_store,
        lifecycle_lock=PluginLifecycleLock(mod_root),
    )
    rejected = stale_plugin_manager.set_enabled(
        "example.plugin",
        True,
        SecurityMode.NORMAL,
    )
    assert not rejected.successful
    assert rejected.errors == ("publisher is no longer trusted",)

    stale_publisher_manager = PublisherManager(
        stale_store,
        registry,
        stale_plugin_manager,
    )
    assert stale_publisher_manager.add(
        "other.example",
        public_key(b"q"),
        SecurityMode.SAFE_MODE,
    ).successful
    reloaded = TrustStore(trust_path)
    reloaded.load()
    revoked = reloaded.find("publisher.example")
    assert revoked is not None and not revoked.enabled
    assert reloaded.get("other.example") is not None
    registry.close()
