from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sqlite3
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import core.plugins.lifecycle as lifecycle_module
import core.plugins.recovery as recovery_module
from core.plugins.installer import PluginInstaller
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.manager import PluginManager
from core.plugins.package_verifier import signed_payload
from core.plugins.recovery import PluginTransactionRecovery
from core.plugins.registry import PendingAction, PluginRegistry
from core.plugins.updater import PluginUpdater
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureResult
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION


class AcceptingSignatureVerifier:
    def verify(
        self, payload: bytes, signature: bytes, public_key: str
    ) -> SignatureResult:
        assert payload and signature and public_key
        return SignatureResult(True, "accepted for test")


def build_package(
    path: Path,
    version: str,
    *,
    plugin_id: str = "example.plugin",
    dependencies: tuple[str, ...] = (),
) -> None:
    source = f"VERSION = '{version}'\n".encode()
    manifest = {
        "schema_version": 1,
        "id": plugin_id,
        "name": "Example",
        "version": version,
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": list(dependencies),
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    manifest_bytes = json.dumps(manifest).encode()
    files_bytes = json.dumps(
        {"files": {"plugin.py": hashlib.sha256(source).hexdigest()}}
    ).encode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.json", manifest_bytes)
        archive.writestr("files.json", files_bytes)
        archive.writestr("plugin.sig", signed_payload(manifest_bytes, files_bytes)[:64])
        archive.writestr("plugin.py", source)


def setup_recovery(tmp_path: Path):
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("trusted.example", base64.b64encode(b"k" * 32).decode("ascii"))
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    verifier = AcceptingSignatureVerifier()
    installer = PluginInstaller(
        tmp_path / "mod", registry, store, signature_verifier=verifier
    )
    manager = PluginManager(
        tmp_path / "mod",
        registry,
        Mock(),
        store,
        signature_verifier=verifier,
    )
    initial = tmp_path / "initial.modpkg"
    build_package(initial, "1.0.0")
    assert installer.install(initial, security_mode=SecurityMode.SAFE_MODE).installed
    old_record = registry.get("example.plugin")
    recovery = PluginTransactionRecovery(tmp_path / "mod", registry, manager)
    return recovery, registry, manager, installer, old_record


def interrupted_replacement(tmp_path: Path, action: PendingAction):
    recovery, registry, manager, installer, old_record = setup_recovery(tmp_path)
    update = tmp_path / "update.modpkg"
    build_package(update, "1.1.0")
    updater = PluginUpdater(tmp_path / "mod", registry, installer, manager)
    assert updater.update(
        update,
        "example.plugin",
        approved_permissions=(),
        security_mode=SecurityMode.SAFE_MODE,
    ).updated
    registry.upsert(replace(old_record, enabled=False, pending_action=action))
    return recovery, registry


@pytest.mark.parametrize("action", [PendingAction.UPDATE, PendingAction.ROLLBACK])
def test_recovery_restores_registered_version_and_preserves_interrupted_one(
    tmp_path: Path, action: PendingAction
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, action)
    report = recovery.recover_all()
    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    interrupted = tmp_path / "mod" / "backups" / "example.plugin" / "1.1.0"
    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert installed.read_text() == "VERSION = '1.0.0'\n"
    assert (interrupted / "plugin.py").is_file()
    record = registry.get("example.plugin")
    assert record.installed_version == "1.0.0"
    assert record.pending_action is PendingAction.NONE
    registry.close()


def test_recovery_clears_journal_when_old_version_never_moved(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.UPDATE)
    )
    report = recovery.recover_all()
    assert report.recovered == ("example.plugin",)
    assert registry.get("example.plugin").pending_action is PendingAction.NONE
    registry.close()


def test_recovery_refuses_tampered_registered_backup(tmp_path: Path) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    (backup / "plugin.py").write_text("tampered", encoding="utf-8")
    report = recovery.recover_all()
    assert report.recovered == ()
    assert any("hash mismatch" in error for error in report.errors)
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE
    registry.close()


