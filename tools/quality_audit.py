from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path, PurePath
import subprocess
import sys
from typing import Callable, Iterable, Sequence


DIRECTORY_TARGETS = (
    ".github/workflows",
    "contracts",
    "core",
    "docs",
    "mod",
    "plugin_host",
    "tests",
    "tools",
    "trusted_ui",
)
ROOT_FILE_TARGETS = (
    "AGENTS.md",
    "INSTALL.md",
    "LICENSE",
    "MOD-DEVELOPMENT.md",
    "MediaManager.spec",
    "README.md",
    "desktop.py",
    "main.py",
    "pyproject.toml",
    "requirements-lock.txt",
    "安裝必備軟體.bat",
    "暫存檔清除.bat",
)
TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".txt",
        ".bat",
        ".ps1",
        ".spec",
    }
)
EXTENSIONLESS_TEXT_TARGETS = frozenset({Path("LICENSE")})
RUFF_SUFFIXES = frozenset({".py"})
RUFF_ARGV_BUDGET = 24_000

_TOOL_ARTIFACTS = (
    chr(0xE200) + "cite",
    "assistant" + " to=",
    "recipient=" + "functions.",
)


class QualityScopeError(RuntimeError):
    """Raised when a configured audit target cannot be inspected safely."""


@dataclass(frozen=True)
class QualityScope:
    root: Path
    ruff_files: tuple[Path, ...]
    text_files: tuple[Path, ...]


@dataclass(frozen=True)
class TextPollutionIssue:
    kind: str
    path: Path
    line: int | None = None
    detail: str | None = None

    def render(self) -> str:
        location = self.path.as_posix()
        if self.line is not None:
            location = f"{location}:{self.line}"
        if self.detail:
            return f"{self.kind} {location} {self.detail}"
        return f"{self.kind} {location}"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _relative_target(value: str | Path) -> Path:
    target = Path(value)
    pure = PurePath(value)
    if (
        target.is_absolute()
        or target.drive
        or target.root
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise QualityScopeError(f"audit target must be a normalized relative path: {value}")
    return Path(*pure.parts)


def _assert_bounded(root: Path, candidate: Path) -> None:
    try:
        candidate.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise QualityScopeError(f"audit target escapes repository root: {candidate}") from exc


def _validate_target(root: Path, value: str | Path, *, directory: bool) -> Path:
    relative = _relative_target(value)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if not current.exists():
                raise QualityScopeError(f"configured audit target is missing: {relative.as_posix()}")
            if _is_link_like(current):
                raise QualityScopeError(f"symlink or junction is not allowed in audit scope: {relative.as_posix()}")
        except OSError as exc:
            raise QualityScopeError(f"cannot inspect configured audit target: {relative.as_posix()}") from exc

    _assert_bounded(root, current)
    if directory and not current.is_dir():
        raise QualityScopeError(f"configured audit directory is not a directory: {relative.as_posix()}")
    if not directory and not current.is_file():
        raise QualityScopeError(f"configured audit file is not a file: {relative.as_posix()}")
    return relative


def _walk_directory(root: Path, relative_directory: Path) -> Iterable[Path]:
    pending = [relative_directory]
    while pending:
        relative = pending.pop()
        directory = root / relative
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name.casefold(), reverse=True)
        except OSError as exc:
            raise QualityScopeError(f"cannot enumerate scoped directory: {relative.as_posix()}") from exc

        for entry in entries:
            child = relative / entry.name
            path = root / child
            try:
                if entry.is_symlink() or _is_link_like(path):
                    raise QualityScopeError(
                        f"symlink or junction is not allowed in audit scope: {child.as_posix()}"
                    )
                if entry.is_dir(follow_symlinks=False):
                    pending.append(child)
                elif entry.is_file(follow_symlinks=False):
                    _assert_bounded(root, path)
                    yield child
                else:
                    raise QualityScopeError(f"unsupported filesystem entry in audit scope: {child.as_posix()}")
            except OSError as exc:
                raise QualityScopeError(f"cannot inspect scoped path: {child.as_posix()}") from exc


def build_quality_scope(
    root: Path,
    *,
    directory_targets: Sequence[str | Path] = DIRECTORY_TARGETS,
    root_file_targets: Sequence[str | Path] = ROOT_FILE_TARGETS,
) -> QualityScope:
    root_input = Path(root)
    if _is_link_like(root_input):
        raise QualityScopeError(f"repository root cannot be a symlink or junction: {root_input}")
    try:
        resolved_root = root_input.resolve(strict=True)
    except OSError as exc:
        raise QualityScopeError(f"repository root does not exist: {root_input}") from exc
    if not resolved_root.is_dir():
        raise QualityScopeError(f"repository root is not a directory: {resolved_root}")

    all_files: set[Path] = set()
    for value in directory_targets:
        relative = _validate_target(resolved_root, value, directory=True)
        all_files.update(_walk_directory(resolved_root, relative))
    for value in root_file_targets:
        all_files.add(_validate_target(resolved_root, value, directory=False))

    ruff_files = tuple(sorted((path for path in all_files if path.suffix.lower() in RUFF_SUFFIXES)))
    text_files = tuple(
        sorted(
            path
            for path in all_files
            if path.suffix.lower() in TEXT_SUFFIXES
            or path in EXTENSIONLESS_TEXT_TARGETS
        )
    )
    if not ruff_files:
        raise QualityScopeError("controlled Ruff scope contains no Python files")
    if not text_files:
        raise QualityScopeError("controlled text scope contains no supported files")
    return QualityScope(root=resolved_root, ruff_files=ruff_files, text_files=text_files)


