from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry


def _record() -> PluginRecord:
    return PluginRecord(
        "example.plugin",
        "1.0.0",
        False,
        PendingAction.NONE,
        "TRUSTED_PUBLISHER",
        "trusted.example",
        (),
        "a" * 64,
    )


def test_set_enabled_does_not_clear_an_unowned_pending_journal(
    tmp_path: Path,
) -> None:
    registry = PluginRegistry(tmp_path / "registry.sqlite3")
    registry.upsert(replace(_record(), pending_action=PendingAction.UPDATE))

    registry.set_enabled("example.plugin", True)

    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled
    assert current.pending_action is PendingAction.UPDATE
    registry.close()


def test_lifecycle_claim_is_atomic_across_stale_registry_connections(
    tmp_path: Path,
) -> None:
    path = tmp_path / "registry.sqlite3"
    first = PluginRegistry(path)
    second = PluginRegistry(path)
    first.upsert(_record())
    stale = second.get("example.plugin")
    assert stale is not None

    assert first.claim_lifecycle(stale, PendingAction.ENABLE)
    assert not second.claim_lifecycle(stale, PendingAction.DISABLE)

    visible = second.get("example.plugin")
    assert visible is not None
    assert visible.pending_action is PendingAction.ENABLE
    first.close()
    second.close()


def test_lifecycle_claim_rejects_stale_version_and_manifest_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "registry.sqlite3"
    first = PluginRegistry(path)
    second = PluginRegistry(path)
    first.upsert(_record())
    stale = second.get("example.plugin")
    assert stale is not None
    first.upsert(
        replace(
            stale,
            installed_version="1.1.0",
            manifest_hash="b" * 64,
        )
    )

    assert not second.claim_lifecycle(stale, PendingAction.ENABLE)

    current = first.get("example.plugin")
    assert current is not None
    assert current.installed_version == "1.1.0"
    assert current.pending_action is PendingAction.NONE
    first.close()
    second.close()


def test_lifecycle_finalize_only_clears_the_owned_action(tmp_path: Path) -> None:
    registry = PluginRegistry(tmp_path / "registry.sqlite3")
    record = _record()
    registry.upsert(record)
    assert registry.claim_lifecycle(record, PendingAction.ENABLE)

    assert not registry.finish_lifecycle(
        record,
        PendingAction.DISABLE,
        enabled=True,
    )
    claimed = registry.get("example.plugin")
    assert claimed is not None
    assert claimed.pending_action is PendingAction.ENABLE
    assert not claimed.enabled

    assert registry.finish_lifecycle(
        record,
        PendingAction.ENABLE,
        enabled=True,
    )
    finalized = registry.get("example.plugin")
    assert finalized is not None
    assert finalized.enabled
    assert finalized.pending_action is PendingAction.NONE
    registry.close()


def test_lifecycle_cas_rejects_non_toggle_actions(tmp_path: Path) -> None:
    registry = PluginRegistry(tmp_path / "registry.sqlite3")
    record = _record()
    registry.upsert(record)

    with pytest.raises(ValueError, match="ENABLE or DISABLE"):
        registry.claim_lifecycle(record, PendingAction.UPDATE)
    with pytest.raises(ValueError, match="ENABLE or DISABLE"):
        registry.finish_lifecycle(
            record,
            PendingAction.ROLLBACK,
            enabled=False,
        )

    assert registry.get("example.plugin") == record
    registry.close()


@pytest.mark.parametrize(
    ("method_name", "arguments"),
    (
        ("set_enabled", ("missing.plugin", True)),
        ("set_pending", ("missing.plugin", PendingAction.UPDATE)),
        ("delete", ("missing.plugin",)),
    ),
)
def test_missing_required_write_rolls_back_sqlite_transaction(
    tmp_path: Path,
    method_name: str,
    arguments: tuple[object, ...],
) -> None:
    path = tmp_path / "registry.sqlite3"
    first = PluginRegistry(path)
    second = PluginRegistry(path)
    first.upsert(_record())

    with pytest.raises(KeyError, match="missing.plugin"):
        getattr(first, method_name)(*arguments)

    assert not first._connection.in_transaction
    second.set_pending("example.plugin", PendingAction.UPDATE)
    current = first.get("example.plugin")
    assert current is not None
    assert current.pending_action is PendingAction.UPDATE
    first.close()
    second.close()
