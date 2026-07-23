from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools import run_tests


def test_default_temp_root_prefers_local_app_data(tmp_path: Path) -> None:
    assert run_tests.default_temp_root({"LOCALAPPDATA": str(tmp_path)}) == (
        tmp_path / "MediaManager-TestRuns"
    )


def test_windows_default_requires_local_app_data() -> None:
    with pytest.raises(RuntimeError, match="--temp-root"):
        run_tests.default_temp_root({}, platform="nt")


def test_targets_are_confined_to_repository_tests(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_example.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_example(): pass\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("def test_outside(): pass\n", encoding="utf-8")

    assert run_tests.resolve_test_targets(
        tmp_path, ("tests/test_example.py::test_example",)
    ) == (f"{test_file}::test_example",)
    with pytest.raises(ValueError, match="must stay under"):
        run_tests.resolve_test_targets(tmp_path, ("outside.py",))


def test_symbolic_link_tests_root_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / "tests").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    with pytest.raises(ValueError, match="must not be a symbolic link"):
        run_tests.resolve_test_targets(tmp_path, ())


def test_run_uses_repository_root_and_cleans_only_owned_temp(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repository"
    test_file = root / "tests" / "test_example.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_example(): pass\n", encoding="utf-8")
    temp_root = tmp_path / "user-temp"
    sibling = temp_root / "preserved"
    sibling.mkdir(parents=True)
    (sibling / "keep.txt").write_text("keep", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setenv("PYTEST_ADDOPTS", str(tmp_path / "outside"))

    def fake_run(command, *, cwd, check, env):
        captured.update(
            {"command": command, "cwd": cwd, "check": check, "env": env}
        )
        basetemp = Path(command[command.index("--basetemp") + 1])
        runtime_temp = Path(env["TEMP"])
        assert runtime_temp.is_dir()
        assert env["TMP"] == str(runtime_temp)
        assert env["TMPDIR"] == str(runtime_temp)
        assert "PYTEST_ADDOPTS" not in env
        assert basetemp.parent == runtime_temp.parent
        assert not basetemp.exists()
        basetemp.mkdir()
        (basetemp / "created-by-test.txt").write_text("test", encoding="utf-8")
        captured["basetemp"] = basetemp
        captured["attempt"] = runtime_temp.parent
        return CompletedProcess(command, 0)

    monkeypatch.setattr(run_tests.subprocess, "run", fake_run)

    assert run_tests.run_tests(root, temp_root=temp_root) == 0
    assert captured["cwd"] == root.resolve()
    assert str(test_file.parent.resolve()) in captured["command"]
    assert not Path(captured["attempt"]).exists()
    assert (sibling / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_invalid_target_cleans_current_attempt(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "tests").mkdir(parents=True)
    temp_root = tmp_path / "user-temp"
    with pytest.raises(ValueError, match="must stay under"):
        run_tests.run_tests(
            root,
            temp_root=temp_root,
            targets=(str(tmp_path / "outside.py"),),
        )
    assert tuple(temp_root.glob("pytest-*")) == ()


def test_runtime_temp_creation_failure_cleans_current_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repository"
    (root / "tests").mkdir(parents=True)
    temp_root = tmp_path / "user-temp"
    original_mkdir = Path.mkdir

    def fail_runtime_mkdir(path: Path, *args, **kwargs) -> None:
        if path.name == "runtime" and path.parent.name.startswith("pytest-"):
            raise PermissionError("runtime temp is locked")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_runtime_mkdir)

    with pytest.raises(PermissionError, match="runtime temp is locked"):
        run_tests.run_tests(root, temp_root=temp_root)

    assert tuple(temp_root.glob("pytest-*")) == ()


def test_keep_temp_preserves_only_current_invocation(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repository"
    (root / "tests").mkdir(parents=True)
    captured: dict[str, Path] = {}

    def fake_run(command, *, cwd, check, env):
        assert cwd == root.resolve()
        assert check is False
        assert Path(env["TEMP"]).is_dir()
        captured["basetemp"] = Path(command[command.index("--basetemp") + 1])
        return CompletedProcess(command, 1)

    monkeypatch.setattr(run_tests.subprocess, "run", fake_run)

    assert run_tests.run_tests(
        root,
        temp_root=tmp_path / "user-temp",
        keep_temp=True,
    ) == 1
    assert captured["basetemp"].parent.is_dir()


def test_cleanup_retries_transient_windows_lock(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "attempt"
    target.mkdir()
    original_rmtree = run_tests.shutil.rmtree
    calls = 0

    def transient_failure(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("locked")
        original_rmtree(path)

    monkeypatch.setattr(run_tests.shutil, "rmtree", transient_failure)
    monkeypatch.setattr(run_tests.time, "sleep", lambda _seconds: None)

    run_tests.remove_test_tree(target)

    assert calls == 2
    assert not target.exists()


@pytest.mark.parametrize(("pytest_code", "expected"), ((0, 2), (1, 1)))
def test_cleanup_failure_does_not_hide_pytest_failure(
    tmp_path: Path, monkeypatch, pytest_code: int, expected: int
) -> None:
    root = tmp_path / "repository"
    (root / "tests").mkdir(parents=True)

    monkeypatch.setattr(
        run_tests.subprocess,
        "run",
        lambda *_args, **_kwargs: CompletedProcess([], pytest_code),
    )
    monkeypatch.setattr(
        run_tests,
        "remove_test_tree",
        lambda _path: (_ for _ in ()).throw(PermissionError("locked")),
    )

    assert run_tests.run_tests(root, temp_root=tmp_path / "user-temp") == expected
