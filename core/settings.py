"""Minimal, defensive JSON settings service."""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import time
import uuid
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import BinaryIO, Iterator, Literal

from core.localization import SUPPORTED_LOCALE_CODES, normalized_core_locale

SUPPORTED_UI_LANGUAGES = SUPPORTED_LOCALE_CODES
SETTINGS_SCHEMA_VERSION = 1
MAX_SETTINGS_BYTES = 64 * 1024
SETTINGS_LOCK_TIMEOUT_SECONDS = 2.0
SETTINGS_LOCK_POLL_SECONDS = 0.02

SettingsState = Literal[
    "missing",
    "legacy",
    "current",
    "corrupt",
    "invalid",
    "future",
    "unreadable",
]


@dataclass(slots=True)
class Settings:
    theme: str = "system"
    language: str = "zh-TW"
    ui_scale: str = "standard"
    download_workers: int = 2
    portable_mode: bool = False
    log_level: str = "INFO"
    in_app_download_notifications: bool = True
    system_download_notifications: bool = False
    initial_mod_setup_completed: bool = False


@dataclass(frozen=True, slots=True)
class SettingsLoadResult:
    """Settings plus the minimum safe persistence state for the caller."""

    settings: Settings
    state: SettingsState
    writable: bool
    diagnostics: tuple[str, ...] = ()
    unknown_keys: tuple[str, ...] = ()


class SettingsWriteBlockedError(OSError):
    """Raised when saving could destroy an unsupported settings document."""


_SETTINGS_TYPES: dict[str, type[object]] = {
    "theme": str,
    "language": str,
    "ui_scale": str,
    "download_workers": int,
    "portable_mode": bool,
    "log_level": str,
    "in_app_download_notifications": bool,
    "system_download_notifications": bool,
    "initial_mod_setup_completed": bool,
}
_SETTINGS_FIELD_NAMES = frozenset(item.name for item in fields(Settings))


