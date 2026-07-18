from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading

import pytest

import tools.settings_rollback as rollback_module
from core.settings import (
    MAX_SETTINGS_BYTES,
    SettingsService,
    SettingsWriteBlockedError,
)
from tools.settings_rollback import (
    SettingsRollbackError,
    apply_settings_rollback,
    main,
    plan_settings_rollback,
)


def _settings_with_backup(
    root: Path,
    *,
    current: bytes | None = None,
    legacy: bytes | None = None,
) -> tuple[Path, Path, bytes, bytes]:
    current_bytes = current or b'{"schema_version": 1, "language": "ja"}'
    legacy_bytes = legacy or b'{"language": "zh-TW", "extension": true}'
    settings = root / "settings.json"
    settings.write_bytes(current_bytes)
    backup_root = root / "backups"
    backup_root.mkdir()
    digest = hashlib.sha256(legacy_bytes).hexdigest()
    backup = backup_root / f"settings.pre-35.{digest}.json"
    backup.write_bytes(legacy_bytes)
    return settings, backup, current_bytes, legacy_bytes


def test_cli_defaults_to_dry_run_and_does_not_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings, backup, current, legacy = _settings_with_backup(tmp_path)

    assert main(["--settings", str(settings)]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN"
    assert report["settings_name"] == "settings.json"
    assert report["backup_name"] == backup.name
    assert report["current_sha256"] == hashlib.sha256(current).hexdigest()
    assert report["backup_sha256"] == hashlib.sha256(legacy).hexdigest()
    assert report["would_change"] is True
    assert settings.read_bytes() == current
    assert tuple((tmp_path / "backups").iterdir()) == (backup,)


def test_apply_requires_confirmed_digest_and_preserves_current_bytes(
    tmp_path: Path,
) -> None:
    settings, _backup, current, legacy = _settings_with_backup(tmp_path)
    digest = hashlib.sha256(current).hexdigest()

    result = apply_settings_rollback(
        settings, expected_current_sha256=digest
    )

    assert settings.read_bytes() == legacy
    assert result.current_backup_path.read_bytes() == current
    assert digest in result.current_backup_path.name
    assert result.current_backup_path.parent == tmp_path / "backups"
    assert not tuple(tmp_path.glob(".settings.json.pre35-restore.*.tmp"))


def test_apply_without_or_with_wrong_confirmation_is_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings, backup, current, _legacy = _settings_with_backup(tmp_path)

    assert main(["--settings", str(settings), "--apply"]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "BLOCKED"
    with pytest.raises(SettingsRollbackError, match="differs"):
        apply_settings_rollback(
            settings,
            expected_current_sha256="0" * 64,
        )

    assert settings.read_bytes() == current
    assert tuple((tmp_path / "backups").iterdir()) == (backup,)


def test_apply_rejects_unbounded_lock_timeout(tmp_path: Path) -> None:
    settings, backup, current, _legacy = _settings_with_backup(tmp_path)

    with pytest.raises(SettingsRollbackError, match="timeout must be finite"):
        apply_settings_rollback(
            settings,
            expected_current_sha256=hashlib.sha256(current).hexdigest(),
            lock_timeout_seconds=float("inf"),
        )

    assert settings.read_bytes() == current
    assert tuple((tmp_path / "backups").iterdir()) == (backup,)


def test_tampered_filename_digest_is_rejected(tmp_path: Path) -> None:
    settings, backup, current, _legacy = _settings_with_backup(tmp_path)
    renamed = backup.with_name(f"settings.pre-35.{'0' * 64}.json")
    backup.rename(renamed)

    with pytest.raises(SettingsRollbackError, match="does not match"):
        plan_settings_rollback(settings)

    assert settings.read_bytes() == current


@pytest.mark.parametrize(
    ("legacy", "message"),
    [
        (b"[]", "not a JSON object"),
        (b'{"schema_version": 2}', "not an unambiguous pre-35"),
        (b'{"download_workers": true}', "invalid known field types"),
    ],
)
def test_invalid_or_future_backup_type_is_rejected(
    tmp_path: Path,
    legacy: bytes,
    message: str,
) -> None:
    settings, _backup, current, _legacy = _settings_with_backup(
        tmp_path, legacy=legacy
    )

    with pytest.raises(SettingsRollbackError, match=message):
        plan_settings_rollback(settings)

    assert settings.read_bytes() == current


def test_oversized_backup_is_rejected(tmp_path: Path) -> None:
    oversized = b" " * (MAX_SETTINGS_BYTES + 1)
    settings, _backup, current, _legacy = _settings_with_backup(
        tmp_path, legacy=oversized
    )

    with pytest.raises(SettingsRollbackError, match="size limit"):
        plan_settings_rollback(settings)

    assert settings.read_bytes() == current


def test_automatic_selection_rejects_multiple_backups(
    tmp_path: Path,
) -> None:
    settings, first, current, _legacy = _settings_with_backup(tmp_path)
    other_bytes = b'{"language": "en"}'
    second = first.with_name(
        f"settings.pre-35.{hashlib.sha256(other_bytes).hexdigest()}.json"
    )
    second.write_bytes(other_bytes)

    with pytest.raises(SettingsRollbackError, match="explicit --backup"):
        plan_settings_rollback(settings)

    selected = plan_settings_rollback(settings, backup_path=first)
    assert selected.backup_path == first
    assert settings.read_bytes() == current


def test_explicit_backup_cannot_escape_backup_directory(tmp_path: Path) -> None:
    settings, _backup, current, legacy = _settings_with_backup(tmp_path)
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    outside = outside_root / (
        f"settings.pre-35.{hashlib.sha256(legacy).hexdigest()}.json"
    )
    outside.write_bytes(legacy)

    with pytest.raises(SettingsRollbackError, match="directly inside"):
        plan_settings_rollback(settings, backup_path=outside)

    assert settings.read_bytes() == current


def test_noncanonical_settings_filename_is_rejected(tmp_path: Path) -> None:
    settings = tmp_path / "other.json"
    settings.write_text("{}", encoding="utf-8")

    with pytest.raises(SettingsRollbackError, match="exact settings.json"):
        plan_settings_rollback(settings)


def test_atomic_replace_failure_preserves_current_and_owned_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, _backup, current, _legacy = _settings_with_backup(tmp_path)

    def reject_replace(source: Path, target: Path) -> None:
        raise PermissionError("settings file is locked")

    monkeypatch.setattr(rollback_module.os, "replace", reject_replace)

    with pytest.raises(PermissionError, match="locked"):
        apply_settings_rollback(
            settings,
            expected_current_sha256=hashlib.sha256(current).hexdigest(),
        )

    assert settings.read_bytes() == current
    owned = tuple(
        (tmp_path / "backups").glob("settings.before-pre35-restore.*.json")
    )
    assert len(owned) == 1
    assert owned[0].read_bytes() == current
    assert not tuple(tmp_path.glob(".settings.json.pre35-restore.*.tmp"))


def test_linklike_backup_is_rejected(tmp_path: Path) -> None:
    settings, backup, current, legacy = _settings_with_backup(tmp_path)
    target = tmp_path / "legacy-target.json"
    target.write_bytes(legacy)
    backup.unlink()
    try:
        backup.symlink_to(target)
    except OSError:
        pytest.skip("link creation is unavailable in this Windows environment")

    with pytest.raises(SettingsRollbackError, match="link-like"):
        plan_settings_rollback(settings)

    assert settings.read_bytes() == current


def test_linklike_detection_fails_closed_without_platform_link_privileges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, backup, current, _legacy = _settings_with_backup(tmp_path)
    original_is_linklike = rollback_module._is_linklike
    monkeypatch.setattr(
        rollback_module,
        "_is_linklike",
        lambda path: path == backup or original_is_linklike(path),
    )

    with pytest.raises(SettingsRollbackError, match="link-like"):
        plan_settings_rollback(settings)

    assert settings.read_bytes() == current


def test_current_change_after_owned_backup_blocks_atomic_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, _backup, current, _legacy = _settings_with_backup(tmp_path)
    original_write = rollback_module._write_new_file
    calls = 0

    def change_after_owned_backup(path: Path, payload: bytes, *, label: str) -> None:
        nonlocal calls
        original_write(path, payload, label=label)
        calls += 1
        if calls == 1:
            settings.write_bytes(b'{"schema_version": 1, "language": "en"}')

    monkeypatch.setattr(
        rollback_module, "_write_new_file", change_after_owned_backup
    )

    with pytest.raises(SettingsRollbackError, match="changed after"):
        apply_settings_rollback(
            settings,
            expected_current_sha256=hashlib.sha256(current).hexdigest(),
        )

    assert json.loads(settings.read_text(encoding="utf-8"))["language"] == "en"
    owned = tuple(
        (tmp_path / "backups").glob("settings.before-pre35-restore.*.json")
    )
    assert len(owned) == 1
    assert owned[0].read_bytes() == current
    assert not tuple(tmp_path.glob(".settings.json.pre35-restore.*.tmp"))


def test_apply_holds_shared_writer_lock_through_backup_and_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, _backup, current, legacy = _settings_with_backup(tmp_path)
    original_write = rollback_module._write_new_file
    owned_backup_created = threading.Event()
    allow_restore_to_continue = threading.Event()
    failures: list[BaseException] = []

    def pause_after_owned_backup(
        path: Path,
        payload: bytes,
        *,
        label: str,
    ) -> None:
        original_write(path, payload, label=label)
        if label == "owned current-settings backup":
            owned_backup_created.set()
            if not allow_restore_to_continue.wait(timeout=5):
                raise AssertionError("test did not release the rollback transaction")

    monkeypatch.setattr(rollback_module, "_write_new_file", pause_after_owned_backup)

    def restore() -> None:
        try:
            apply_settings_rollback(
                settings,
                expected_current_sha256=hashlib.sha256(current).hexdigest(),
            )
        except BaseException as error:
            failures.append(error)

    restore_thread = threading.Thread(target=restore)
    restore_thread.start()
    assert owned_backup_created.wait(timeout=5)

    competing_writer = SettingsService(settings, lock_timeout_seconds=0)
    with pytest.raises(SettingsWriteBlockedError, match="lock timed out"):
        competing_writer.patch(language="en")

    allow_restore_to_continue.set()
    restore_thread.join(timeout=5)
    assert not restore_thread.is_alive()
    assert failures == []
    assert settings.read_bytes() == legacy
