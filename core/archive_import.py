"""Bounded, non-executable ZIP media import for official account exports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import stat
import uuid
from zipfile import BadZipFile, ZipFile, ZipInfo


MAX_ARCHIVE_BYTES = 8 * 1024**3
MAX_ARCHIVE_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 64 * 1024**3
MAX_COMPRESSION_RATIO = 200
_METADATA_SUFFIXES = frozenset({".json", ".js", ".html", ".txt", ".csv"})


@dataclass(frozen=True, slots=True)
class ArchiveMediaEntry:
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class ArchivePreview:
    archive: Path
    media_entries: tuple[ArchiveMediaEntry, ...]
    metadata_count: int
    total_uncompressed_bytes: int


def _safe_member_path(info: ZipInfo) -> PurePosixPath:
    if not info.filename or "\\" in info.filename or "\x00" in info.filename:
        raise ValueError("archive entry path is invalid")
    path = PurePosixPath(info.filename)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("archive entry path escapes its destination")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise ValueError("archive symbolic links are not accepted")
    if info.flag_bits & 0x1:
        raise ValueError("encrypted archive entries are not accepted")
    if info.file_size < 0 or info.compress_size < 0:
        raise ValueError("archive entry size is invalid")
    if info.file_size and not info.compress_size:
        raise ValueError("archive entry compression ratio is invalid")
    if (
        info.compress_size
        and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
    ):
        raise ValueError("archive entry compression ratio is too high")
    return path


def preview_media_archive(
    archive: Path,
    *,
    allowed_media_suffixes: frozenset[str],
) -> ArchivePreview:
    candidate = Path(archive).resolve()
    if (
        candidate.suffix.casefold() != ".zip"
        or candidate.is_symlink()
        or not candidate.is_file()
        or candidate.stat().st_size > MAX_ARCHIVE_BYTES
    ):
        raise ValueError("official export must be a local ZIP within the size limit")
    normalized_suffixes = frozenset(
        suffix.casefold() for suffix in allowed_media_suffixes
    )
    if not normalized_suffixes or any(
        not suffix.startswith(".") or len(suffix) > 16
        for suffix in normalized_suffixes
    ):
        raise ValueError("allowed archive media suffixes are invalid")
    media: list[ArchiveMediaEntry] = []
    metadata_count = 0
    total = 0
    seen: set[str] = set()
    try:
        with ZipFile(candidate) as source:
            members = source.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES:
                raise ValueError("archive contains too many entries")
            for info in members:
                path = _safe_member_path(info)
                key = path.as_posix().casefold()
                if key in seen:
                    raise ValueError("archive contains duplicate entry paths")
                seen.add(key)
                if info.is_dir():
                    continue
                total += info.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("archive expands beyond the safety limit")
                suffix = path.suffix.casefold()
                if suffix in normalized_suffixes:
                    media.append(ArchiveMediaEntry(path.as_posix(), info.file_size))
                elif suffix in _METADATA_SUFFIXES:
                    metadata_count += 1
    except BadZipFile as error:
        raise ValueError("official export ZIP is damaged or unsupported") from error
    return ArchivePreview(
        candidate,
        tuple(media),
        metadata_count,
        total,
    )


def extract_media_archive(
    archive: Path,
    destination: Path,
    *,
    allowed_media_suffixes: frozenset[str],
) -> tuple[Path, ...]:
    preview = preview_media_archive(
        archive, allowed_media_suffixes=allowed_media_suffixes
    )
    if not preview.media_entries:
        raise ValueError("archive contains no supported media")
    output = Path(destination).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("archive destination is unsafe")
    index_path = output / "media-index.json"
    if index_path.exists():
        raise ValueError("archive index path is already in use")
    names = {entry.name for entry in preview.media_entries}
    extracted: list[Path] = []
    temporary_paths: list[Path] = []
    try:
        with ZipFile(preview.archive) as source:
            by_name = {info.filename: info for info in source.infolist()}
            for name in sorted(names):
                info = by_name.get(name)
                if info is None or _safe_member_path(info).as_posix() != name:
                    raise ValueError("archive changed after it was inspected")
                target = output.joinpath(*PurePosixPath(name).parts).resolve()
                if not target.is_relative_to(output) or target.exists():
                    raise ValueError("archive output path is already in use")
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(
                    f".{target.name}.{uuid.uuid4().hex}.part"
                )
                temporary_paths.append(temporary)
                written = 0
                with source.open(info) as input_file, temporary.open("xb") as output_file:
                    while chunk := input_file.read(1024 * 1024):
                        written += len(chunk)
                        if written > info.file_size:
                            raise ValueError("archive entry exceeded its declared size")
                        output_file.write(chunk)
                if written != info.file_size:
                    raise ValueError("archive entry ended before its declared size")
                temporary.replace(target)
                temporary_paths.remove(temporary)
                extracted.append(target)
    except BadZipFile as error:
        for path in reversed(extracted):
            path.unlink(missing_ok=True)
        raise ValueError("official export ZIP changed or became unreadable") from error
    except (OSError, ValueError):
        for path in reversed(extracted):
            path.unlink(missing_ok=True)
        raise
    finally:
        for temporary in temporary_paths:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    index = {
        "schema": 1,
        "source_archive": preview.archive.name,
        "media": [
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
            }
            for path in extracted
        ],
    }
    temporary_index = output / f".media-index.{uuid.uuid4().hex}.tmp"
    try:
        temporary_index.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_index.replace(index_path)
    except OSError:
        temporary_index.unlink(missing_ok=True)
        for path in reversed(extracted):
            path.unlink(missing_ok=True)
        raise
    return tuple(extracted)
