from __future__ import annotations

import base64
import json

import pytest

from core.security.trust_store import TrustStore


def public_key(byte: bytes = b"p") -> str:
    return "ed25519:" + base64.b64encode(byte * 32).decode("ascii")


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


@pytest.mark.parametrize(
    "document",
    [
        None,
        [],
        {
            "publishers": [
                {
                    "publisher_id": "publisher.example",
                    "public_key": None,
                    "enabled": True,
                }
            ]
        },
        {
            "publishers": [
                {
                    "publisher_id": "publisher.example",
                    "public_key": public_key(),
                    "enabled": "false",
                }
            ]
        },
    ],
)
def test_trust_store_rejects_malformed_document_types(
    tmp_path,
    document: object,
) -> None:
    path = tmp_path / "trust-store.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="trust store document is invalid"):
        TrustStore(path).load()


def test_trust_store_load_failure_clears_previous_trust(tmp_path) -> None:
    path = tmp_path / "trust-store.json"
    store = TrustStore(path)
    publisher = store.add("publisher.example", public_key())
    assert store.get(publisher.publisher_id) == publisher
    path.write_text("null", encoding="utf-8")

    with pytest.raises(ValueError, match="trust store document is invalid"):
        store.load()

    assert store.get(publisher.publisher_id) is None
    assert store.list_all() == ()

def test_trust_store_rejects_public_key_alias(tmp_path) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    key = base64.b64encode(b"p" * 32).decode("ascii")
    store.add("first.example", key)
    with pytest.raises(ValueError, match="already assigned"):
        store.add("second.example", "ed25519:" + key)


def test_trust_store_write_failure_does_not_change_memory(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    key = "ed25519:" + base64.b64encode(b"p" * 32).decode("ascii")

    def fail_save(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(store, "_save", fail_save)

    with pytest.raises(OSError, match="simulated write failure"):
        store.add("publisher.example", key)

    assert store.find("publisher.example") is None


def test_trust_store_enable_failure_keeps_publisher_disabled(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TrustStore(tmp_path / "trust-store.json")
    key = "ed25519:" + base64.b64encode(b"p" * 32).decode("ascii")
    store.add("publisher.example", key)
    store.set_enabled("publisher.example", False)

    def fail_save(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(store, "_save", fail_save)

    with pytest.raises(OSError, match="simulated write failure"):
        store.set_enabled("publisher.example", True)

    assert store.get("publisher.example") is None