def test_recovery_reverts_swap_when_post_move_verification_fails(
    tmp_path: Path,
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    recovery.plugin_manager.verify_directory = Mock(
        side_effect=[
            (),
            (),
            ("installed plugin manifest was modified",),
        ]
    )

    report = recovery.recover_all()

    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    record = registry.get("example.plugin")
    assert report.recovered == ()
    assert report.errors == (
        "example.plugin: installed plugin manifest was modified",
    )
    assert installed.read_text(encoding="utf-8") == "VERSION = '1.1.0'\n"
    assert (backup / "plugin.py").is_file()
    assert record.installed_version == "1.0.0"
    assert record.pending_action is PendingAction.UPDATE
    assert recovery.plugin_manager.verify_directory.call_count == 3
    assert all(
        call.kwargs["refresh_trust_store"]
        for call in recovery.plugin_manager.verify_directory.call_args_list
    )
    registry.close()


def test_recovery_retries_after_registry_finalize_failure(tmp_path: Path) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    upsert = registry.upsert
    failed = False

    def fail_once(record) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise sqlite3.OperationalError("simulated registry failure")
        upsert(record)

    registry.upsert = Mock(side_effect=fail_once)

    first = recovery.recover_all()

    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "1.0.0"
    assert first.recovered == ()
    assert any("simulated registry failure" in error for error in first.errors)
    assert installed.read_text(encoding="utf-8") == "VERSION = '1.1.0'\n"
    assert (backup / "plugin.py").is_file()
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE

    second = recovery.recover_all()

    assert second.recovered == ("example.plugin",)
    assert second.errors == ()
    assert installed.read_text(encoding="utf-8") == "VERSION = '1.0.0'\n"
    assert registry.get("example.plugin").pending_action is PendingAction.NONE
    registry.close()


def test_recovery_converges_after_swap_back_move_fails_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    recovery.plugin_manager.verify_directory = Mock(
        side_effect=[(), (), ("installed plugin manifest was modified",), (), (), ()]
    )
    original_replace = recovery_module.os.replace
    replace_count = 0

    def fail_first_swap_back(source, destination) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 3:
            raise OSError("simulated swap-back failure")
        original_replace(source, destination)

    monkeypatch.setattr(recovery_module.os, "replace", fail_first_swap_back)

    first = recovery.recover_all()

    assert first.recovered == ()
    assert any("swap-back failure" in error for error in first.errors)
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE

    second = recovery.recover_all()

    installed = tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    interrupted = tmp_path / "mod" / "backups" / "example.plugin" / "1.1.0"
    assert second.recovered == ("example.plugin",)
    assert second.errors == ()
    assert installed.read_text(encoding="utf-8") == "VERSION = '1.0.0'\n"
    assert (interrupted / "plugin.py").is_file()
    assert registry.get("example.plugin").pending_action is PendingAction.NONE
    registry.close()


def test_recovery_rejects_reparse_backup_root_before_file_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    original = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path.name == "backups" or original(path),
    )
    replace_spy = Mock(wraps=recovery_module.os.replace)
    monkeypatch.setattr(recovery_module.os, "replace", replace_spy)

    report = recovery.recover_all()

    assert report.recovered == ()
    assert report.errors == (
        "example.plugin: transaction paths escape the MOD root",
    )
    replace_spy.assert_not_called()
    assert registry.get("example.plugin").pending_action is PendingAction.UPDATE
    registry.close()


def test_recovery_reports_missing_registered_version(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    shutil.rmtree(installed)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.ROLLBACK)
    )
    report = recovery.recover_all()
    assert report.recovered == ()
    assert report.errors == (
        "example.plugin: registered version is absent from installed and backups",
    )
    registry.close()


def test_recovery_can_verify_with_disabled_publisher(tmp_path: Path) -> None:
    recovery, registry, manager, _, old_record = setup_recovery(tmp_path)
    manager.trust_store.set_enabled("trusted.example", False)
    registry.upsert(
        replace(old_record, enabled=False, pending_action=PendingAction.UPDATE)
    )
    report = recovery.recover_all()
    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    registry.close()


def test_recovery_rejects_registry_path_escape(tmp_path: Path) -> None:
    recovery, registry, _, _, old_record = setup_recovery(tmp_path)
    registry.upsert(
        replace(
            old_record,
            plugin_id="../../escape",
            enabled=False,
            pending_action=PendingAction.UPDATE,
        )
    )
    report = recovery.recover_all()
    assert report.recovered == ()
    assert report.errors == ("../../escape: transaction paths escape the MOD root",)
    registry.close()


