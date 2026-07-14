"""Pinned publisher trust store with atomic updates."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

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
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        publishers = raw.get("publishers", [])
        if not isinstance(publishers, list):
            raise ValueError("publishers must be a list")
        loaded = [TrustedPublisher(**item) for item in publishers]
        if len({item.publisher_id for item in loaded}) != len(loaded):
            raise ValueError("duplicate publisher id")
        for publisher in loaded:
            self._validate(publisher.publisher_id, publisher.public_key)
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
        if publisher_id in self._publishers:
            raise ValueError("publisher already exists")
        key_bytes = self._decode_key(public_key)
        if any(
            self._decode_key(item.public_key) == key_bytes
            for item in self._publishers.values()
        ):
            raise ValueError("public key is already assigned to another publisher")
        publisher = TrustedPublisher(publisher_id, public_key, True)
        self._publishers[publisher_id] = publisher
        self._save()
        return publisher

    def set_enabled(self, publisher_id: str, enabled: bool) -> None:
        current = self._publishers.get(publisher_id)
        if current is None:
            raise KeyError(publisher_id)
        self._publishers[publisher_id] = TrustedPublisher(
            current.publisher_id,
            current.public_key,
            enabled,
        )
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {"publishers": [asdict(item) for item in self.list_all()]}
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @classmethod
    def _validate(cls, publisher_id: str, public_key: str) -> None:
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
