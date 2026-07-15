"""Deterministic fingerprint for the bounded MediaManager source surface."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


_SOURCE_DIRS = (
    ".github",
    "assets",
    "contracts",
    "core",
    "docs",
    "mod/builtin",
    "plugin_host",
    "tests",
    "third_party",
    "tools",
    "trusted_ui",
)
_ROOT_FILES = (
    "AGENTS.md",
    "LICENSE",
    "MediaManager.spec",
    "README.md",
    "desktop.py",
    "main.py",
    "pyproject.toml",
    "requirements-lock.txt",
    "安裝必備軟體.bat",
    "暫存檔清除.bat",
)
_ALLOWED_SUFFIXES = frozenset(
    {
        ".bat",
        ".ico",
        ".json",
        ".md",
        ".png",
        ".py",
        ".spec",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
_MAX_FILES = 20_000
_MAX_FILE_SIZE = 16 * 1024 * 1024
_MAX_TOTAL_SIZE = 256 * 1024 * 1024


def _source_files(root: Path) -> tuple[Path, ...]:
    candidates = [root / name for name in _ROOT_FILES]
    for name in _SOURCE_DIRS:
        directory = root / Path(*name.split("/"))
        if directory.is_dir() and not directory.is_symlink():
            candidates.extend(
                path
                for path in directory.rglob("*")
                if path.suffix.casefold() in _ALLOWED_SUFFIXES
            )
    files = tuple(
        sorted(
            (
                path
                for path in candidates
                if path.is_file() and not path.is_symlink()
            ),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )
    if len(files) > _MAX_FILES:
        raise ValueError("source fingerprint file count exceeds limit")
    return files


def source_fingerprint(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    total_size = 0
    for path in _source_files(root):
        size = path.stat().st_size
        if size > _MAX_FILE_SIZE:
            raise ValueError(f"source fingerprint file exceeds limit: {path.name}")
        total_size += size
        if total_size > _MAX_TOTAL_SIZE:
            raise ValueError("source fingerprint total size exceeds limit")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def source_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=root.resolve(),
            capture_output=True,
            text=True,
            encoding="ascii",
            errors="replace",
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = result.stdout.strip().casefold()
    if result.returncode != 0 or len(value) not in {40, 64}:
        return "unavailable"
    if any(char not in "0123456789abcdef" for char in value):
        return "unavailable"
    return value