def test_recovery_restores_interrupted_purge(tmp_path: Path) -> None:
    recovery, registry, _, _, record = setup_recovery(tmp_path)
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    removed = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / record.installed_version
    )
    removed.parent.mkdir(parents=True)
    installed.replace(removed)
    backup = tmp_path / "mod" / "backups" / "example.plugin" / "0.9.0"
    backup.mkdir(parents=True)
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    removed.replace(staging / "removed")
    (backup.parent).replace(staging / "backups")
    registry.set_pending("example.plugin", PendingAction.PURGE)

    report = recovery.recover_all()

    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert removed.is_dir() and backup.is_dir()
    assert not staging.exists()
    assert registry.get("example.plugin").pending_action is PendingAction.REMOVE
    registry.close()


def test_recovery_finishes_orphaned_committed_purge(tmp_path: Path) -> None:
    recovery, registry, _, _, _ = setup_recovery(tmp_path)
    registry.delete("example.plugin")
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    (staging / "removed").mkdir()

    report = recovery.recover_all()

    assert report.errors == () and report.warnings == ()
    assert not staging.exists()
    registry.close()


def test_recovery_rejects_reparse_purge_staging_before_move_or_erase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry, _, _, record = setup_recovery(tmp_path)
    installed = tmp_path / "mod" / "installed" / "example.plugin"
    removed = (
        tmp_path
        / "mod"
        / "quarantine"
        / "removed"
        / "example.plugin"
        / record.installed_version
    )
    removed.parent.mkdir(parents=True)
    installed.replace(removed)
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    removed.replace(staging / "removed")
    registry.set_pending("example.plugin", PendingAction.PURGE)
    original_reparse_check = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path == staging or original_reparse_check(path),
    )
    replace_spy = Mock(wraps=recovery_module.os.replace)
    erase_spy = Mock(wraps=recovery_module.shutil.rmtree)
    monkeypatch.setattr(recovery_module.os, "replace", replace_spy)
    monkeypatch.setattr(recovery_module.shutil, "rmtree", erase_spy)

    report = recovery.recover_all()

    assert report.recovered == ()
    assert any("purge recovery path is unsafe" in error for error in report.errors)
    assert any("unsafe purge path" in warning for warning in report.warnings)
    replace_spy.assert_not_called()
    erase_spy.assert_not_called()
    assert (staging / "removed").is_dir()
    assert registry.get("example.plugin").pending_action is PendingAction.PURGE
    registry.close()


def test_recovery_rejects_reparse_orphan_purge_root_before_erase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry, _, _, _ = setup_recovery(tmp_path)
    registry.delete("example.plugin")
    staging = recovery.cleanup.purge_staging_path("example.plugin")
    staging.mkdir(parents=True)
    (staging / "removed").mkdir()
    purge_root = tmp_path / "mod" / "quarantine" / "purge"
    original_reparse_check = lifecycle_module._is_reparse_point
    monkeypatch.setattr(
        lifecycle_module,
        "_is_reparse_point",
        lambda path: path == purge_root or original_reparse_check(path),
    )
    erase_spy = Mock(wraps=recovery_module.shutil.rmtree)
    monkeypatch.setattr(recovery_module.shutil, "rmtree", erase_spy)

    report = recovery.recover_all()

    assert report.recovered == ()
    assert any("unsafe purge root" in warning for warning in report.warnings)
    erase_spy.assert_not_called()
    assert (staging / "removed").is_dir()
    registry.close()


def test_recovery_holds_lifecycle_lock_through_file_moves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry = interrupted_replacement(tmp_path, PendingAction.UPDATE)
    competitor = PluginLifecycleLock(tmp_path / "mod", timeout_seconds=0)
    original_replace = recovery_module.os.replace
    checked = False

    def guarded_replace(source: Path, destination: Path) -> None:
        nonlocal checked
        with pytest.raises(PluginLifecycleLockError, match="unavailable"):
            with competitor.hold():
                pass
        checked = True
        original_replace(source, destination)

    monkeypatch.setattr(recovery_module.os, "replace", guarded_replace)

    report = recovery.recover_all()

    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    assert checked
    assert recovery.lifecycle_lock is recovery.plugin_manager.lifecycle_lock
    registry.close()


def test_recovery_maps_registry_scan_failure_to_safe_report(tmp_path: Path) -> None:
    recovery, registry, _, _, _ = setup_recovery(tmp_path)
    recovery.registry.list_all = Mock(
        side_effect=sqlite3.OperationalError("simulated registry failure")
    )

    report = recovery.recover_all()

    assert report.recovered == ()
    assert report.errors == (
        "plugin transaction recovery failed: simulated registry failure",
    )
    registry.close()


