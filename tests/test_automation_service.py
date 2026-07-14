from __future__ import annotations

from pathlib import Path

import pytest

from core.automation import AutomationService


def service(tmp_path: Path, dispatcher, *, name: str = "automation.sqlite3"):
    return AutomationService(tmp_path / name, dispatcher, poll_seconds=3600)


def test_mod_and_new_rules_are_disabled_by_default(tmp_path: Path) -> None:
    dispatched = []
    automation = service(tmp_path, lambda rule, candidate: dispatched.append(candidate) or "task")
    try:
        rule_id = automation.create_rule(
            name="Daily", kind="schedule", source="https://example.com/list"
        )
        assert not automation.is_enabled
        assert not automation.list_rules()[0].enabled
        assert automation.run_once(now=1000) == 0
        assert dispatched == []
        assert automation._thread is None
        assert rule_id
    finally:
        automation.close()


def test_schedule_is_bounded_and_duplicate_slots_are_deterministic(tmp_path: Path) -> None:
    dispatched = []
    automation = service(tmp_path, lambda rule, candidate: dispatched.append(candidate) or candidate.candidate_key)
    try:
        rule_id = automation.create_rule(
            name="Playlist", kind="schedule", source="https://example.com/list",
            interval_minutes=1, rate_limit=2,
        )
        automation.set_rule_enabled(rule_id, True, now=0)
        automation.set_enabled(True)
        assert automation.run_once(now=300) == 2
        assert len(dispatched) == 2
        assert automation.run_once(now=300) == 0
        assert len({item.candidate_key for item in automation.list_candidates()}) == 2
        assert automation.list_rules()[0].next_run == 360
    finally:
        automation.close()


def test_watch_folder_uses_path_size_and_mtime_identity(tmp_path: Path) -> None:
    watched = tmp_path / "watched"
    watched.mkdir()
    media = watched / "song.mp3"
    media.write_bytes(b"one")
    dispatched = []
    automation = service(tmp_path, lambda rule, candidate: dispatched.append(candidate.source) or "convert")
    try:
        rule_id = automation.create_rule(
            name="Watch", kind="watch-folder", source=str(watched),
            preset={"action": "media-convert", "output_dir": str(tmp_path)},
            interval_minutes=1,
        )
        automation.set_rule_enabled(rule_id, True, now=1000)
        automation.set_enabled(True)
        assert automation.run_once(now=1000) == 1
        assert automation.run_once(now=1060) == 0
        media.write_bytes(b"changed-size")
        assert automation.run_once(now=1120) == 1
        assert dispatched == [str(media.resolve()), str(media.resolve())]
    finally:
        automation.close()


def test_clipboard_accepts_only_https_and_deduplicates(tmp_path: Path) -> None:
    dispatched = []
    automation = service(tmp_path, lambda rule, candidate: dispatched.append(candidate.source) or "download")
    try:
        rule_id = automation.create_rule(name="Clipboard", kind="clipboard")
        automation.set_rule_enabled(rule_id, True, now=1000)
        automation.set_enabled(True)
        assert automation.observe_clipboard("http://example.com/video", now=1000) == 0
        assert automation.observe_clipboard("https://Example.com/video", now=1000) == 1
        assert automation.observe_clipboard("https://example.com/video", now=1001) == 0
        assert automation.run_once(now=1001) == 1
        assert dispatched == ["https://example.com/video"]
    finally:
        automation.close()


def test_failed_candidate_is_visible_and_requires_explicit_retry(tmp_path: Path) -> None:
    failures = {"count": 0}

    def dispatcher(_rule, _candidate):
        failures["count"] += 1
        if failures["count"] == 1:
            raise RuntimeError("temporary failure")
        return "recovered"

    automation = service(tmp_path, dispatcher)
    try:
        rule_id = automation.create_rule(name="Clipboard", kind="clipboard")
        automation.set_rule_enabled(rule_id, True, now=1000)
        automation.set_enabled(True)
        automation.observe_clipboard("https://example.com/video", now=1000)
        assert automation.run_once(now=1000) == 0
        candidate = automation.list_candidates()[0]
        assert candidate.state == "FAILED"
        assert candidate.error == "temporary failure"
        automation.retry_candidate(candidate.candidate_key)
        assert automation.run_once(now=1001) == 1
        assert automation.list_candidates()[0].state == "DISPATCHED"
    finally:
        automation.close()


def test_interrupted_claim_recovers_to_pending_without_duplicate_row(tmp_path: Path) -> None:
    database_name = "recovery.sqlite3"
    first = service(tmp_path, lambda _rule, _candidate: "unused", name=database_name)
    rule_id = first.create_rule(name="Clipboard", kind="clipboard")
    first.set_rule_enabled(rule_id, True, now=1000)
    first.set_enabled(True)
    first.observe_clipboard("https://example.com/video", now=1000)
    with first._connection:
        first._connection.execute("UPDATE candidates SET state='CLAIMED'")
    first.close()

    dispatched = []
    second = service(tmp_path, lambda _rule, candidate: dispatched.append(candidate.candidate_key) or "task", name=database_name)
    try:
        assert second.list_candidates()[0].state == "PENDING"
        second.set_enabled(True)
        assert second.run_once(now=1001) == 1
        assert len(dispatched) == 1
        assert len(second.list_candidates()) == 1
    finally:
        second.close()


@pytest.mark.parametrize("window", ("24:00", "12:60", "bad"))
def test_invalid_run_window_is_rejected(tmp_path: Path, window: str) -> None:
    automation = service(tmp_path, lambda _rule, _candidate: "task")
    try:
        with pytest.raises(ValueError, match="HH:MM"):
            automation.create_rule(
                name="Bad", kind="clipboard", window_start=window
            )
    finally:
        automation.close()
