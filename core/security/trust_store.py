"""Pinned publisher trust store with atomic updates."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from core.settings import SettingsWriteBlockedError, settings_file_lock

_PUBLISHER_ID = re.compile(r"^[a-z][a-z0-9.-]{1,127}$")


@dataclass(frozen=True, slots=True)
class TrustedPublisher:
    publisher_id: str
    public_key: str
    enabled: bool = True


class TrustStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._publishers: dict[str, TrustedPublisher] = {}

    def load(self) -> None:
        if not self.path.exists():
            self._publishers = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("trust store document is invalid")
            publishers = raw.get("publishers", [])
            if not isinstance(publishers, list):
                raise ValueError("publishers must be a list")
            loaded: list[TrustedPublisher] = []
            required_fields = {"publisher_id", "public_key", "enabled"}
            for item in publishers:
                if not isinstance(item, dict) or set(item) != required_fields:
                    raise ValueError("trust store document is invalid")
                publisher_id = item["publisher_id"]
                public_key = item["public_key"]
                enabled = item["enabled"]
                if (
                    not isinstance(publisher_id, str)
                    or not isinstance(public_key, str)
                    or type(enabled) is not bool
                ):
                    raise ValueError("trust store document is invalid")
                loaded.append(TrustedPublisher(publisher_id, public_key, enabled))
            if len({item.publisher_id for item in loaded}) != len(loaded):
                raise ValueError("duplicate publisher id")
            for publisher in loaded:
                self._validate(publisher.publisher_id, publisher.public_key)
        except (OSError, TypeError, ValueError):
            self._publishers = {}
            raise
        self._publishers = {item.publisher_id: item for item in loaded}

    def find(self, publisher_id: str) -> TrustedPublisher | None:
        return self._publishers.get(publisher_id)

    def get(self, publisher_id: str) -> TrustedPublisher | None:
        publisher = self._publishers.get(publisher_id)
        return publisher if publisher and publisher.enabled else None

    def list_all(self) -> tuple[TrustedPublisher, ...]:
        return tuple(self._publishers[key] for key in sorted(self._publishers))

    def add(self, publisher_id: str, public_key: str) -> TrustedPublisher:
        self._validate(publisher_id, public_key)
        try:
            with settings_file_lock(self.path):
                self.load()
                if publisher_id in self._publishers:
                    raise ValueError("publisher already exists")
                key_bytes = self._decode_key(public_key)
                if any(
                    self._decode_key(item.public_key) == key_bytes
                    for item in self._publishers.values()
                ):
                    raise ValueError(
                        "public key is already assigned to another publisher"
                    )
                publisher = TrustedPublisher(publisher_id, public_key, True)
                updated = dict(self._publishers)
                updated[publisher_id] = publisher
                self._save(updated)
                self._publishers = updated
                return publisher
        except SettingsWriteBlockedError as error:
            raise OSError("publisher trust store is busy") from error

    def set_enabled(self, publisher_id: str, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("publisher enabled state must be a boolean")
        try:
            with settings_file_lock(self.path):
                self.load()
                current = self._publishers.get(publisher_id)
                if current is None:
                    raise KeyError(publisher_id)
                updated = dict(self._publishers)
                updated[publisher_id] = TrustedPublisher(
                    current.publisher_id,
                    current.public_key,
                    enabled,
                )
                self._save(updated)
                self._publishers = updated
        except SettingsWriteBlockedError as error:
            raise OSError("publisher trust store is busy") from error

    def _save(self, publishers: dict[str, TrustedPublisher]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {
            "publishers": [
                asdict(publishers[key]) for key in sorted(publishers)
            ]
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @classmethod
    def _validate(cls, publisher_id: str, public_key: str) -> None:
        if not isinstance(publisher_id, str) or not isinstance(public_key, str):
            raise ValueError("publisher id and public key must be strings")
        if not _PUBLISHER_ID.fullmatch(publisher_id):
            raise ValueError("invalid publisher id")
        cls._decode_key(public_key)

    @staticmethod
    def _decode_key(public_key: str) -> bytes:
        try:
            raw = base64.b64decode(
                public_key.removeprefix("ed25519:").strip(),
                validate=True,
            )
        except (ValueError, binascii.Error) as error:
            raise ValueError("invalid Ed25519 public key encoding") from error
        if len(raw) != 32:
            raise ValueError("Ed25519 public key must be 32 bytes")
        return raw