@pytest.mark.parametrize(
    ("action", "enabled"),
    (
        (PendingAction.ENABLE, False),
        (PendingAction.DISABLE, True),
    ),
)
def test_recovery_stops_interrupted_lifecycle_before_cas_to_disabled(
    tmp_path: Path,
    action: PendingAction,
    enabled: bool,
) -> None:
    recovery, registry, manager, _, record = setup_recovery(tmp_path)
    registry.upsert(replace(record, enabled=enabled, pending_action=action))
    observer = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    finish_lifecycle = Mock(wraps=registry.finish_lifecycle)
    registry.finish_lifecycle = finish_lifecycle

    def observe_stop(plugin_id: str) -> None:
        assert plugin_id == "example.plugin"
        current = observer.get(plugin_id)
        assert current is not None
        assert current.enabled is enabled
        assert current.pending_action is action
        finish_lifecycle.assert_not_called()

    manager._supervisor.stop.side_effect = observe_stop

    report = recovery.recover_all()

    assert report.recovered == ("example.plugin",)
    assert report.errors == ()
    manager._supervisor.stop.assert_called_once_with("example.plugin")
    finish_lifecycle.assert_called_once()
    expected, finalized_action = finish_lifecycle.call_args.args
    assert expected.pending_action is action
    assert finalized_action is action
    assert finish_lifecycle.call_args.kwargs == {"enabled": False}
    current = registry.get("example.plugin")
    assert current is not None
    assert not current.enabled
    assert current.pending_action is PendingAction.NONE
    observer.close()
    registry.close()


@pytest.mark.parametrize(
    ("action", "enabled"),
    (
        (PendingAction.ENABLE, False),
        (PendingAction.DISABLE, True),
    ),
)
def test_recovery_retains_interrupted_lifecycle_when_stop_fails(
    tmp_path: Path,
    action: PendingAction,
    enabled: bool,
) -> None:
    recovery, registry, manager, _, record = setup_recovery(tmp_path)
    registry.upsert(replace(record, enabled=enabled, pending_action=action))
    finish_lifecycle = Mock(wraps=registry.finish_lifecycle)
    registry.finish_lifecycle = finish_lifecycle
    manager._supervisor.stop.side_effect = RuntimeError("stop unconfirmed")

    report = recovery.recover_all()

    assert report.recovered == ()
    assert_errors = "\n".join(report.errors).lower()
    assert action.value.lower() in assert_errors
    assert "stop unconfirmed" in assert_errors
    manager._supervisor.stop.assert_called_once_with("example.plugin")
    finish_lifecycle.assert_not_called()
    current = registry.get("example.plugin")
    assert current is not None
    assert current.enabled is enabled
    assert current.pending_action is action
    registry.close()


