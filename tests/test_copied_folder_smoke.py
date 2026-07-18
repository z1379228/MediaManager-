from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from tools import copied_folder_smoke
from tools.audit_versions import audit_version


def _write_release(
    root: Path, version: str, *, track: str | None = None
) -> Path:
    major, minor, _patch = version.split(".")
    release = root / f"{major}.{minor}"
    release.mkdir(parents=True)
    (release / "MediaManager.exe").write_bytes(f"exe-{version}".encode())
    wheel = release / f"mediamanager-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"mediamanager-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: mediamanager\nVersion: {version}\n",
        )
    info = {
        "schema_version": 1,
        "core_version": version,
        "version_folder": f"{major}.{minor}",
        "portable_tools": [],
    }
    if track is not None:
        info["release_track"] = track
    (release / "release-info.json").write_text(
        json.dumps(info), encoding="utf-8"
    )
    files = sorted(path for path in release.rglob("*") if path.is_file())
    (release / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(release).as_posix()}\n"
            for path in files
        ),
        encoding="ascii",
    )
    assert audit_version(release).valid
    return release


def _passing_runner(
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command, *, cwd, **options):
        calls.append((tuple(command), Path(cwd), options))
        assert options["shell"] is False
        assert options["check"] is False
        assert options["capture_output"] is True
        assert options["text"] is True
        assert options["timeout"] == 7
        assert Path(command[0]).parent == Path(cwd)
        assert Path(command[0]).name == "MediaManager.exe"
        environment = options["env"]
        assert Path(environment["LOCALAPPDATA"]).is_relative_to(Path(cwd))
        assert Path(environment["APPDATA"]).is_relative_to(Path(cwd))
        assert Path(environment["USERPROFILE"]).is_relative_to(Path(cwd))
        assert Path(environment["TEMP"]).is_relative_to(Path(cwd))
        sentinel = Path(cwd) / "UserData" / copied_folder_smoke._ROLLBACK_SENTINEL
        assert sentinel.is_file()
        assert len(sentinel.read_text(encoding="ascii")) == 64
        return subprocess.CompletedProcess(command, 0, "ok\n", "")

    return run


def _releases(tmp_path: Path) -> tuple[Path, Path, Path]:
    retained = tmp_path / "Version"
    development = retained / "Development"
    previous = _write_release(
        development, "1.0.0", track="Development"
    )
    current = _write_release(
        development, "2.0.0", track="Development"
    )
    return retained, current, previous


