from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

import tools.quality_audit as quality_audit
from tools.quality_audit import (
    DIRECTORY_TARGETS,
    QualityScope,
    QualityScopeError,
    ROOT_FILE_TARGETS,
    build_quality_scope,
    ruff_command,
    ruff_commands,
    run_quality_audit,
    scan_text_pollution,
)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for relative in DIRECTORY_TARGETS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in ROOT_FILE_TARGETS:
        (root / relative).write_text("clean\n", encoding="utf-8")
    (root / "core" / "module.py").write_text("value = 1\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("clean\n", encoding="utf-8")
    (root / "tests" / "test_module.py").write_text("def test_value():\n    assert 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    return root


def _scope(root: Path):
    return build_quality_scope(
        root,
        directory_targets=("core", "docs", "tests"),
        root_file_targets=("pyproject.toml",),
    )


def test_scope_only_contains_explicit_targets(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    outside = root / "tmp-old"
    outside.mkdir()
    (outside / "polluted.py").write_text("broken =\n", encoding="utf-8")

    scope = _scope(root)

    assert Path("tmp-old/polluted.py") not in scope.ruff_files
    assert scope.ruff_files == (Path("core/module.py"), Path("tests/test_module.py"))
    command = ruff_command(scope)
    assert command[2:4] == ("ruff", "check")
    assert "." not in command[4:]
    assert all("tmp-old" not in argument for argument in command[4:])


def test_text_pollution_in_scoped_file_is_still_reported(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    pollution = "<" * 7 + " HEAD\n" + chr(0xE234) + "\n"
    (root / "docs" / "guide.md").write_text(pollution, encoding="utf-8")

    issues = scan_text_pollution(_scope(root))

    rendered = {issue.render() for issue in issues}
    assert "MERGE_MARKER docs/guide.md:1" in rendered
    assert "PRIVATE_USE docs/guide.md:2 U+E234" in rendered


def test_declared_txt_and_extensionless_targets_are_scanned(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    (root / "LICENSE").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    (root / "requirements-lock.txt").write_bytes(b"\xff")

    scope = build_quality_scope(root)
    issues = {issue.render() for issue in scan_text_pollution(scope)}

    assert Path("LICENSE") in scope.text_files
    assert Path("requirements-lock.txt") in scope.text_files
    assert "MERGE_MARKER LICENSE:1" in issues
    assert "INVALID_UTF8 requirements-lock.txt" in issues


def test_scope_rejects_parent_traversal(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (tmp_path / "outside.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(QualityScopeError, match="normalized relative path"):
        build_quality_scope(
            root,
            directory_targets=("core",),
            root_file_targets=("../outside.py",),
        )


def test_scope_rejects_drive_relative_target(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    with pytest.raises(QualityScopeError, match="normalized relative path"):
        build_quality_scope(
            root,
            directory_targets=("core",),
            root_file_targets=("C:outside.py",),
        )


def test_scope_rejects_symlink_in_allowed_tree(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    link = root / "core" / "linked.py"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(QualityScopeError, match="symlink or junction"):
        _scope(root)


def test_scope_fails_closed_when_entry_is_link_like(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    linked = root / "core" / "linked.py"
    linked.write_text("value = 1\n", encoding="utf-8")
    original = quality_audit._is_link_like
    monkeypatch.setattr(
        quality_audit,
        "_is_link_like",
        lambda path: path == linked or original(path),
    )

    with pytest.raises(QualityScopeError, match="symlink or junction"):
        _scope(root)


def test_invalid_utf8_is_reported_without_aborting_other_files(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "docs" / "invalid.md").write_bytes(b"\xff")

    issues = scan_text_pollution(_scope(root))

    assert any(issue.render() == "INVALID_UTF8 docs/invalid.md" for issue in issues)


def test_runner_uses_repository_cwd_and_propagates_ruff_failure(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, check):
        captured.update(command=command, cwd=cwd, check=check)
        return subprocess.CompletedProcess(command, 1)

    result = run_quality_audit(
        root,
        run_text=False,
        runner=fake_run,
    )

    assert result == 1
    assert captured["cwd"] == root.resolve()
    assert captured["check"] is False
    assert "." not in captured["command"][4:]


def test_ruff_commands_respect_budget_and_include_each_file_once(
    tmp_path: Path,
) -> None:
    paths = tuple(
        Path("tests") / f"test_windows_command_{index:02d}_{'x' * 32}.py"
        for index in range(12)
    )
    scope = QualityScope(root=tmp_path.resolve(), ruff_files=paths, text_files=())
    prefix = ruff_command(
        QualityScope(root=scope.root, ruff_files=(paths[0],), text_files=())
    )[:4]
    budget = max(
        len(subprocess.list2cmdline((*prefix, path.as_posix()))) for path in paths
    )

    commands = ruff_commands(scope, argv_budget=budget)
    arguments = [argument for command in commands for argument in command[4:]]

    assert len(commands) > 1
    assert all(len(subprocess.list2cmdline(command)) <= budget for command in commands)
    assert arguments == [path.as_posix() for path in paths]
    assert len(arguments) == len(set(arguments))


def test_runner_executes_all_ruff_batches_and_aggregates_failure(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    for index in range(8):
        (root / "core" / f"module_{index:02d}_{'x' * 32}.py").write_text(
            "value = 1\n",
            encoding="utf-8",
        )
    scope = build_quality_scope(root)
    prefix = ruff_command(
        QualityScope(root=scope.root, ruff_files=(scope.ruff_files[0],), text_files=())
    )[:4]
    budget = max(
        len(subprocess.list2cmdline((*prefix, path.as_posix())))
        for path in scope.ruff_files
    )
    expected_commands = ruff_commands(scope, argv_budget=budget)
    captured: list[tuple[str, ...]] = []

    def fake_run(command, *, cwd, check):
        assert cwd == root.resolve()
        assert check is False
        captured.append(command)
        return subprocess.CompletedProcess(command, 1 if len(captured) == 2 else 0)

    result = run_quality_audit(
        root,
        run_text=False,
        runner=fake_run,
        ruff_argv_budget=budget,
    )

    assert result == 1
    assert captured == list(expected_commands)
    assert len(captured) > 2
