from __future__ import annotations

import base64

import pytest

from core.security.trust_store import TrustStore


def test_trust_store_add_disable_and_reload(tmp_path) -> None:
    path = tmp_path / "trust-store.json"
    store = TrustStore(path)
    publisher = store.add(
        "publisher.example",
        "ed25519:" + base64.b64encode(b"p" * 32).decode("ascii"),
    )
    assert store.get(publisher.publisher_id) == publisher
    store.set_enabled(publisher.publisher_id, False)
    assert store.get(publisher.publisher_id) is None
    reloaded = TrustStore(path)
    reloaded.load()
    assert len(reloaded.list_all()) == 1
    assert not reloaded.list_all()[0].enabled


def test_trust_store_rejects_invalid_key(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    with pytest.raises(ValueError, match="public key"):
        store.add("publisher.example", "not-a-key")
    assert not (tmp_path / "trust-store.json").exists()

def test_trust_store_rejects_public_key_alias(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    key = base64.b64encode(b"p" * 32).decode("ascii")
    store.add("first.example", key)
    with pytest.raises(ValueError, match="already assigned"):
        store.add("second.example", "ed25519:" + key)