def normalized_download_workers(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        return 2
    return max(1, min(value, 4))


def normalized_language(value: object) -> str:
    return normalized_core_locale(value)


def _invalid_field_types(values: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        name
        for name, expected in _SETTINGS_TYPES.items()
        if name in values and type(values[name]) is not expected
    )


def _try_acquire_file_lock(handle: BinaryIO) -> bool:
    """Acquire one byte exclusively without blocking the caller thread."""

    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in {errno.EACCES, errno.EAGAIN} or getattr(
            error, "winerror", None
        ) in {33, 36}:
            return False
        raise
    return True


def _release_file_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def settings_file_lock(
    path: Path,
    *,
    timeout_seconds: float = SETTINGS_LOCK_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """Hold the interprocess lock shared by every settings-file writer."""

    timeout = max(0.0, float(timeout_seconds))
    if not math.isfinite(timeout):
        raise SettingsWriteBlockedError("settings lock timeout must be finite")
    lock_path = path.with_name(f".{path.name}.lock")
    if path.parent.is_symlink() or lock_path.is_symlink():
        raise SettingsWriteBlockedError("settings lock path is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = lock_path.open("a+b")
    except OSError as error:
        raise SettingsWriteBlockedError("settings lock cannot be opened") from error

    acquired = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                acquired = _try_acquire_file_lock(handle)
            except OSError as error:
                raise SettingsWriteBlockedError(
                    "settings lock cannot be acquired"
                ) from error
            if acquired:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SettingsWriteBlockedError("settings lock timed out")
            time.sleep(min(SETTINGS_LOCK_POLL_SECONDS, remaining))
        yield
    finally:
        if acquired:
            # Closing the descriptor also releases OS-owned locks after a crash;
            # suppressing unlock errors avoids reporting a completed write as failed.
            with suppress(OSError):
                _release_file_lock(handle)
        handle.close()


class SettingsService:
    def __init__(
        self,
        path: Path,
        *,
        lock_timeout_seconds: float = SETTINGS_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.path = path
        self.lock_timeout_seconds = max(0.0, float(lock_timeout_seconds))

    def load(self) -> Settings:
        """Load settings while preserving the original compatibility API."""

        return self.load_with_status().settings

    def load_with_status(self) -> SettingsLoadResult:
        """Load settings and report whether the source can be safely replaced."""

        result, _, _ = self._inspect()
        return result

    def save(self, settings: Settings) -> None:
        """Atomically save typed settings without discarding unknown fields."""

        known_values = self._validated_values(settings)
        with self._settings_lock():
            result, source, raw_bytes = self._writable_inspection()
            self._write_inspected(
                known_values,
                result=result,
                source=source,
                raw_bytes=raw_bytes,
            )

    def patch(self, **changes: object) -> Settings:
        """Merge typed fields into the latest on-disk settings under one lock."""

        unknown_fields = tuple(sorted(set(changes) - _SETTINGS_FIELD_NAMES))
        if unknown_fields:
            raise SettingsWriteBlockedError(
                f"unknown settings fields: {', '.join(unknown_fields)}"
            )
        invalid_fields = _invalid_field_types(changes)
        if invalid_fields:
            raise SettingsWriteBlockedError(
                f"settings values have invalid types: {', '.join(invalid_fields)}"
            )

        with self._settings_lock():
            result, source, raw_bytes = self._writable_inspection()
            if not changes:
                return result.settings
            latest_values = asdict(result.settings)
            latest_values.update(changes)
            merged = Settings(**latest_values)
            self._write_inspected(
                latest_values,
                result=result,
                source=source,
                raw_bytes=raw_bytes,
            )
            return merged

    @staticmethod
    def _validated_values(settings: Settings) -> dict[str, object]:
        if not isinstance(settings, Settings):
            raise SettingsWriteBlockedError("settings object type is invalid")
        known_values = asdict(settings)
        invalid_fields = _invalid_field_types(known_values)
        if invalid_fields:
            raise SettingsWriteBlockedError(
                f"settings values have invalid types: {', '.join(invalid_fields)}"
            )
        return known_values

    def _writable_inspection(
        self,
    ) -> tuple[SettingsLoadResult, dict[str, object] | None, bytes | None]:
        result, source, raw_bytes = self._inspect()
        if not result.writable:
            detail = ", ".join(result.diagnostics) or result.state
            raise SettingsWriteBlockedError(
                f"settings file is read-only for safety: {detail}"
            )
        return result, source, raw_bytes

    def _write_inspected(
        self,
        known_values: dict[str, object],
        *,
        result: SettingsLoadResult,
        source: dict[str, object] | None,
        raw_bytes: bytes | None,
    ) -> None:
        if result.state == "legacy":
            if raw_bytes is None:
                raise SettingsWriteBlockedError("legacy settings bytes are missing")
            self._ensure_legacy_backup(raw_bytes)

        document: dict[str, object] = {"schema_version": SETTINGS_SCHEMA_VERSION}
        if source is not None:
            document.update(
                {
                    key: value
                    for key, value in source.items()
                    if key not in _SETTINGS_FIELD_NAMES and key != "schema_version"
                }
            )
        document.update(known_values)
        payload = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
        if len(payload) > MAX_SETTINGS_BYTES:
            raise SettingsWriteBlockedError("settings document is too large")
        self._atomic_write(payload, expected_source=raw_bytes)

    @contextmanager
    def _settings_lock(self) -> Iterator[None]:
        with settings_file_lock(
            self.path,
            timeout_seconds=self.lock_timeout_seconds,
        ):
            yield

    def _inspect(
        self,
    ) -> tuple[
        SettingsLoadResult,
        dict[str, object] | None,
        bytes | None,
    ]:
        if self.path.is_symlink():
            return self._unsafe_result("unsafe_symlink"), None, None
        if not self.path.exists():
            return SettingsLoadResult(Settings(), "missing", True), None, None
        try:
            if not self.path.is_file():
                return self._unsafe_result("not_a_regular_file"), None, None
            if self.path.stat().st_size > MAX_SETTINGS_BYTES:
                return self._unsafe_result("document_too_large"), None, None
            raw_bytes = self.path.read_bytes()
            if len(raw_bytes) > MAX_SETTINGS_BYTES:
                return self._unsafe_result("document_too_large"), None, None
        except OSError as error:
            diagnostic = f"read_error:{type(error).__name__}"
            return (
                SettingsLoadResult(Settings(), "unreadable", False, (diagnostic,)),
                None,
                None,
            )
        try:
            raw = json.loads(raw_bytes.decode("utf-8"))
        except UnicodeDecodeError, json.JSONDecodeError, RecursionError:
            return (
                SettingsLoadResult(Settings(), "corrupt", False, ("invalid_json",)),
                None,
                raw_bytes,
            )
        if not isinstance(raw, dict):
            return (
                SettingsLoadResult(
                    Settings(), "invalid", False, ("top_level_not_object",)
                ),
                None,
                raw_bytes,
            )

        source = {str(key): value for key, value in raw.items()}
        unknown_keys = tuple(
            sorted(set(source) - _SETTINGS_FIELD_NAMES - {"schema_version"})
        )
        schema_version = source.get("schema_version")
        if "schema_version" not in source:
            state: SettingsState = "legacy"
        elif type(schema_version) is not int or schema_version < 1:
            return (
                SettingsLoadResult(
                    Settings(),
                    "invalid",
                    False,
                    ("invalid_schema_version",),
                    unknown_keys,
                ),
                source,
                raw_bytes,
            )
        elif schema_version > SETTINGS_SCHEMA_VERSION:
            return (
                SettingsLoadResult(
                    Settings(),
                    "future",
                    False,
                    (f"unsupported_future_schema:{schema_version}",),
                    unknown_keys,
                ),
                source,
                raw_bytes,
            )
        else:
            state = "current"

        defaults = asdict(Settings())
        if "initial_mod_setup_completed" not in source:
            # Existing installations predate the one-time wizard. Treating them as
            # new installs could disable MODs or cancel recovered work on upgrade.
            defaults["initial_mod_setup_completed"] = True
        invalid_fields = _invalid_field_types(source)
        for name in _SETTINGS_FIELD_NAMES:
            if name in source and name not in invalid_fields:
                defaults[name] = source[name]
        settings = Settings(**defaults)
        if invalid_fields:
            return (
                SettingsLoadResult(
                    settings,
                    "invalid",
                    False,
                    tuple(f"invalid_type:{name}" for name in invalid_fields),
                    unknown_keys,
                ),
                source,
                raw_bytes,
            )
        return (
            SettingsLoadResult(
                settings,
                state,
                True,
                unknown_keys=unknown_keys,
            ),
            source,
            raw_bytes,
        )

    @staticmethod
    def _unsafe_result(diagnostic: str) -> SettingsLoadResult:
        return SettingsLoadResult(Settings(), "unreadable", False, (diagnostic,))

    def _ensure_legacy_backup(self, raw_bytes: bytes) -> Path:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        backup_root = self.path.parent / "backups"
        if self.path.parent.is_symlink() or backup_root.is_symlink():
            raise SettingsWriteBlockedError("settings backup path is unsafe")
        backup_root.mkdir(parents=True, exist_ok=True)
        target = backup_root / f"{self.path.stem}.pre-35.{digest}.json"
        if target.is_symlink():
            raise SettingsWriteBlockedError("settings backup target is unsafe")
        if target.exists():
            try:
                if not target.is_file() or target.read_bytes() != raw_bytes:
                    raise SettingsWriteBlockedError(
                        "existing settings backup does not match its source"
                    )
            except OSError as error:
                raise SettingsWriteBlockedError(
                    "existing settings backup cannot be verified"
                ) from error
            return target

        created = False
        try:
            with target.open("xb") as output:
                created = True
                output.write(raw_bytes)
                output.flush()
                os.fsync(output.fileno())
            if target.read_bytes() != raw_bytes:
                raise SettingsWriteBlockedError("settings backup verification failed")
        except FileExistsError:
            try:
                if not target.is_file() or target.read_bytes() != raw_bytes:
                    raise SettingsWriteBlockedError(
                        "concurrent settings backup does not match its source"
                    )
            except OSError as error:
                raise SettingsWriteBlockedError(
                    "concurrent settings backup cannot be verified"
                ) from error
        except Exception:
            if created:
                target.unlink(missing_ok=True)
            raise
        return target

    def _source_is_unchanged(self, expected_source: bytes | None) -> bool:
        if self.path.is_symlink():
            return False
        if expected_source is None:
            return not self.path.exists()
        try:
            if not self.path.is_file():
                return False
            with self.path.open("rb") as source:
                return source.read(len(expected_source) + 1) == expected_source
        except OSError:
            return False

    def _atomic_write(
        self,
        payload: bytes,
        *,
        expected_source: bytes | None,
    ) -> None:
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise SettingsWriteBlockedError("settings destination is unsafe")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            if not self._source_is_unchanged(expected_source):
                raise SettingsWriteBlockedError("settings source changed during write")
            for attempt in range(3):
                try:
                    temporary.replace(self.path)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)
