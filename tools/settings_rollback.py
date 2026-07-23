"""Fail-closed operator tool for restoring a verified pre-35 settings file.

The command is a dry-run unless ``--apply`` and the current settings digest
reported by that dry-run are both supplied.  It never reads or writes actual
user settings during tests; callers select the settings path explicitly.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Sequence
import uuid

from core.settings import (
    MAX_SETTINGS_BYTES,
    SETTINGS_LOCK_TIMEOUT_SECONDS,
    Settings,
    SettingsWriteBlockedError,
    settings_file_lock,
)


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class SettingsRollbackError(RuntimeError):
    """A settings restore was rejected before an unsafe write."""


@dataclass(frozen=True, slots=True)
class SettingsRollbackPlan:
    settings_path: Path
    backup_path: Path
    current_sha256: str
    backup_sha256: str
    current_size: int
    backup_size: int

    @property
    def would_change(self) -> bool:
        return self.current_sha256 != self.backup_sha256

    def public_report(self) -> dict[str, object]:
        """Return a bounded report without exposing a user-profile path."""

        return {
            "status": "DRY_RUN",
            "settings_name": self.settings_path.name,
            "backup_name": self.backup_path.name,
            "current_sha256": self.current_sha256,
            "backup_sha256": self.backup_sha256,
            "current_size": self.current_size,
            "backup_size": self.backup_size,
            "would_change": self.would_change,
            "apply_requires_current_sha256": True,
        }


@dataclass(frozen=True, slots=True)
class SettingsRollbackResult:
    plan: SettingsRollbackPlan
    current_backup_path: Path

    def public_report(self) -> dict[str, object]:
        """Return an apply report without exposing a user-profile path."""

        return {
            "status": "APPLIED",
            "settings_name": self.plan.settings_path.name,
            "source_backup_name": self.plan.backup_path.name,
            "current_backup_name": self.current_backup_path.name,
            "current_backup_sha256": self.plan.current_sha256,
            "restored_sha256": self.plan.backup_sha256,
        }


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_linklike(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(is_junction is not None and is_junction())
    except OSError as error:
        raise SettingsRollbackError("path type cannot be verified") from error


def _safe_absolute(path: Path, *, label: str) -> Path:
    """Normalize a path without accepting an existing symlink or junction."""

    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if _is_linklike(current):
            raise SettingsRollbackError(f"{label} contains a link-like path")
    return absolute


def _read_regular_file(path: Path, *, label: str) -> bytes:
    """Read one stable, bounded regular file through an owned descriptor."""

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SettingsRollbackError(f"{label} cannot be opened safely") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SettingsRollbackError(f"{label} is not a regular file")
        if before.st_size > MAX_SETTINGS_BYTES:
            raise SettingsRollbackError(f"{label} exceeds the size limit")
        chunks: list[bytes] = []
        remaining = MAX_SETTINGS_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 16 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(payload) > MAX_SETTINGS_BYTES:
        raise SettingsRollbackError(f"{label} exceeds the size limit")
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or len(payload) != after.st_size:
        raise SettingsRollbackError(f"{label} changed while it was read")
    return payload


def _backup_name_pattern(settings_path: Path) -> re.Pattern[str]:
    return re.compile(
        rf"{re.escape(settings_path.stem)}\.pre-35\.([0-9a-f]{{64}})\.json"
    )


def _select_backup(
    settings_path: Path,
    explicit_backup: Path | None,
) -> tuple[Path, str]:
    backup_root = _safe_absolute(
        settings_path.parent / "backups", label="backup directory"
    )
    pattern = _backup_name_pattern(settings_path)
    if explicit_backup is not None:
        candidate = _safe_absolute(explicit_backup, label="settings backup")
        if candidate.parent != backup_root:
            raise SettingsRollbackError(
                "settings backup must be directly inside the backup directory"
            )
        match = pattern.fullmatch(candidate.name)
        if match is None:
            raise SettingsRollbackError("settings backup name is invalid")
        return candidate, match.group(1)

    try:
        if not backup_root.is_dir():
            raise SettingsRollbackError("settings backup directory is missing")
        candidates = sorted(
            (
                (candidate, match.group(1))
                for candidate in backup_root.iterdir()
                if (match := pattern.fullmatch(candidate.name)) is not None
            ),
            key=lambda item: item[0].name,
        )
    except OSError as error:
        raise SettingsRollbackError(
            "settings backup directory cannot be inspected"
        ) from error
    if not candidates:
        raise SettingsRollbackError("no pre-35 settings backup was found")
    if len(candidates) != 1:
        raise SettingsRollbackError(
            "multiple pre-35 settings backups require an explicit --backup"
        )
    candidate, filename_digest = candidates[0]
    return _safe_absolute(candidate, label="settings backup"), filename_digest


def _validate_legacy_backup(payload: bytes) -> None:
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SettingsRollbackError(
            "settings backup is not valid UTF-8 JSON"
        ) from error
    if not isinstance(document, dict):
        raise SettingsRollbackError("settings backup is not a JSON object")
    if "schema_version" in document:
        raise SettingsRollbackError(
            "settings backup is versioned and is not an unambiguous pre-35 file"
        )
    expected_types = {
        name: type(value) for name, value in asdict(Settings()).items()
    }
    invalid = tuple(
        name
        for name, expected_type in expected_types.items()
        if name in document and type(document[name]) is not expected_type
    )
    if invalid:
        raise SettingsRollbackError(
            "settings backup contains invalid known field types"
        )


def plan_settings_rollback(
    settings_path: Path,
    *,
    backup_path: Path | None = None,
) -> SettingsRollbackPlan:
    """Inspect a current settings file and one immutable pre-35 backup."""

    settings = _safe_absolute(settings_path, label="settings path")
    if settings.name != "settings.json":
        raise SettingsRollbackError(
            "settings path must identify the exact settings.json file"
        )
    backup, filename_digest = _select_backup(settings, backup_path)
    current_payload = _read_regular_file(settings, label="current settings")
    backup_payload = _read_regular_file(backup, label="settings backup")
    backup_digest = _digest(backup_payload)
    if filename_digest != backup_digest:
        raise SettingsRollbackError(
            "settings backup SHA-256 does not match its filename"
        )
    _validate_legacy_backup(backup_payload)
    return SettingsRollbackPlan(
        settings_path=settings,
        backup_path=backup,
        current_sha256=_digest(current_payload),
        backup_sha256=backup_digest,
        current_size=len(current_payload),
        backup_size=len(backup_payload),
    )


def _write_new_file(path: Path, payload: bytes, *, label: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    created = False
    try:
        descriptor = os.open(path, flags, 0o600)
        created = True
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if _read_regular_file(path, label=label) != payload:
            raise SettingsRollbackError(f"{label} verification failed")
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise


def apply_settings_rollback(
    settings_path: Path,
    *,
    expected_current_sha256: str,
    backup_path: Path | None = None,
    lock_timeout_seconds: float = SETTINGS_LOCK_TIMEOUT_SECONDS,
) -> SettingsRollbackResult:
    """Back up the current bytes and atomically restore a verified legacy file."""

    if _SHA256_PATTERN.fullmatch(expected_current_sha256) is None:
        raise SettingsRollbackError(
            "expected current SHA-256 must be 64 lowercase hexadecimal characters"
        )
    settings = _safe_absolute(settings_path, label="settings path")
    if settings.name != "settings.json":
        raise SettingsRollbackError(
            "settings path must identify the exact settings.json file"
        )
    try:
        with settings_file_lock(
            settings,
            timeout_seconds=lock_timeout_seconds,
        ):
            return _apply_settings_rollback_locked(
                settings,
                expected_current_sha256=expected_current_sha256,
                backup_path=backup_path,
            )
    except SettingsWriteBlockedError as error:
        raise SettingsRollbackError(
            f"settings write lock blocked the restore: {error}"
        ) from error


def _apply_settings_rollback_locked(
    settings_path: Path,
    *,
    expected_current_sha256: str,
    backup_path: Path | None,
) -> SettingsRollbackResult:
    """Perform the complete restore transaction while its writer lock is held."""

    plan = plan_settings_rollback(settings_path, backup_path=backup_path)
    if expected_current_sha256 != plan.current_sha256:
        raise SettingsRollbackError(
            "current settings SHA-256 differs from the confirmed dry-run"
        )
    if not plan.would_change:
        raise SettingsRollbackError("current settings already match the backup")

    current_payload = _read_regular_file(
        plan.settings_path, label="current settings"
    )
    backup_payload = _read_regular_file(
        plan.backup_path, label="settings backup"
    )
    if _digest(current_payload) != plan.current_sha256:
        raise SettingsRollbackError("current settings changed before backup")
    if _digest(backup_payload) != plan.backup_sha256:
        raise SettingsRollbackError("settings backup changed before restore")

    nonce = uuid.uuid4().hex
    owned_backup = plan.backup_path.parent / (
        f"{plan.settings_path.stem}.before-pre35-restore."
        f"{plan.current_sha256}.{nonce}.json"
    )
    _write_new_file(
        owned_backup,
        current_payload,
        label="owned current-settings backup",
    )

    temporary = plan.settings_path.with_name(
        f".{plan.settings_path.name}.pre35-restore.{nonce}.tmp"
    )
    try:
        _write_new_file(
            temporary,
            backup_payload,
            label="temporary restored settings",
        )
        if (
            _read_regular_file(plan.settings_path, label="current settings")
            != current_payload
        ):
            raise SettingsRollbackError(
                "current settings changed after its owned backup was created"
            )
        if (
            _read_regular_file(plan.backup_path, label="settings backup")
            != backup_payload
        ):
            raise SettingsRollbackError(
                "settings backup changed after restore preparation"
            )
        os.replace(temporary, plan.settings_path)
    finally:
        temporary.unlink(missing_ok=True)
    if (
        _read_regular_file(plan.settings_path, label="restored settings")
        != backup_payload
    ):
        raise SettingsRollbackError(
            "restored settings verification failed; retain the owned backup"
        )
    return SettingsRollbackResult(plan=plan, current_backup_path=owned_backup)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--settings",
        type=Path,
        required=True,
        help="Explicit settings.json path; no user path is selected implicitly.",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help=(
            "Exact settings.pre-35.<sha256>.json path when more than one "
            "verified backup exists."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply after a dry-run; still requires --expected-current-sha256.",
    )
    parser.add_argument(
        "--expected-current-sha256",
        help="Exact current SHA-256 reported by the immediately preceding dry-run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.apply:
            if args.expected_current_sha256 is None:
                raise SettingsRollbackError(
                    "--apply requires --expected-current-sha256 from a dry-run"
                )
            report = apply_settings_rollback(
                args.settings,
                expected_current_sha256=args.expected_current_sha256,
                backup_path=args.backup,
            ).public_report()
        else:
            if args.expected_current_sha256 is not None:
                raise SettingsRollbackError(
                    "--expected-current-sha256 is only valid with --apply"
                )
            report = plan_settings_rollback(
                args.settings, backup_path=args.backup
            ).public_report()
    except SettingsRollbackError as error:
        print(
            json.dumps(
                {"status": "BLOCKED", "error": str(error)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except OSError as error:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": f"filesystem operation failed: {type(error).__name__}",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
