"""SQLite-backed plugin registry and pending-action journal."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PendingAction(StrEnum):
    NONE = "NONE"
    INSTALL = "INSTALL"
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"
    ROLLBACK = "ROLLBACK"
    PURGE = "PURGE"


_LIFECYCLE_ACTIONS = frozenset(
    {PendingAction.ENABLE, PendingAction.DISABLE}
)


@dataclass(frozen=True, slots=True)
class PluginRecord:
    plugin_id: str
    installed_version: str
    enabled: bool
    pending_action: PendingAction
    trust_level: str
    publisher_id: str
    approved_permissions: tuple[str, ...]
    manifest_hash: str
    failure_count: int = 0
    quarantine_reason: str | None = None


class PluginRegistry:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self._connection.execute("""CREATE TABLE IF NOT EXISTS plugins (
            plugin_id TEXT PRIMARY KEY, installed_version TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
            pending_action TEXT NOT NULL DEFAULT 'NONE', trust_level TEXT NOT NULL, publisher_id TEXT NOT NULL,
            approved_permissions TEXT NOT NULL DEFAULT '[]', manifest_hash TEXT NOT NULL,
            last_verified_at TEXT, last_started_at TEXT, failure_count INTEGER NOT NULL DEFAULT 0,
            quarantine_reason TEXT, CHECK(enabled IN (0,1)))""")
        self._connection.commit()

    def upsert(self, record: PluginRecord) -> None:
        try:
            self._connection.execute(
                """INSERT INTO plugins
                (plugin_id,installed_version,enabled,pending_action,trust_level,publisher_id,approved_permissions,manifest_hash,failure_count,quarantine_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(plugin_id) DO UPDATE SET
                installed_version=excluded.installed_version, enabled=excluded.enabled, pending_action=excluded.pending_action,
                trust_level=excluded.trust_level, publisher_id=excluded.publisher_id,
                approved_permissions=excluded.approved_permissions, manifest_hash=excluded.manifest_hash,
                failure_count=excluded.failure_count, quarantine_reason=excluded.quarantine_reason""",
                (
                    record.plugin_id,
                    record.installed_version,
                    record.enabled,
                    record.pending_action,
                    record.trust_level,
                    record.publisher_id,
                    json.dumps(record.approved_permissions),
                    record.manifest_hash,
                    record.failure_count,
                    record.quarantine_reason,
                ),
            )
            self._connection.commit()
        except sqlite3.Error:
            self._connection.rollback()
            raise

    def get(self, plugin_id: str) -> PluginRecord | None:
        row = self._connection.execute(
            "SELECT * FROM plugins WHERE plugin_id=?", (plugin_id,)
        ).fetchone()
        return self._record(row) if row else None

    def list_all(self) -> tuple[PluginRecord, ...]:
        rows = self._connection.execute("SELECT * FROM plugins ORDER BY plugin_id")
        return tuple(self._record(row) for row in rows)

    def list_dependency_records(self, *, limit: int) -> tuple[PluginRecord, ...]:
        """Return a bounded dependency-graph view without removal tombstones."""

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("dependency record limit must be a positive integer")
        rows = self._connection.execute(
            """SELECT * FROM plugins
            WHERE pending_action NOT IN (?, ?)
            ORDER BY plugin_id LIMIT ?""",
            (PendingAction.REMOVE, PendingAction.PURGE, limit),
        )
        return tuple(self._record(row) for row in rows)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        self._required_update(
            "UPDATE plugins SET enabled=? WHERE plugin_id=?",
            (int(enabled), plugin_id),
            plugin_id,
        )

    def claim_lifecycle(
        self,
        expected: PluginRecord,
        action: PendingAction,
    ) -> bool:
        """Atomically claim one NONE journal without accepting stale identity."""

        self._validate_lifecycle_action(action)
        if expected.pending_action is not PendingAction.NONE:
            return False
        return self._conditional_update(
            """UPDATE plugins SET pending_action=?
            WHERE plugin_id=? AND installed_version=? AND manifest_hash=?
            AND enabled=? AND pending_action=?""",
            (
                action,
                expected.plugin_id,
                expected.installed_version,
                expected.manifest_hash,
                int(expected.enabled),
                PendingAction.NONE,
            ),
        )

    def finish_lifecycle(
        self,
        expected: PluginRecord,
        action: PendingAction,
        *,
        enabled: bool,
    ) -> bool:
        """Finalize the exact journal while its caller holds the lifecycle lock."""

        self._validate_lifecycle_action(action)
        return self._conditional_update(
            """UPDATE plugins SET enabled=?, pending_action=?
            WHERE plugin_id=? AND installed_version=? AND manifest_hash=?
            AND enabled=? AND pending_action=?""",
            (
                int(enabled),
                PendingAction.NONE,
                expected.plugin_id,
                expected.installed_version,
                expected.manifest_hash,
                int(expected.enabled),
                action,
            ),
        )

    def list_enabled(self) -> tuple[PluginRecord, ...]:
        return tuple(
            self._record(row)
            for row in self._connection.execute(
                "SELECT * FROM plugins WHERE enabled=1 AND pending_action='NONE'"
            )
        )

    def set_pending(self, plugin_id: str, action: PendingAction) -> None:
        self._required_update(
            "UPDATE plugins SET pending_action=? WHERE plugin_id=?",
            (action, plugin_id),
            plugin_id,
        )

    def delete(self, plugin_id: str) -> None:
        self._required_update(
            "DELETE FROM plugins WHERE plugin_id=?",
            (plugin_id,),
            plugin_id,
        )

    def close(self) -> None:
        self._connection.close()

    def _conditional_update(
        self,
        statement: str,
        parameters: tuple[object, ...],
    ) -> bool:
        try:
            cursor = self._connection.execute(statement, parameters)
            updated = cursor.rowcount == 1
            self._connection.commit()
            return updated
        except sqlite3.Error:
            self._connection.rollback()
            raise

    def _required_update(
        self,
        statement: str,
        parameters: tuple[object, ...],
        plugin_id: str,
    ) -> None:
        try:
            cursor = self._connection.execute(statement, parameters)
            if cursor.rowcount != 1:
                raise KeyError(plugin_id)
            self._connection.commit()
        except (KeyError, sqlite3.Error):
            self._connection.rollback()
            raise

    @staticmethod
    def _validate_lifecycle_action(action: PendingAction) -> None:
        if action not in _LIFECYCLE_ACTIONS:
            raise ValueError("lifecycle action must be ENABLE or DISABLE")

    @staticmethod
    def _record(row: sqlite3.Row) -> PluginRecord:
        return PluginRecord(
            row["plugin_id"],
            row["installed_version"],
            bool(row["enabled"]),
            PendingAction(row["pending_action"]),
            row["trust_level"],
            row["publisher_id"],
            tuple(json.loads(row["approved_permissions"])),
            row["manifest_hash"],
            row["failure_count"],
            row["quarantine_reason"],
        )
