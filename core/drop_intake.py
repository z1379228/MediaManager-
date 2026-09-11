"""Bounded classification for explicit drag-and-drop intake."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

from core.downloads.batch_import import parse_download_intake_text
from core.media_library import classify


MAX_DROP_ITEMS = 500
_BATCH_SUFFIXES = frozenset({".csv", ".txt"})


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


@dataclass(frozen=True, slots=True)
class DropIntakeIssue:
    value: str
    reason: str


@dataclass(frozen=True, slots=True)
class DropIntake:
    """One non-executing intake preview for a trusted UI drop target."""

    urls: tuple[str, ...] = ()
    batch_files: tuple[Path, ...] = ()
    media_files: tuple[Path, ...] = ()
    issues: tuple[DropIntakeIssue, ...] = ()

    @property
    def accepted_count(self) -> int:
        return len(self.urls) + len(self.batch_files) + len(self.media_files)


def prepare_drop_intake(
    *,
    text: object = "",
    local_paths: Iterable[Path | str] = (),
) -> DropIntake:
    """Classify bounded text and regular local files without starting work."""

    if not isinstance(text, str):
        raise ValueError("drop text is invalid")
    try:
        raw_paths = tuple(local_paths)
    except TypeError as error:
        raise ValueError("drop paths are invalid") from error
    if len(raw_paths) > MAX_DROP_ITEMS:
        raise ValueError("drop intake exceeds the 500-item limit")

    urls: list[str] = []
    batch_files: list[Path] = []
    media_files: list[Path] = []
    issues: list[DropIntakeIssue] = []
    seen_paths: set[str] = set()

    if text.strip():
        parsed = parse_download_intake_text(text)
        urls.extend(entry.url for entry in parsed.entries)
        issues.extend(
            DropIntakeIssue(issue.value[:300], issue.reason)
            for issue in parsed.issues
        )

    for raw_path in raw_paths:
        try:
            candidate = Path(raw_path).expanduser()
        except (TypeError, ValueError) as error:
            issues.append(DropIntakeIssue("", f"invalid local path: {error}"))
            continue
        display = str(candidate)[:300]
        try:
            if _is_linklike(candidate):
                issues.append(
                    DropIntakeIssue(
                        display,
                        "symbolic links and junctions are not accepted",
                    )
                )
                continue
            if not candidate.is_file():
                issues.append(
                    DropIntakeIssue(
                        display,
                        "local file is missing or is not a regular file",
                    )
                )
                continue
            resolved = candidate.resolve()
        except OSError:
            issues.append(
                DropIntakeIssue(
                    display,
                    "local file could not be inspected",
                )
            )
            continue
        key = os.path.normcase(str(resolved))
        if key in seen_paths:
            issues.append(DropIntakeIssue(display, "duplicate local file"))
            continue
        seen_paths.add(key)
        suffix = resolved.suffix.casefold()
        if suffix in _BATCH_SUFFIXES:
            batch_files.append(resolved)
        elif classify(resolved) is not None:
            media_files.append(resolved)
        else:
            issues.append(
                DropIntakeIssue(display, "unsupported local file type")
            )

    if len(urls) + len(raw_paths) > MAX_DROP_ITEMS:
        raise ValueError("drop intake exceeds the 500-item limit")
    return DropIntake(
        tuple(urls),
        tuple(batch_files),
        tuple(media_files),
        tuple(issues),
    )