def test_full_smoke_uses_current_previous_current_and_preserves_sources(
    tmp_path: Path,
) -> None:
    retained, current, previous = _releases(tmp_path)
    before = {
        path.relative_to(retained): path.read_bytes()
        for path in retained.rglob("*")
        if path.is_file()
    }
    temp_root = tmp_path / "smoke"
    sibling = temp_root / "unrelated"
    sibling.mkdir(parents=True)
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=temp_root,
        timeout=7,
        runner=_passing_runner(calls),
        process_tree_safe=True,
    )

    assert report.copied_folder_smoke
    assert report.rollback
    assert report.source_unchanged
    assert report.attempt == ""
    assert report.errors == ()
    assert [phase.label for phase in report.versions] == [
        "current",
        "previous",
        "current",
    ]
    assert [command.name for phase in report.versions for command in phase.commands] == [
        "version",
        "verify-only",
        "headless-portable",
    ] * 3
    assert [call[0][1:] for call in calls] == [
        ("--version",),
        ("--portable", "--verify-only"),
        ("--headless", "--portable"),
    ] * 3
    assert "current" in calls[0][1].parts
    assert "previous" in calls[3][1].parts
    assert "current" in calls[6][1].parts
    assert all(
        Path(phase.portable_data_root).is_relative_to(Path(phase.copied_root))
        for phase in report.versions
    )
    assert sibling.is_dir()
    assert list(temp_root.glob("copied-folder-*")) == []
    after = {
        path.relative_to(retained): path.read_bytes()
        for path in retained.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize("kind", ["outside", "invalid-audit", "linklike"])
def test_invalid_or_escaping_version_root_is_rejected_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    retained, current, previous = _releases(tmp_path)
    if kind == "outside":
        current = _write_release(tmp_path / "outside", "3.0.0")
    elif kind == "invalid-audit":
        (current / "MediaManager.exe").write_bytes(b"tampered")
    else:
        original = copied_folder_smoke._is_linklike
        monkeypatch.setattr(
            copied_folder_smoke,
            "_is_linklike",
            lambda path: path == current or original(path),
        )
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        timeout=7,
        runner=_passing_runner(calls),
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert report.versions == ()
    assert calls == []
    assert not (tmp_path / "smoke").exists()


@pytest.mark.parametrize(
    "location",
    ["retained", "inside-retained", "contains-retained", "current", "previous"],
)
def test_temp_root_overlap_is_rejected_before_mkdir_even_with_keep_temp(
    tmp_path: Path,
    location: str,
) -> None:
    retained, current, previous = _releases(tmp_path)
    values = {
        "retained": retained,
        "inside-retained": retained / "new-smoke-root",
        "contains-retained": tmp_path,
        "current": current / "new-smoke-root",
        "previous": previous / "new-smoke-root",
    }
    temp_root = values[location]
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=temp_root,
        keep_temp=True,
        timeout=7,
        runner=_passing_runner(calls),
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert "overlaps" in " ".join(report.errors)
    assert calls == []
    assert not (retained / "new-smoke-root").exists()
    assert not (current / "new-smoke-root").exists()
    assert not (previous / "new-smoke-root").exists()
    assert not tuple(temp_root.glob("copied-folder-*"))


def test_cross_track_versions_are_rejected_before_attempt_creation(
    tmp_path: Path,
) -> None:
    retained, current, _previous = _releases(tmp_path)
    stable_previous = _write_release(
        retained / "Stable", "1.0.0", track="Stable"
    )
    temp_root = tmp_path / "smoke"

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        stable_previous,
        retained_root=retained,
        temp_root=temp_root,
        timeout=7,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert "same release track" in " ".join(report.errors)
    assert not temp_root.exists()


def test_previous_folder_must_be_strictly_earlier_than_current(
    tmp_path: Path,
) -> None:
    retained, later, earlier = _releases(tmp_path)
    temp_root = tmp_path / "smoke"

    report = copied_folder_smoke.run_copied_folder_smoke(
        earlier,
        later,
        retained_root=retained,
        temp_root=temp_root,
        timeout=7,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert "strictly earlier" in " ".join(report.errors)
    assert not temp_root.exists()


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_subprocess_failure_or_timeout_fails_closed_and_cleans_attempt(
    tmp_path: Path,
    failure: str,
) -> None:
    retained, current, previous = _releases(tmp_path)
    temp_root = tmp_path / "smoke"
    calls: list[tuple[str, ...]] = []

    def runner(command, **_options):
        calls.append(tuple(command))
        if len(calls) == 2 and failure == "timeout":
            raise subprocess.TimeoutExpired(command, 7)
        return subprocess.CompletedProcess(
            command,
            1 if len(calls) == 2 else 0,
            "",
            "failed" if len(calls) == 2 else "",
        )

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=temp_root,
        timeout=7,
        runner=runner,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert report.source_unchanged
    assert len(calls) == 2
    assert len(report.versions) == 1
    assert not report.versions[0].commands[-1].passed
    assert report.versions[0].commands[-1].timed_out is (failure == "timeout")
    assert list(temp_root.glob("copied-folder-*")) == []


def test_default_runner_capability_stops_after_verify_only(tmp_path: Path) -> None:
    retained, current, previous = _releases(tmp_path)
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        timeout=7,
        runner=_passing_runner(calls),
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert not report.process_tree_safe
    assert len(calls) == 2
    assert [status.name for status in report.versions[0].commands] == [
        "version",
        "verify-only",
        "headless-portable",
    ]
    assert "process tree" in report.versions[0].commands[-1].error


def test_contained_windows_runner_assigns_job_and_closes_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Job:
        def __init__(self, **limits) -> None:
            events.append(("job", limits))

        def assign(self, handle: int) -> None:
            events.append(("assign", handle))

        def close(self) -> None:
            events.append("close")

    class Process:
        _handle = 42
        returncode = 0

        def communicate(self, *, timeout: float):
            events.append(("communicate", timeout))
            return "stdout", "stderr"

    def popen(command, **options):
        events.append(("popen", tuple(command), options))
        return Process()

    monkeypatch.setattr(copied_folder_smoke, "ProviderJob", Job)
    monkeypatch.setattr(copied_folder_smoke.subprocess, "Popen", popen)
    monkeypatch.setattr(
        copied_folder_smoke,
        "_resume_suspended_process",
        lambda handle: events.append(("resume", handle)),
    )

    result = copied_folder_smoke.contained_windows_runner(
        ["MediaManager.exe", "--version"],
        cwd=tmp_path,
        shell=False,
        timeout=7,
        check=False,
        capture_output=True,
        text=True,
        env={"SYSTEMROOT": r"C:\Windows"},
    )

    assert result.returncode == 0
    assert result.stdout == "stdout"
    assert ("assign", 42) in events
    assert events.index(("assign", 42)) < events.index(("resume", 42))
    popen_event = next(event for event in events if event[0] == "popen")
    assert popen_event[2]["shell"] is False
    assert popen_event[2]["stdin"] is subprocess.DEVNULL
    assert popen_event[2]["stdout"] is subprocess.PIPE
    assert popen_event[2]["creationflags"] & copied_folder_smoke._CREATE_SUSPENDED
    assert events[-1] == "close"


def test_contained_windows_runner_timeout_closes_job_kills_and_reaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Job:
        def __init__(self, **_limits) -> None:
            pass

        def assign(self, handle: int) -> None:
            events.append(("assign", handle))

        def close(self) -> None:
            events.append("close")

    class Process:
        _handle = 43
        returncode = -1
        calls = 0

        def communicate(self, *, timeout: float):
            self.calls += 1
            events.append(("communicate", timeout))
            if self.calls == 1:
                raise subprocess.TimeoutExpired("MediaManager.exe", timeout)
            return "final", ""

        def poll(self):
            events.append("poll")
            return None

        def kill(self) -> None:
            events.append("kill")

    monkeypatch.setattr(copied_folder_smoke, "ProviderJob", Job)
    monkeypatch.setattr(copied_folder_smoke, "_resume_suspended_process", lambda _handle: None)
    monkeypatch.setattr(
        copied_folder_smoke.subprocess,
        "Popen",
        lambda *_args, **_options: Process(),
    )

    with pytest.raises(subprocess.TimeoutExpired) as raised:
        copied_folder_smoke.contained_windows_runner(
            ["MediaManager.exe", "--headless", "--portable"],
            cwd=tmp_path,
            shell=False,
            timeout=7,
            check=False,
            capture_output=True,
            text=True,
            env={"SYSTEMROOT": r"C:\Windows"},
        )

    assert raised.value.output == "final"
    assert events.index("close") < events.index("kill")
    assert events.count("close") >= 1
    assert ("communicate", 5) in events


def test_contained_windows_runner_assign_failure_terminates_direct_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Job:
        def __init__(self, **_limits) -> None:
            pass

        def assign(self, _handle: int) -> None:
            events.append("assign")
            raise RuntimeError("assignment failed")

        def close(self) -> None:
            events.append("close")

    class Process:
        _handle = 44
        returncode = -1

        def poll(self):
            events.append("poll")
            return None

        def kill(self) -> None:
            events.append("kill")

        def communicate(self, *, timeout: float):
            events.append(("communicate", timeout))
            return "", ""

    monkeypatch.setattr(copied_folder_smoke, "ProviderJob", Job)
    monkeypatch.setattr(copied_folder_smoke, "_resume_suspended_process", lambda _handle: None)
    monkeypatch.setattr(
        copied_folder_smoke.subprocess,
        "Popen",
        lambda *_args, **_options: Process(),
    )

    with pytest.raises(RuntimeError, match="assignment failed"):
        copied_folder_smoke.contained_windows_runner(
            ["MediaManager.exe", "--verify-only"],
            cwd=tmp_path,
            shell=False,
            timeout=7,
            check=False,
            capture_output=True,
            text=True,
            env={"SYSTEMROOT": r"C:\Windows"},
        )

    assert events.index("close") < events.index("kill")
    assert ("communicate", 5) in events


def test_contained_windows_runner_setup_attribute_error_kills_suspended_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Job:
        def __init__(self, **_limits) -> None:
            pass

        def assign(self, _handle: int) -> None:
            raise AssertionError("a missing handle must fail before assignment")

        def close(self) -> None:
            events.append("close")

    class Process:
        returncode = -1

        def poll(self):
            events.append("poll")
            return None

        def kill(self) -> None:
            events.append("kill")

        def communicate(self, *, timeout: float):
            events.append(("communicate", timeout))
            return "", ""

    monkeypatch.setattr(copied_folder_smoke, "ProviderJob", Job)
    monkeypatch.setattr(
        copied_folder_smoke.subprocess,
        "Popen",
        lambda *_args, **_options: Process(),
    )

    with pytest.raises(AttributeError):
        copied_folder_smoke.contained_windows_runner(
            ["MediaManager.exe", "--verify-only"],
            cwd=tmp_path,
            shell=False,
            timeout=7,
            check=False,
            capture_output=True,
            text=True,
            env={"SYSTEMROOT": r"C:\Windows"},
        )

    assert events.index("close") < events.index("kill")
    assert ("communicate", 5) in events


def test_cli_selects_process_tree_safe_contained_runner(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def smoke(*_args, **options):
        captured.update(options)
        return copied_folder_smoke.CopiedFolderSmokeReport(
            schema_version=1,
            copied_folder_smoke=True,
            rollback=True,
            source_unchanged=True,
            process_tree_safe=True,
            attempt="",
            kept_temp=False,
            errors=(),
            versions=(),
        )

    monkeypatch.setattr(copied_folder_smoke, "run_copied_folder_smoke", smoke)

    result = copied_folder_smoke.main(
        [
            "--current",
            "Version/Development/2.0",
            "--previous",
            "Version/Development/1.0",
        ]
    )

    assert result == 0
    assert captured["runner"] is copied_folder_smoke.contained_windows_runner
    assert captured["process_tree_safe"] is True
    assert json.loads(capsys.readouterr().out)["rollback"] is True


def test_keep_temp_preserves_only_the_current_owned_attempt(tmp_path: Path) -> None:
    retained, current, previous = _releases(tmp_path)
    temp_root = tmp_path / "smoke"
    sibling = temp_root / "older-attempt"
    sibling.mkdir(parents=True)
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=temp_root,
        keep_temp=True,
        timeout=7,
        runner=_passing_runner(calls),
        process_tree_safe=True,
    )

    attempt = Path(report.attempt)
    assert report.copied_folder_smoke
    assert report.rollback
    assert report.kept_temp
    assert attempt.parent == temp_root.resolve()
    assert tuple((attempt / "current").rglob("MediaManager.exe"))
    assert tuple((attempt / "previous").rglob("MediaManager.exe"))
    assert (attempt / copied_folder_smoke._OWNER_MARKER).is_file()
    current_data = Path(report.versions[-1].portable_data_root)
    previous_data = Path(report.versions[1].portable_data_root)
    assert current_data.is_dir()
    assert not previous_data.exists()
    assert (
        current_data / copied_folder_smoke._ROLLBACK_SENTINEL
    ).read_text(encoding="ascii") == (
        attempt / copied_folder_smoke._OWNER_MARKER
    ).read_text(encoding="ascii")
    assert sibling.is_dir()


def test_rollback_phases_share_one_portable_data_tree(tmp_path: Path) -> None:
    retained, current, previous = _releases(tmp_path)
    headless_labels: list[str] = []
    sentinel_values: list[str] = []

    def runner(command, *, cwd, **_options):
        data = Path(cwd) / "UserData"
        sentinel = data / copied_folder_smoke._ROLLBACK_SENTINEL
        sentinel_values.append(sentinel.read_text(encoding="ascii"))
        if command[1:] == ["--headless", "--portable"]:
            state = data / "rollback-state.txt"
            if not headless_labels:
                assert "current" in Path(cwd).parts
                assert not state.exists()
                state.write_text("current", encoding="ascii")
                headless_labels.append("current")
            elif len(headless_labels) == 1:
                assert "previous" in Path(cwd).parts
                assert state.read_text(encoding="ascii") == "current"
                state.write_text("current>previous", encoding="ascii")
                headless_labels.append("previous")
            else:
                assert "current" in Path(cwd).parts
                assert state.read_text(encoding="ascii") == "current>previous"
                headless_labels.append("current")
        return subprocess.CompletedProcess(command, 0, "", "")

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        keep_temp=True,
        timeout=7,
        runner=runner,
        process_tree_safe=True,
    )

    assert report.copied_folder_smoke
    assert report.rollback
    assert headless_labels == ["current", "previous", "current"]
    assert len(set(sentinel_values)) == 1
    current_data = Path(report.versions[-1].portable_data_root)
    previous_data = Path(report.versions[1].portable_data_root)
    assert (current_data / "rollback-state.txt").read_text(encoding="ascii") == (
        "current>previous"
    )
    assert not previous_data.exists()


def test_previous_phase_failure_recovers_shared_data_to_current(
    tmp_path: Path,
) -> None:
    retained, current, previous = _releases(tmp_path)
    calls = 0

    def runner(command, **_options):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 1 if calls == 6 else 0, "", "")

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        keep_temp=True,
        timeout=7,
        runner=runner,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    current_data = Path(report.versions[0].portable_data_root)
    previous_data = Path(report.versions[1].portable_data_root)
    assert current_data.is_dir()
    assert not previous_data.exists()
    assert (current_data / copied_folder_smoke._ROLLBACK_SENTINEL).is_file()


