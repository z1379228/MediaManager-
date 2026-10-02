"""Fail closed when runtime subprocess calls may open Windows console windows."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


RUNTIME_DIRECTORIES = ("core", "mod", "plugin_host", "trusted_ui")
RUNTIME_ROOT_FILES = ("desktop.py", "main.py")
_PROCESS_CALLS = frozenset({"Popen", "run"})


@dataclass(frozen=True, slots=True)
class SubprocessPolicyIssue:
    """One runtime child-process call without a proven hidden-window policy."""

    path: Path
    line: int
    call: str

    def render(self) -> str:
        return (
            f"VISIBLE_SUBPROCESS_RISK {self.path.as_posix()}:{self.line} "
            f"{self.call}"
        )


def _runtime_python_files(root: Path) -> tuple[Path, ...]:
    paths: set[Path] = set()
    for name in RUNTIME_ROOT_FILES:
        candidate = root / name
        if candidate.is_file() and not candidate.is_symlink():
            paths.add(candidate)
    for name in RUNTIME_DIRECTORIES:
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            continue
        paths.update(
            path
            for path in directory.rglob("*.py")
            if "__pycache__" not in path.parts and not path.is_symlink()
        )
    return tuple(sorted(paths))


def _contains_create_no_window(
    node: ast.AST,
    assignments: dict[str, tuple[ast.AST, ...]],
    *,
    seen: frozenset[str] = frozenset(),
) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "CREATE_NO_WINDOW":
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "CREATE_NO_WINDOW"
    ):
        return True
    if isinstance(node, ast.Name):
        if node.id in seen:
            return False
        return any(
            _contains_create_no_window(
                value,
                assignments,
                seen=seen | {node.id},
            )
            for value in assignments.get(node.id, ())
        )
    return any(
        _contains_create_no_window(child, assignments, seen=seen)
        for child in ast.iter_child_nodes(node)
    )


def _subprocess_call(
    node: ast.Call,
    module_aliases: frozenset[str],
    direct_aliases: dict[str, str],
) -> str | None:
    function = node.func
    if (
        isinstance(function, ast.Attribute)
        and function.attr in _PROCESS_CALLS
        and isinstance(function.value, ast.Name)
        and function.value.id in module_aliases
    ):
        return f"subprocess.{function.attr}"
    if isinstance(function, ast.Name) and function.id in direct_aliases:
        return f"subprocess.{direct_aliases[function.id]}"
    return None


def _file_issues(root: Path, path: Path) -> tuple[SubprocessPolicyIssue, ...]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return ()

    module_aliases: set[str] = set()
    direct_aliases: dict[str, str] = {}
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in _PROCESS_CALLS:
                    direct_aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: Iterable[ast.expr]
            value: ast.AST | None
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            else:
                targets = (node.target,)
                value = node.value
            if value is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(value)
    frozen_assignments = {
        name: tuple(values) for name, values in assignments.items()
    }

    issues: list[SubprocessPolicyIssue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call = _subprocess_call(
            node,
            frozenset(module_aliases),
            direct_aliases,
        )
        if call is None:
            continue
        creationflags = next(
            (
                keyword.value
                for keyword in node.keywords
                if keyword.arg == "creationflags"
            ),
            None,
        )
        if creationflags is not None and _contains_create_no_window(
            creationflags,
            frozen_assignments,
        ):
            continue
        issues.append(
            SubprocessPolicyIssue(
                path.relative_to(root),
                int(getattr(node, "lineno", 1)),
                call,
            )
        )
    return tuple(issues)


def audit_subprocess_window_policy(
    root: Path,
) -> tuple[SubprocessPolicyIssue, ...]:
    """Inspect executable runtime code, excluding tests and maintenance tools."""

    resolved = Path(root).resolve()
    issues = [
        issue
        for path in _runtime_python_files(resolved)
        for issue in _file_issues(resolved, path)
    ]
    return tuple(sorted(issues, key=lambda issue: issue.render()))


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    args = parser.parse_args(argv)
    issues = audit_subprocess_window_policy(args.root)
    for issue in issues:
        print(issue.render())
    print(
        "SUBPROCESS_WINDOW_AUDIT="
        f"{'FAIL' if issues else 'PASS'} issues={len(issues)}"
    )
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