def test_recovery_stops_pending_toggles_dependent_first(
    tmp_path: Path,
) -> None:
    recovery, registry, manager, installer, _ = setup_recovery(tmp_path)
    dependency_package = tmp_path / "dependency.modpkg"
    dependent_package = tmp_path / "dependent.modpkg"
    build_package(
        dependency_package,
        "1.0.0",
        plugin_id="z.dependency",
    )
    build_package(
        dependent_package,
        "1.0.0",
        plugin_id="a.dependent",
        dependencies=("z.dependency",),
    )
    assert installer.install(
        dependency_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    assert installer.install(
        dependent_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    for plugin_id in ("z.dependency", "a.dependent"):
        record = registry.get(plugin_id)
        assert record is not None
        registry.upsert(
            replace(
                record,
                enabled=True,
                pending_action=PendingAction.DISABLE,
            )
        )

    report = recovery.recover_all()

    assert [call.args[0] for call in manager._supervisor.stop.call_args_list] == [
        "a.dependent",
        "z.dependency",
    ]
    assert report.recovered == ("a.dependent", "z.dependency")
    assert report.errors == ()
    for plugin_id in ("z.dependency", "a.dependent"):
        current = registry.get(plugin_id)
        assert current is not None
        assert not current.enabled
        assert current.pending_action is PendingAction.NONE
    registry.close()


def test_recovery_preserves_dependency_when_dependent_stop_is_unconfirmed(
    tmp_path: Path,
) -> None:
    recovery, registry, manager, installer, _ = setup_recovery(tmp_path)
    dependency_package = tmp_path / "dependency.modpkg"
    dependent_package = tmp_path / "dependent.modpkg"
    build_package(
        dependency_package,
        "1.0.0",
        plugin_id="z.dependency",
    )
    build_package(
        dependent_package,
        "1.0.0",
        plugin_id="a.dependent",
        dependencies=("z.dependency",),
    )
    assert installer.install(
        dependency_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    assert installer.install(
        dependent_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    for plugin_id in ("z.dependency", "a.dependent"):
        record = registry.get(plugin_id)
        assert record is not None
        registry.upsert(
            replace(
                record,
                enabled=True,
                pending_action=PendingAction.DISABLE,
            )
        )

    def fail_dependent_stop(plugin_id: str) -> None:
        if plugin_id == "a.dependent":
            raise RuntimeError("dependent stop unconfirmed")

    manager._supervisor.stop.side_effect = fail_dependent_stop

    report = recovery.recover_all()

    assert report.recovered == ()
    assert [call.args[0] for call in manager._supervisor.stop.call_args_list] == [
        "a.dependent",
    ]
    assert any("dependent stop unconfirmed" in error for error in report.errors)
    assert any(
        "z.dependency: lifecycle recovery blocked by live dependents: "
        "a.dependent" in error
        for error in report.errors
    )
    for plugin_id in ("z.dependency", "a.dependent"):
        current = registry.get(plugin_id)
        assert current is not None
        assert current.enabled
        assert current.pending_action is PendingAction.DISABLE
    registry.close()


def test_transaction_recovery_restores_dependencies_before_dependents(
    tmp_path: Path,
) -> None:
    recovery, registry, _, installer, _ = setup_recovery(tmp_path)
    dependency_package = tmp_path / "dependency.modpkg"
    dependent_package = tmp_path / "dependent.modpkg"
    build_package(
        dependency_package,
        "1.0.0",
        plugin_id="z.dependency",
    )
    build_package(
        dependent_package,
        "1.0.0",
        plugin_id="a.dependent",
        dependencies=("z.dependency",),
    )
    assert installer.install(
        dependency_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    assert installer.install(
        dependent_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    for plugin_id in ("a.dependent", "z.dependency"):
        record = registry.get(plugin_id)
        assert record is not None
        registry.upsert(replace(record, pending_action=PendingAction.UPDATE))
    recover_record = Mock(wraps=recovery._recover_record)
    recovery._recover_record = recover_record

    report = recovery.recover_all()

    assert [call.args[0].plugin_id for call in recover_record.call_args_list] == [
        "z.dependency",
        "a.dependent",
    ]
    assert report.recovered == ("z.dependency", "a.dependent")
    assert report.errors == ()
    registry.close()


def test_transaction_recovery_rejects_invalid_candidate_before_file_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery, registry, manager, installer, old_record = setup_recovery(tmp_path)
    update_package = tmp_path / "update.modpkg"
    build_package(update_package, "1.1.0")
    updater = PluginUpdater(tmp_path / "mod", registry, installer, manager)
    assert updater.update(
        update_package,
        "example.plugin",
        approved_permissions=(),
        security_mode=SecurityMode.SAFE_MODE,
    ).updated
    dependent_package = tmp_path / "dependent.modpkg"
    build_package(
        dependent_package,
        "1.0.0",
        plugin_id="dependent.plugin",
        dependencies=("example.plugin",),
    )
    assert installer.install(
        dependent_package,
        security_mode=SecurityMode.SAFE_MODE,
    ).installed
    backup_manifest = (
        tmp_path
        / "mod"
        / "backups"
        / "example.plugin"
        / "1.0.0"
        / "plugin.json"
    )
    candidate = json.loads(backup_manifest.read_text(encoding="utf-8"))
    candidate["dependencies"] = ["dependent.plugin"]
    manifest_bytes = json.dumps(candidate).encode()
    backup_manifest.write_bytes(manifest_bytes)
    registry.upsert(
        replace(
            old_record,
            enabled=False,
            pending_action=PendingAction.UPDATE,
            manifest_hash=hashlib.sha256(manifest_bytes).hexdigest(),
        )
    )
    replace_spy = Mock(wraps=recovery_module.os.replace)
    monkeypatch.setattr(recovery_module.os, "replace", replace_spy)

    report = recovery.recover_all()

    assert report.recovered == ()
    assert any("dependency cycle" in error for error in report.errors)
    replace_spy.assert_not_called()
    current = registry.get("example.plugin")
    assert current is not None
    assert current.installed_version == "1.0.0"
    assert current.pending_action is PendingAction.UPDATE
    assert (
        tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py"
    ).read_text() == "VERSION = '1.1.0'\n"
    assert backup_manifest.is_file()
    registry.close()
