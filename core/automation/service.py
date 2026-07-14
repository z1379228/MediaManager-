"""Bounded scheduler/watch/clipboard engine with a crash-recovery ledger."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from threading import Event, RLock, Thread
import time
from urllib.parse import urlsplit, urlunsplit
import uuid

from core.automation.models import AutomationCandidate, AutomationRule

KINDS = frozenset({"schedule", "watch-folder", "clipboard"})
MAX_RULES = 200
MAX_RATE = 100
MAX_WATCH_FILES = 10_000
PRESET_KEYS = frozenset(
    {
        "action", "playlist", "output_dir", "format_preset", "recursive",
        "conversion_preset", "model_id", "formats", "language",
    }
)


class AutomationDuplicate(RuntimeError):
    """A candidate is already present in the target queue/archive."""


class AutomationService:
    provider_id = "automation"
    display_name = "Automation"
    available = True

    def __init__(
        self,
        database: Path,
        dispatcher: Callable[[AutomationRule, AutomationCandidate], str],
        *,
        poll_seconds: float = 5.0,
    ) -> None:
        self.database = database.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.dispatcher = dispatcher
        self.poll_seconds = max(1.0, float(poll_seconds))
        self._lock = RLock()
        self._connection = sqlite3.connect(self.database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._enabled = False
        self._closed = False
        self._stop = Event()
        self._thread: Thread | None = None
        self._create_schema()

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    preset_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    interval_seconds INTEGER NOT NULL,
                    window_start INTEGER NOT NULL,
                    window_end INTEGER NOT NULL,
                    rate_limit INTEGER NOT NULL,
                    next_run REAL,
                    last_run REAL,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_key TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL REFERENCES rules(rule_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    discovered_at REAL NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    dispatch_token TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_candidates_dispatch
                ON candidates(rule_id, state, updated_at);
                """
            )
            self._connection.execute(
                "UPDATE candidates SET state='PENDING',error='recovered interrupted dispatch' "
                "WHERE state='CLAIMED'"
            )

    def set_enabled(self, enabled: bool) -> int:
        thread = None
        with self._lock:
            if self._closed:
                raise RuntimeError("automation service is closed")
            self._enabled = enabled
            if enabled and (self._thread is None or not self._thread.is_alive()):
                self._stop.clear()
                self._thread = Thread(target=self._monitor, name="automation", daemon=True)
                self._thread.start()
            elif not enabled:
                self._stop.set()
                thread = self._thread
                self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=3)
        return 0

    def close(self) -> None:
        if self._closed:
            return
        self.set_enabled(False)
        with self._lock:
            self._closed = True
            self._connection.close()

    def create_rule(
        self,
        *,
        name: str,
        kind: str,
        source: str = "",
        preset: Mapping[str, object] | None = None,
        interval_minutes: int = 60,
        window_start: str = "00:00",
        window_end: str = "23:59",
        rate_limit: int = 10,
    ) -> str:
        if len(self.list_rules()) >= MAX_RULES:
            raise ValueError("automation rule limit reached")
        name = name.strip()
        kind = kind.strip().casefold()
        if not name or len(name) > 120 or any(ord(char) < 32 for char in name):
            raise ValueError("automation rule name is invalid")
        if kind not in KINDS:
            raise ValueError("automation rule kind is invalid")
        normalized_source = self._source(kind, source)
        normalized_preset = self._preset(kind, preset or {})
        if not isinstance(interval_minutes, int) or not 1 <= interval_minutes <= 43_200:
            raise ValueError("automation interval must be 1 to 43200 minutes")
        if not isinstance(rate_limit, int) or not 1 <= rate_limit <= MAX_RATE:
            raise ValueError("automation rate limit must be 1 to 100")
        start = self._minute(window_start)
        end = self._minute(window_end)
        rule_id = uuid.uuid4().hex
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO rules(rule_id,name,kind,source,preset_json,enabled,"
                "interval_seconds,window_start,window_end,rate_limit,next_run) "
                "VALUES(?,?,?,?,?,0,?,?,?,?,NULL)",
                (
                    rule_id, name, kind, normalized_source,
                    json.dumps(normalized_preset, ensure_ascii=False, sort_keys=True),
                    interval_minutes * 60, start, end, rate_limit,
                ),
            )
        return rule_id

    def set_rule_enabled(self, rule_id: str, enabled: bool, *, now: float | None = None) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE rules SET enabled=?,next_run=?,last_error='' WHERE rule_id=?",
                (int(enabled), (now if now is not None else time.time()) if enabled else None, rule_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(rule_id)

    def remove_rule(self, rule_id: str) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute("DELETE FROM rules WHERE rule_id=?", (rule_id,))
            if cursor.rowcount != 1:
                raise KeyError(rule_id)

    def list_rules(self) -> tuple[AutomationRule, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM rules ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return tuple(self._row_rule(row) for row in rows)

    def list_candidates(self, *, limit: int = 500) -> tuple[AutomationCandidate, ...]:
        limit = max(1, min(500, int(limit)))
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM candidates ORDER BY discovered_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return tuple(self._row_candidate(row) for row in rows)

    def observe_clipboard(self, value: str, *, now: float | None = None) -> int:
        if not self.is_enabled:
            return 0
        try:
            source = self._https_url(value)
        except ValueError:
            return 0
        now = time.time() if now is None else now
        inserted = 0
        for rule in self.list_rules():
            if rule.kind != "clipboard" or not rule.enabled or not self._in_window(rule, now):
                continue
            key = self._key(rule.rule_id, source)
            inserted += self._insert_candidate(key, rule.rule_id, source, now)
        return inserted

    def run_once(self, *, now: float | None = None) -> int:
        if not self.is_enabled:
            return 0
        now = time.time() if now is None else float(now)
        dispatched = 0
        for rule in self.list_rules():
            if not rule.enabled or not self._in_window(rule, now):
                continue
            if rule.kind == "schedule" and rule.next_run is not None and rule.next_run <= now:
                due = rule.next_run
                created = 0
                while due <= now and created < rule.rate_limit:
                    created += self._insert_candidate(
                        self._key(rule.rule_id, str(int(due))), rule.rule_id, rule.source, due
                    )
                    due += rule.interval_seconds
                if due <= now:
                    due = now + rule.interval_seconds
                self._set_next(rule.rule_id, due, now)
            elif rule.kind == "watch-folder" and rule.next_run is not None and rule.next_run <= now:
                self._discover_folder(rule, now)
                self._set_next(rule.rule_id, now + rule.interval_seconds, now)
            dispatched += self._dispatch_pending(rule, now)
        return dispatched

    def retry_candidate(self, candidate_key: str) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE candidates SET state='PENDING',error='',updated_at=? "
                "WHERE candidate_key=? AND state='FAILED'",
                (time.time(), candidate_key),
            )
            if cursor.rowcount != 1:
                raise KeyError(candidate_key)

    def _monitor(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self.run_once()
            except Exception:
                continue

    def _discover_folder(self, rule: AutomationRule, now: float) -> None:
        root = Path(rule.source)
        if root.is_symlink() or not root.is_dir():
            self._rule_error(rule.rule_id, "watch folder is unavailable")
            return
        recursive = bool(rule.preset.get("recursive", False))
        iterator = root.rglob("*") if recursive else root.iterdir()
        count = 0
        examined = 0
        for path in iterator:
            examined += 1
            if examined > min(MAX_WATCH_FILES, rule.rate_limit * 20):
                break
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            source = str(path.resolve())
            identity = f"{os.path.normcase(source)}|{stat.st_size}|{stat.st_mtime_ns}"
            count += self._insert_candidate(
                self._key(rule.rule_id, identity), rule.rule_id, source, now
            )

    def _dispatch_pending(self, rule: AutomationRule, now: float) -> int:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM candidates WHERE rule_id=? AND state='PENDING' "
                "ORDER BY discovered_at,candidate_key LIMIT ?",
                (rule.rule_id, rule.rate_limit),
            ).fetchall()
        dispatched = 0
        for row in rows:
            candidate = self._row_candidate(row)
            with self._lock, self._connection:
                cursor = self._connection.execute(
                    "UPDATE candidates SET state='CLAIMED',attempts=attempts+1,updated_at=? "
                    "WHERE candidate_key=? AND state='PENDING'",
                    (now, candidate.candidate_key),
                )
            if cursor.rowcount != 1:
                continue
            try:
                token = self.dispatcher(rule, candidate)
            except AutomationDuplicate as error:
                state, token, error_text = "SKIPPED", "", str(error)
            except Exception as error:
                state, token, error_text = "FAILED", "", str(error)[:500]
                self._rule_error(rule.rule_id, error_text)
            else:
                state, error_text = "DISPATCHED", ""
                dispatched += 1
            with self._lock, self._connection:
                self._connection.execute(
                    "UPDATE candidates SET state=?,dispatch_token=?,error=?,updated_at=? "
                    "WHERE candidate_key=?",
                    (state, str(token)[:500], error_text, now, candidate.candidate_key),
                )
        return dispatched

    def _insert_candidate(self, key: str, rule_id: str, source: str, now: float) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "INSERT OR IGNORE INTO candidates(candidate_key,rule_id,source,discovered_at,state,updated_at) "
                "VALUES(?,?,?,?,'PENDING',?)",
                (key, rule_id, source, now, now),
            )
        return int(cursor.rowcount == 1)

    def _set_next(self, rule_id: str, next_run: float, last_run: float) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE rules SET next_run=?,last_run=? WHERE rule_id=?",
                (next_run, last_run, rule_id),
            )

    def _rule_error(self, rule_id: str, error: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE rules SET last_error=? WHERE rule_id=?", (error[:500], rule_id)
            )

    @staticmethod
    def _source(kind: str, source: str) -> str:
        if kind == "clipboard":
            return ""
        if kind == "schedule":
            return AutomationService._https_url(source)
        path = Path(source).expanduser().resolve()
        if path.is_symlink() or not path.is_dir():
            raise ValueError("watch source must be an existing regular folder")
        return str(path)

    @staticmethod
    def _preset(kind: str, value: Mapping[str, object]) -> dict[str, object]:
        if not set(value).issubset(PRESET_KEYS):
            raise ValueError("automation preset contains unsupported fields")
        preset = dict(value)
        action = str(preset.get("action", "download" if kind != "watch-folder" else "media-convert"))
        allowed = {"download"} if kind in {"schedule", "clipboard"} else {"media-convert", "speech-to-text"}
        if action not in allowed:
            raise ValueError("automation action does not match the rule kind")
        preset["action"] = action
        if "output_dir" in preset:
            output = Path(str(preset["output_dir"])).expanduser().resolve()
            if output.is_symlink() or not output.is_dir():
                raise ValueError("automation output folder is invalid")
            preset["output_dir"] = str(output)
        return preset

    @staticmethod
    def _https_url(value: str) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise ValueError("automation URL must be a plain HTTPS URL")
        return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", parts.query, ""))

    @staticmethod
    def _minute(value: str) -> int:
        try:
            hour_text, minute_text = value.split(":", 1)
            hour, minute = int(hour_text), int(minute_text)
        except (AttributeError, ValueError) as error:
            raise ValueError("run window must use HH:MM") from error
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("run window must use HH:MM")
        return hour * 60 + minute

    @staticmethod
    def _in_window(rule: AutomationRule, now: float) -> bool:
        local = time.localtime(now)
        minute = local.tm_hour * 60 + local.tm_min
        if rule.window_start <= rule.window_end:
            return rule.window_start <= minute <= rule.window_end
        return minute >= rule.window_start or minute <= rule.window_end

    @staticmethod
    def _key(rule_id: str, identity: str) -> str:
        return hashlib.sha256(f"{rule_id}\0{identity}".encode("utf-8")).hexdigest()

    @staticmethod
    def _row_rule(row: sqlite3.Row) -> AutomationRule:
        preset = json.loads(row["preset_json"])
        return AutomationRule(
            row["rule_id"], row["name"], row["kind"], row["source"], preset,
            bool(row["enabled"]), int(row["interval_seconds"]),
            int(row["window_start"]), int(row["window_end"]), int(row["rate_limit"]),
            float(row["next_run"]) if row["next_run"] is not None else None,
            float(row["last_run"]) if row["last_run"] is not None else None,
            row["last_error"],
        )

    @staticmethod
    def _row_candidate(row: sqlite3.Row) -> AutomationCandidate:
        return AutomationCandidate(
            row["candidate_key"], row["rule_id"], row["source"],
            float(row["discovered_at"]), row["state"], int(row["attempts"]),
            row["dispatch_token"], row["error"],
        )