def test_sentinel_tampering_fails_and_best_effort_moves_data_back(
    tmp_path: Path,
) -> None:
    retained, current, previous = _releases(tmp_path)
    calls = 0

    def runner(command, *, cwd, **_options):
        nonlocal calls
        calls += 1
        if calls == 6:
            sentinel = Path(cwd) / "UserData" / copied_folder_smoke._ROLLBACK_SENTINEL
            sentinel.write_text("tampered", encoding="ascii")
        return subprocess.CompletedProcess(command, 0, "", "")

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        keep_temp=True,
        timeout=7,
        runner=runner,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert "sentinel" in " ".join(report.errors)
    current_data = Path(report.versions[0].portable_data_root)
    previous_data = Path(report.versions[1].portable_data_root)
    assert current_data.is_dir()
    assert not previous_data.exists()
    assert (
        current_data / copied_folder_smoke._ROLLBACK_SENTINEL
    ).read_text(encoding="ascii") == "tampered"


def test_cleanup_failure_cannot_be_reported_as_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retained, current, previous = _releases(tmp_path)
    calls: list[tuple[tuple[str, ...], Path, dict[str, object]]] = []
    monkeypatch.setattr(
        copied_folder_smoke,
        "remove_owned_attempt",
        lambda _attempt: (_ for _ in ()).throw(RuntimeError("locked")),
    )

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        timeout=7,
        runner=_passing_runner(calls),
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert "cleanup failed" in " ".join(report.errors)
    assert Path(report.attempt).is_dir()


def test_retained_source_mutation_is_detected(tmp_path: Path) -> None:
    retained, current, previous = _releases(tmp_path)
    calls = 0

    def runner(command, **_options):
        nonlocal calls
        calls += 1
        if calls == 3:
            (current / "MediaManager.exe").write_bytes(b"changed")
        return subprocess.CompletedProcess(command, 0, "", "")

    report = copied_folder_smoke.run_copied_folder_smoke(
        current,
        previous,
        retained_root=retained,
        temp_root=tmp_path / "smoke",
        timeout=7,
        runner=runner,
        process_tree_safe=True,
    )

    assert not report.copied_folder_smoke
    assert not report.rollback
    assert not report.source_unchanged
    assert "retained source changed" in " ".join(report.errors)


def test_default_temp_root_uses_local_app_data() -> None:
    assert copied_folder_smoke.default_temp_root(
        {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"}, platform="nt"
    ) == Path(r"C:\Users\tester\AppData\Local\MediaManager-SmokeRuns")


def test_windows_default_temp_root_requires_local_app_data() -> None:
    with pytest.raises(RuntimeError, match="--temp-root"):
        copied_folder_smoke.default_temp_root({}, platform="nt")
