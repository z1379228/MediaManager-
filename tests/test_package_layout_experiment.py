from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

import pytest

from tools import package_layout_experiment
from tools.build_version import (
    PYINSTALLER_CONSOLE_ENVIRONMENT,
    PYINSTALLER_PATH_ENVIRONMENT,
)


def test_package_layout_paths_are_explicit_and_distinct(tmp_path: Path) -> None:
    onefile_root, onefile_executable = package_layout_experiment.artifact_paths(
        tmp_path,
        "onefile",
    )
    onedir_root, onedir_executable = package_layout_experiment.artifact_paths(
        tmp_path,
        "onedir",
    )

    assert onefile_root == tmp_path / "dist"
    assert onefile_executable == tmp_path / "dist" / "MediaManager.exe"
    assert onedir_root == tmp_path / "dist" / "MediaManager"
    assert onedir_executable == onedir_root / "MediaManager.exe"
    with pytest.raises(ValueError, match="onefile or onedir"):
        package_layout_experiment.artifact_paths(tmp_path, "unknown")


def test_snapshot_identity_detects_copied_tree_changes(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    (root / "_internal").mkdir(parents=True)
    (root / "MediaManager.exe").write_bytes(b"exe")
    payload = root / "_internal" / "payload.bin"
    payload.write_bytes(b"payload")

    before = package_layout_experiment.snapshot_tree(root)
    identity = package_layout_experiment.artifact_identity(before)
    payload.write_bytes(b"changed")
    after = package_layout_experiment.snapshot_tree(root)

    assert identity.files == 2
    assert identity.bytes == len(b"exe") + len(b"payload")
    assert before != after
    assert package_layout_experiment.artifact_identity(after) != identity


def test_runtime_materialization_allows_only_pinned_builtin_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "MediaManager.exe").write_bytes(b"exe")
    before = package_layout_experiment.snapshot_tree(root)
    provider = root / "mod" / "builtin" / "demo" / "provider.py"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(b"provider")
    digest = hashlib.sha256(b"provider").hexdigest()

    result = package_layout_experiment.validate_runtime_materialization(
        before,
        package_layout_experiment.snapshot_tree(root),
        {"demo": {"provider.py": digest}},
    )

    assert result == {
        "passed": True,
        "added_files": 1,
        "added_bytes": len(b"provider"),
    }

    (root / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unexpected artifact files"):
        package_layout_experiment.validate_runtime_materialization(
            before,
            package_layout_experiment.snapshot_tree(root),
            {"demo": {"provider.py": digest}},
        )


def test_experiment_builds_both_layouts_and_verifies_copy(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "MediaManager.spec").write_text("spec", encoding="utf-8")
    builder = tmp_path / "runtime" / "pyinstaller.exe"
    builder.parent.mkdir()
    builder.write_bytes(b"builder")
    observed_layouts: list[str] = []

    def fake_build(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        layout = environment[package_layout_experiment.PYINSTALLER_LAYOUT_ENVIRONMENT]
        assert (
            environment[PYINSTALLER_PATH_ENVIRONMENT]
            == environment["PATH"]
        )
        assert (
            environment[PYINSTALLER_CONSOLE_ENVIRONMENT]
            == "0"
        )
        observed_layouts.append(layout)
        dist = Path(command[command.index("--distpath") + 1])
        if layout == "onefile":
            dist.mkdir(parents=True)
            (dist / "MediaManager.exe").write_bytes(b"onefile")
        else:
            artifact = dist / "MediaManager"
            (artifact / "_internal").mkdir(parents=True)
            (artifact / "MediaManager.exe").write_bytes(b"onedir")
            (artifact / "_internal" / "runtime.bin").write_bytes(b"runtime")
        return subprocess.CompletedProcess(command, 0)

    def fake_sample(
        command: tuple[str, ...],
        **kwargs: object,
    ) -> dict[str, object]:
        if "--verify-only" in command:
            artifact = Path(str(kwargs["cwd"]))
            source_root = (
                Path(package_layout_experiment.__file__).parents[1]
                / "mod"
                / "builtin"
            )
            for provider_id, files in (
                package_layout_experiment.BUILTIN_PROVIDER_HASHES.items()
            ):
                for relative in files:
                    source = source_root / provider_id / relative
                    target = artifact / "mod" / "builtin" / provider_id / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.copy2(source, target)
        expected = kwargs["expected_codes"]
        assert isinstance(expected, frozenset)
        returncode = next(iter(expected))
        return {
            "returncode": returncode,
            "elapsed_ms": 10.0,
            "status": "supported",
            "cpu_time_ms": 5,
            "private_bytes": 100,
            "working_set_bytes": 90,
            "peak_working_set_bytes": 110,
            "os_threads": 2,
        }

    report = package_layout_experiment.run_layout_experiment(
        repository,
        temp_root=tmp_path / "experiments",
        warmups=0,
        iterations=1,
        pyinstaller=builder,
        build_runner=fake_build,
        sample_runner=fake_sample,
        source_validator=lambda _root: "a" * 40,
    )

    assert observed_layouts == ["onefile", "onedir"]
    assert report["result"] == "PACKAGE_LAYOUT_EXPERIMENT_RECORDED"
    assert report["layouts"]["onefile"]["artifact"]["files"] == 1
    assert report["layouts"]["onedir"]["artifact"]["files"] == 2
    expected_files = sum(
        len(files)
        for files in package_layout_experiment.BUILTIN_PROVIDER_HASHES.values()
    )
    assert (
        report["layouts"]["onefile"]["measurement_materialization"][
            "added_files"
        ]
        == expected_files
    )
    assert report["layouts"]["onedir"]["copied_folder_smoke"]["passed"] is True
    assert report["artifacts_retained"] is False
    assert not tuple((tmp_path / "experiments").glob("g39-*"))


def test_dirty_source_stops_before_creating_experiment_root(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    builder = tmp_path / "pyinstaller.exe"
    builder.write_bytes(b"builder")
    experiment_root = tmp_path / "experiments"

    def dirty(_root: Path) -> str:
        raise RuntimeError("source is dirty")

    with pytest.raises(RuntimeError, match="source is dirty"):
        package_layout_experiment.run_layout_experiment(
            repository,
            temp_root=experiment_root,
            pyinstaller=builder,
            source_validator=dirty,
        )

    assert not experiment_root.exists()


def test_cli_defaults_to_a_side_effect_free_plan(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        package_layout_experiment,
        "run_layout_experiment",
        lambda *_args, **_kwargs: pytest.fail("default CLI must not build"),
    )

    assert package_layout_experiment.main([]) == 0
    output = capsys.readouterr().out
    assert "BUILD_NOT_EXECUTED" in output
    assert '"execute_required": true' in output


def test_process_sample_records_the_child_without_visible_ui(tmp_path: Path) -> None:
    sample = package_layout_experiment.run_process_sample(
        (
            sys.executable,
            "-B",
            "-c",
            "import time; time.sleep(0.05)",
        ),
        cwd=tmp_path,
        environment={},
        expected_codes=frozenset({0}),
        timeout=2,
    )

    assert sample["returncode"] == 0
    assert sample["elapsed_ms"] >= 50
    if sys.platform == "win32":
        assert sample["status"] == "supported"
        assert sample["private_bytes"] > 0
        assert sample["working_set_bytes"] > 0
        assert sample["os_threads"] >= 1


def test_process_sample_rejects_an_unexpected_exit(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="expected"):
        package_layout_experiment.run_process_sample(
            (sys.executable, "-B", "-c", "raise SystemExit(3)"),
            cwd=tmp_path,
            environment={},
            expected_codes=frozenset({0}),
            timeout=2,
        )


def test_process_sample_contains_the_windows_process_before_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Job:
        def __init__(self, **limits: object) -> None:
            events.append(("job", limits))

        def assign(self, handle: int) -> None:
            events.append(("assign", handle))

        def close(self) -> None:
            events.append("close")

    class Process:
        _handle = 51
        returncode = 0
        stdin = None
        polls = iter((None, 0))

        def poll(self) -> int | None:
            return next(self.polls, 0)

        def communicate(self, *, timeout: float) -> tuple[str, str]:
            events.append(("communicate", timeout))
            return "", ""

        def kill(self) -> None:
            events.append("kill")

    def popen(command: list[str], **options: object) -> Process:
        events.append(("popen", tuple(command), options))
        return Process()

    monkeypatch.setattr(package_layout_experiment, "ProviderJob", Job)
    monkeypatch.setattr(package_layout_experiment.subprocess, "Popen", popen)
    monkeypatch.setattr(
        package_layout_experiment,
        "_resume_suspended_process",
        lambda handle: events.append(("resume", handle)),
    )
    monkeypatch.setattr(
        package_layout_experiment,
        "_windows_child_metrics",
        lambda _process: {
            "private_bytes": 10,
            "working_set_bytes": 9,
            "peak_working_set_bytes": 11,
            "os_threads": 1,
            "cpu_time_ms": 1,
        },
    )
    monkeypatch.setattr(package_layout_experiment.time, "sleep", lambda _delay: None)

    sample = package_layout_experiment.run_process_sample(
        ("MediaManager.exe", "--version"),
        cwd=tmp_path,
        environment={"SYSTEMROOT": r"C:\Windows"},
        expected_codes=frozenset({0}),
    )

    assert sample["status"] == "supported"
    assert events.index(("assign", 51)) < events.index(("resume", 51))
    popen_event = next(event for event in events if event[0] == "popen")
    assert popen_event[2]["creationflags"] & package_layout_experiment._CREATE_SUSPENDED
    assert events[-1] == "close"


def test_execute_rejects_repository_output_before_build(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        package_layout_experiment,
        "run_layout_experiment",
        lambda *_args, **_kwargs: pytest.fail("unsafe output must stop before build"),
    )

    repository_output = Path(package_layout_experiment.__file__).parents[1] / "bad.json"
    assert (
        package_layout_experiment.main(
            ["--execute", "--output", str(repository_output)]
        )
        == 2
    )
    assert "outside the repository" in capsys.readouterr().err
