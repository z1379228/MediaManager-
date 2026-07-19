"""Security policy for publisher trust changes."""

from __future__ import annotations

import base64
import hashlib
import sqlite3
from dataclasses import dataclass

from core.plugins.lifecycle import PluginLifecycleLockError
from core.plugins.manager import PluginManager
from core.plugins.registry import PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.trust_store import TrustStore, TrustedPublisher


@dataclass(frozen=True, slots=True)
class PublisherOperationResult:
    successful: bool
    publisher: TrustedPublisher | None = None
    errors: tuple[str, ...] = ()


class PublisherManager:
    def __init__(
        self,
        trust_store: TrustStore,
        registry: PluginRegistry,
        plugin_manager: PluginManager,
    ) -> None:
        self.trust_store = trust_store
        self.registry = registry
        self.plugin_manager = plugin_manager
        self.lifecycle_lock = plugin_manager.lifecycle_lock

    def add(
        self,
        publisher_id: str,
        public_key: str,
        security_mode: SecurityMode,
    ) -> PublisherOperationResult:
        if security_mode is SecurityMode.BLOCKED:
            return PublisherOperationResult(
                False,
                errors=("cannot add trust while security mode is BLOCKED",),
            )
        try:
            with self.lifecycle_lock.hold():
                return self._add_locked(publisher_id, public_key)
        except PluginLifecycleLockError:
            return PublisherOperationResult(
                False,
                errors=("plugin lifecycle is busy",),
            )

    def _add_locked(
        self,
        publisher_id: str,
        public_key: str,
    ) -> PublisherOperationResult:
        try:
            publisher = self.trust_store.add(publisher_id, public_key)
            return PublisherOperationResult(True, publisher)
        except (OSError, ValueError) as error:
            return PublisherOperationResult(False, errors=(str(error),))

    def set_enabled(
        self,
        publisher_id: str,
        enabled: bool,
        security_mode: SecurityMode,
    ) -> PublisherOperationResult:
        try:
            with self.lifecycle_lock.hold():
                return self._set_enabled_locked(
                    publisher_id,
                    enabled,
                    security_mode,
                )
        except PluginLifecycleLockError:
            return PublisherOperationResult(
                False,
                errors=("plugin lifecycle is busy",),
            )

    def _set_enabled_locked(
        self,
        publisher_id: str,
        enabled: bool,
        security_mode: SecurityMode,
    ) -> PublisherOperationResult:
        try:
            self.trust_store.load()
        except (OSError, TypeError, ValueError) as error:
            return PublisherOperationResult(False, errors=(str(error),))
        publishers = {item.publisher_id: item for item in self.trust_store.list_all()}
        publisher = publishers.get(publisher_id)
        if publisher is None:
            return PublisherOperationResult(False, errors=("publisher does not exist",))
        if enabled and security_mode is SecurityMode.BLOCKED:
            return PublisherOperationResult(
                False,
                publisher,
                ("cannot enable trust while security mode is BLOCKED",),
            )
        try:
            self.trust_store.set_enabled(publisher_id, enabled)
            updated = self.trust_store.find(publisher_id) or publisher
            errors: list[str] = []
            if not enabled:
                try:
                    records = self.registry.list_all()
                except (sqlite3.Error, TypeError, ValueError):
                    errors = [
                        "publisher trust was updated, but plugin registry "
                        "reconciliation failed"
                    ]
                    try:
                        self.plugin_manager._stop_all_runtimes_for_trust_change()
                    except (OSError, RuntimeError, TimeoutError, ValueError):
                        errors.append(
                            "emergency plugin shutdown could not be confirmed"
                        )
                    return PublisherOperationResult(
                        False,
                        updated,
                        tuple(errors),
                    )
                affected = tuple(
                    record
                    for record in records
                    if record.publisher_id == publisher_id and record.enabled
                )
                if affected:
                    errors.extend(
                        self.plugin_manager._contain_runtimes_for_trust_revocation(
                            affected
                        )
                    )
            return PublisherOperationResult(not errors, updated, tuple(errors))
        except (OSError, KeyError, ValueError) as error:
            return PublisherOperationResult(False, publisher, (str(error),))


def public_key_fingerprint(public_key: str) -> str:
    raw = base64.b64decode(
        public_key.removeprefix("ed25519:").strip(),
        validate=True,
    )
    digest = hashlib.sha256(raw).hexdigest().upper()
    return ":".join(digest[index : index + 4] for index in range(0, 32, 4))
