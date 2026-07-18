from __future__ import annotations

import json
from pathlib import Path
import threading
import time

import pytest

import core.settings as settings_module
from core.settings import (
    MAX_SETTINGS_BYTES,
    SETTINGS_SCHEMA_VERSION,
    Settings,
    SettingsService,
    SettingsWriteBlockedError,
)


def _save_is_blocked_without_changing_source(
    service: SettingsService,
    original: bytes,
) -> None:
    with pytest.raises(SettingsWriteBlockedError):
        service.save(Settings())
    assert service.path.read_bytes() == original
    assert not tuple(service.path.parent.glob(f".{service.path.name}.*.tmp"))


def test_missing_settings_round_trip_uses_flat_current_schema(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")

    service.save(Settings(theme="dark", language="ja"))

    document = json.loads(service.path.read_text(encoding="utf-8"))
    assert document["schema_version"] == SETTINGS_SCHEMA_VERSION
    assert document["theme"] == "dark"
    assert service.load() == Settings(theme="dark", language="ja")
    result = service.load_with_status()
    assert result.state == "current"
    assert result.writable


def test_corrupt_settings_are_read_only_and_preserved(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = b'{"language":'
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.settings == Settings()
    assert result.state == "corrupt"
    assert not result.writable
    assert result.diagnostics == ("invalid_json",)
    _save_is_blocked_without_changing_source(service, original)


def test_deeply_nested_settings_are_read_only_and_preserved(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = (
        '{"schema_version":1,"nested":' + "[" * 20_000 + "0" + "]" * 20_000 + "}"
    ).encode("utf-8")
    assert len(original) < MAX_SETTINGS_BYTES
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.state == "corrupt"
    assert not result.writable
    assert result.diagnostics == ("invalid_json",)
    _save_is_blocked_without_changing_source(service, original)


def test_list_settings_are_read_only_instead_of_crashing(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = b"[]"
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.settings == Settings()
    assert result.state == "invalid"
    assert not result.writable
    assert result.diagnostics == ("top_level_not_object",)
    _save_is_blocked_without_changing_source(service, original)


def test_wrong_known_field_types_default_per_field_and_block_save(
    tmp_path: Path,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    document = {
        "theme": "dark",
        "language": [],
        "ui_scale": 3,
        "download_workers": True,
        "portable_mode": "false",
        "log_level": [],
        "in_app_download_notifications": 1,
        "system_download_notifications": "false",
        "initial_mod_setup_completed": "false",
    }
    original = json.dumps(document).encode("utf-8")
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.settings.theme == "dark"
    assert result.settings.language == "zh-TW"
    assert result.settings.ui_scale == "standard"
    assert result.settings.download_workers == 2
    assert result.settings.portable_mode is False
    assert result.settings.log_level == "INFO"
    assert result.settings.in_app_download_notifications is True
    assert result.settings.system_download_notifications is False
    assert result.settings.initial_mod_setup_completed is False
    assert result.state == "invalid"
    assert not result.writable
    assert set(result.diagnostics) == {
        "invalid_type:language",
        "invalid_type:ui_scale",
        "invalid_type:download_workers",
        "invalid_type:portable_mode",
        "invalid_type:log_level",
        "invalid_type:in_app_download_notifications",
        "invalid_type:system_download_notifications",
        "invalid_type:initial_mod_setup_completed",
    }
    _save_is_blocked_without_changing_source(service, original)


def test_future_schema_is_read_only_and_preserved(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    document = {
        "schema_version": SETTINGS_SCHEMA_VERSION + 1,
        "language": "ja",
        "future_setting": {"enabled": True},
    }
    original = json.dumps(document).encode("utf-8")
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.settings == Settings()
    assert result.state == "future"
    assert not result.writable
    assert result.diagnostics == (
        f"unsupported_future_schema:{SETTINGS_SCHEMA_VERSION + 1}",
    )
    assert result.unknown_keys == ("future_setting",)
    _save_is_blocked_without_changing_source(service, original)


@pytest.mark.parametrize("schema_version", [True, 0, "1"])
def test_invalid_schema_version_is_read_only(
    tmp_path: Path,
    schema_version: object,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = json.dumps({"schema_version": schema_version}).encode("utf-8")
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.state == "invalid"
    assert not result.writable
    assert result.diagnostics == ("invalid_schema_version",)
    _save_is_blocked_without_changing_source(service, original)


def test_unknown_keys_survive_current_schema_round_trip(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    document = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "language": "zh-TW",
        "future_ui": {"density": "wide"},
        "extension_flag": True,
    }
    service.path.write_text(json.dumps(document), encoding="utf-8")
    result = service.load_with_status()
    result.settings.language = "en"

    service.save(result.settings)

    saved = json.loads(service.path.read_text(encoding="utf-8"))
    assert result.unknown_keys == ("extension_flag", "future_ui")
    assert saved["future_ui"] == {"density": "wide"}
    assert saved["extension_flag"] is True
    assert saved["language"] == "en"


@pytest.mark.parametrize(
    "document",
    [
        {"language": "ja"},
        {"schema_version": SETTINGS_SCHEMA_VERSION, "language": "ja"},
    ],
)
def test_existing_settings_without_initial_setup_flag_skip_upgrade_wizard(
    tmp_path: Path,
    document: dict[str, object],
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.path.write_text(json.dumps(document), encoding="utf-8")

    result = service.load_with_status()

    assert result.settings.initial_mod_setup_completed is True


def test_truly_missing_settings_keep_initial_setup_required(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")

    result = service.load_with_status()

    assert result.state == "missing"
    assert result.settings.initial_mod_setup_completed is False


def test_patch_merges_only_requested_fields_from_latest_source(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.save(Settings(language="en", system_download_notifications=False))
    stale = service.load()

    first = service.patch(system_download_notifications=True)
    second = service.patch(ui_scale="large")

    assert stale.system_download_notifications is False
    assert first.system_download_notifications is True
    assert second.system_download_notifications is True
    assert second.ui_scale == "large"
    assert service.load().system_download_notifications is True


@pytest.mark.parametrize(
    "original",
    [
        b'{"schema_version":99,"future_only":true}',
        b'{"schema_version":',
    ],
)
def test_patch_fails_closed_for_future_or_corrupt_source(
    tmp_path: Path,
    original: bytes,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.path.write_bytes(original)

    with pytest.raises(SettingsWriteBlockedError):
        service.patch(language="ja")

    assert service.path.read_bytes() == original


def test_patch_rejects_source_revision_change_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.save(Settings(language="en"))
    replacement = b'{"schema_version":99,"future_only":true}'
    original_atomic_write = service._atomic_write

    def replace_source(
        payload: bytes,
        *,
        expected_source: bytes | None,
    ) -> None:
        service.path.write_bytes(replacement)
        original_atomic_write(payload, expected_source=expected_source)

    monkeypatch.setattr(service, "_atomic_write", replace_source)

    with pytest.raises(SettingsWriteBlockedError, match="source changed"):
        service.patch(language="ja")

    assert service.path.read_bytes() == replacement
    assert not tuple(tmp_path.glob(".settings.json.*.tmp"))


def test_patch_serializes_writers_and_preserves_non_overlapping_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = SettingsService(tmp_path / "settings.json")
    second = SettingsService(tmp_path / "settings.json")
    first.save(Settings(language="en", ui_scale="standard"))
    entered_write = threading.Event()
    release_write = threading.Event()
    second_done = threading.Event()
    errors: list[BaseException] = []
    original_atomic_write = first._atomic_write

    def paused_write(
        payload: bytes,
        *,
        expected_source: bytes | None,
    ) -> None:
        entered_write.set()
        assert release_write.wait(2.0)
        original_atomic_write(payload, expected_source=expected_source)

    monkeypatch.setattr(first, "_atomic_write", paused_write)

    def run_patch(service: SettingsService, **changes: object) -> None:
        try:
            service.patch(**changes)
        except BaseException as error:
            errors.append(error)
        finally:
            if service is second:
                second_done.set()

    first_thread = threading.Thread(
        target=run_patch,
        args=(first,),
        kwargs={"language": "ja"},
    )
    second_thread = threading.Thread(
        target=run_patch,
        args=(second,),
        kwargs={"ui_scale": "large"},
    )
    first_thread.start()
    assert entered_write.wait(2.0)
    second_thread.start()
    time.sleep(0.05)
    assert not second_done.is_set()
    release_write.set()
    first_thread.join(2.0)
    second_thread.join(2.0)

    assert not errors
    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert first.load().language == "ja"
    assert first.load().ui_scale == "large"


def test_lock_timeout_closes_handle_and_later_patch_can_succeed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SettingsService(
        tmp_path / "settings.json",
        lock_timeout_seconds=0,
    )
    monkeypatch.setattr(settings_module, "_try_acquire_file_lock", lambda _: False)

    with pytest.raises(SettingsWriteBlockedError, match="lock timed out"):
        service.patch(language="ja")

    lock_path = tmp_path / ".settings.json.lock"
    lock_path.unlink()
    monkeypatch.undo()
    assert service.patch(language="ja").language == "ja"


def test_legacy_first_write_creates_immutable_exact_backup(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = b'{\n  "theme": "dark",\n  "extension_flag": true\n}'
    service.path.write_bytes(original)
    result = service.load_with_status()
    assert result.state == "legacy"
    assert result.writable

    service.save(result.settings)

    backups = tuple((tmp_path / "backups").glob("settings.pre-35.*.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    saved = json.loads(service.path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == SETTINGS_SCHEMA_VERSION
    assert saved["extension_flag"] is True

    result = service.load_with_status()
    result.settings.theme = "system"
    service.save(result.settings)
    assert tuple((tmp_path / "backups").glob("settings.pre-35.*.json")) == backups
    assert backups[0].read_bytes() == original


def test_atomic_replace_failure_preserves_original_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = json.dumps(
        {"schema_version": SETTINGS_SCHEMA_VERSION, "theme": "system"}
    ).encode("utf-8")
    service.path.write_bytes(original)
    monkeypatch.setattr(settings_module.time, "sleep", lambda _: None)

    def reject_replace(self: Path, target: Path) -> Path:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "replace", reject_replace)

    with pytest.raises(PermissionError, match="locked"):
        service.save(Settings(theme="dark"))

    assert service.path.read_bytes() == original
    assert not tuple(tmp_path.glob(".settings.json.*.tmp"))


def test_save_rejects_wrong_typed_settings_before_creating_file(
    tmp_path: Path,
) -> None:
    service = SettingsService(tmp_path / "settings.json")
    settings = Settings()
    settings.log_level = []  # type: ignore[assignment]

    with pytest.raises(SettingsWriteBlockedError, match="log_level"):
        service.save(settings)

    assert not service.path.exists()


def test_oversized_settings_are_read_only_and_preserved(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    original = b" " * (MAX_SETTINGS_BYTES + 1)
    service.path.write_bytes(original)

    result = service.load_with_status()

    assert result.state == "unreadable"
    assert not result.writable
    assert result.diagnostics == ("document_too_large",)
    _save_is_blocked_without_changing_source(service, original)