def scan_text_pollution(scope: QualityScope) -> tuple[TextPollutionIssue, ...]:
    issues: list[TextPollutionIssue] = []
    for relative in scope.text_files:
        path = scope.root / relative
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            issues.append(TextPollutionIssue("INVALID_UTF8", relative))
            continue
        except OSError as exc:
            raise QualityScopeError(f"cannot read scoped text file: {relative.as_posix()}") from exc

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.startswith(("<<<<<<<", "=======", ">>>>>>>")):
                issues.append(TextPollutionIssue("MERGE_MARKER", relative, line_number))
            for artifact in _TOOL_ARTIFACTS:
                if artifact in line:
                    issues.append(TextPollutionIssue("TOOL_ARTIFACT", relative, line_number))
            for character in line:
                code_point = ord(character)
                if 0xE000 <= code_point <= 0xF8FF:
                    issues.append(
                        TextPollutionIssue(
                            "PRIVATE_USE",
                            relative,
                            line_number,
                            f"U+{code_point:04X}",
                        )
                    )
                    break
    return tuple(sorted(set(issues), key=TextPollutionIssue.render))


def _ruff_prefix() -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "ruff",
        "check",
    )


def _windows_command_line_length(command: Sequence[str]) -> int:
    return len(subprocess.list2cmdline(command))


def ruff_commands(
    scope: QualityScope,
    *,
    argv_budget: int = RUFF_ARGV_BUDGET,
) -> tuple[tuple[str, ...], ...]:
    prefix = _ruff_prefix()
    if argv_budget <= _windows_command_line_length(prefix):
        raise ValueError("Ruff argv budget is too small for the command prefix")

    commands: list[tuple[str, ...]] = []
    current = list(prefix)
    for path in scope.ruff_files:
        argument = path.as_posix()
        candidate = (*current, argument)
        if _windows_command_line_length(candidate) <= argv_budget:
            current.append(argument)
            continue

        if len(current) == len(prefix):
            raise QualityScopeError(
                f"scoped Ruff path exceeds argv budget: {argument}"
            )
        commands.append(tuple(current))
        current = [*prefix, argument]
        if _windows_command_line_length(current) > argv_budget:
            raise QualityScopeError(
                f"scoped Ruff path exceeds argv budget: {argument}"
            )

    if len(current) > len(prefix):
        commands.append(tuple(current))
    if not commands:
        raise QualityScopeError("controlled Ruff scope contains no Python files")
    return tuple(commands)


def ruff_command(scope: QualityScope) -> tuple[str, ...]:
    commands = ruff_commands(scope)
    if len(commands) != 1:
        raise QualityScopeError("Ruff scope requires multiple bounded commands")
    return commands[0]


def run_quality_audit(
    root: Path,
    *,
    run_ruff: bool = True,
    run_text: bool = True,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ruff_argv_budget: int = RUFF_ARGV_BUDGET,
) -> int:
    if not run_ruff and not run_text:
        raise ValueError("at least one quality audit must be enabled")
    scope = build_quality_scope(root)
    print(
        f"QUALITY_SCOPE=PASS ruff_files={len(scope.ruff_files)} "
        f"text_files={len(scope.text_files)}"
    )

    failed = False
    if run_ruff:
        commands = ruff_commands(scope, argv_budget=ruff_argv_budget)
        ruff_failed = False
        for command in commands:
            completed = runner(command, cwd=scope.root, check=False)
            if completed.returncode != 0:
                ruff_failed = True
        failed = ruff_failed
        state = "FAIL" if ruff_failed else "PASS"
        print(
            f"RUFF_AUDIT={state} files={len(scope.ruff_files)} "
            f"batches={len(commands)}"
        )

    if run_text:
        issues = scan_text_pollution(scope)
        for issue in issues:
            print(issue.render())
        if issues:
            failed = True
            print(f"TEXT_POLLUTION_SCAN=FAIL issues={len(issues)}")
        else:
            print(f"TEXT_POLLUTION_SCAN=PASS files={len(scope.text_files)}")

    print(f"QUALITY_AUDIT={'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Ruff and text-pollution checks over a fail-closed repository scope."
    )
    parser.add_argument("--root", type=Path, default=repository_root())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ruff-only", action="store_true")
    mode.add_argument("--text-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return run_quality_audit(
            args.root,
            run_ruff=not args.text_only,
            run_text=not args.ruff_only,
        )
    except (OSError, QualityScopeError, ValueError) as exc:
        print(f"QUALITY_SCOPE=FAIL {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
