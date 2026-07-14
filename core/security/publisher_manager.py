"""Security policy for publisher trust changes."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass

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
            errors: list[str] = []
            if not enabled:
                for record in self.registry.list_all():
                    if record.publisher_id != publisher_id or not record.enabled:
                        continue
                    result = self.plugin_manager.set_enabled(
                        record.plugin_id,
                        False,
                        security_mode,
                    )
                    errors.extend(result.errors)
            updated = next(
                item
                for item in self.trust_store.list_all()
                if item.publisher_id == publisher_id
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