"""Bounded TXT/CSV import for atomic download batches."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

from core.downloads.models import DownloadRequest


MAX_BATCH_IMPORT_BYTES = 2 * 1024 * 1024
MAX_BATCH_IMPORT_ENTRIES = 500

_URL_HEADERS = frozenset({"url", "link", "網址", "連結"})
_TITLE_HEADERS = frozenset({"title", "name", "標題", "名稱"})
_ARTIST_HEADERS = frozenset(
    {"artist", "author", "uploader", "歌手", "作者", "上傳者"}
)


@dataclass(frozen=True, slots=True)
class BatchImportEntry:
    row_number: int
    url: str
    title: str = ""
    artist: str = ""


@dataclass(frozen=True, slots=True)
class BatchImportIssue:
    row_number: int
    value: str
    reason: str


@dataclass(frozen=True, slots=True)
class BatchImportResult:
    entries: tuple[BatchImportEntry, ...]
    issues: tuple[BatchImportIssue, ...]


def _normalized_header(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _clean_metadata(value: str, *, field: str, limit: int) -> str:
    cleaned = " ".join(value.strip().split())
    if "\x00" in cleaned or len(cleaned) > limit:
        raise ValueError(f"{field} is invalid or too long")
    return cleaned


def _validated_url(value: str) -> str:
    url = value.strip()
    if not url or len(url) > 4096 or "\x00" in url:
        raise ValueError("URL is empty or too long")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise ValueError("URL is malformed") from error
    if parsed.scheme.casefold() not in {"http", "https"} or not hostname:
        raise ValueError("URL must use HTTP or HTTPS and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL credentials are not accepted")
    return parsed.scheme.casefold() + url[len(parsed.scheme) :]


def _append_entry(
    entries: list[BatchImportEntry],
    issues: list[BatchImportIssue],
    seen: set[str],
    *,
    row_number: int,
    raw_url: str,
    raw_title: str = "",
    raw_artist: str = "",
) -> None:
    try:
        url = _validated_url(raw_url)
        title = _clean_metadata(raw_title, field="title", limit=300)
        artist = _clean_metadata(raw_artist, field="artist", limit=200)
    except ValueError as error:
        issues.append(
            BatchImportIssue(row_number, raw_url.strip()[:300], str(error))
        )
        return
    duplicate_key = url
    if duplicate_key in seen:
        issues.append(BatchImportIssue(row_number, url[:300], "duplicate URL"))
        return
    seen.add(duplicate_key)
    entries.append(BatchImportEntry(row_number, url, title, artist))


def _parse_txt(text: str) -> BatchImportResult:
    rows = [
        (number, value.strip())
        for number, value in enumerate(text.splitlines(), start=1)
        if value.strip() and not value.lstrip().startswith("#")
    ]
    if len(rows) > MAX_BATCH_IMPORT_ENTRIES:
        raise ValueError("batch import exceeds the 500-row limit")
    entries: list[BatchImportEntry] = []
    issues: list[BatchImportIssue] = []
    seen: set[str] = set()
    for row_number, value in rows:
        _append_entry(
            entries,
            issues,
            seen,
            row_number=row_number,
            raw_url=value,
        )
    return BatchImportResult(tuple(entries), tuple(issues))


def _parse_csv(text: str) -> BatchImportResult:
    try:
        reader = csv.reader(StringIO(text), strict=True)
        rows = [
            (reader.line_num, row)
            for row in reader
            if any(value.strip() for value in row)
        ]
    except csv.Error as error:
        raise ValueError(f"CSV data is invalid: {error}") from error
    if not rows:
        return BatchImportResult((), ())

    first_headers = tuple(_normalized_header(value) for value in rows[0][1])
    known_headers = _URL_HEADERS | _TITLE_HEADERS | _ARTIST_HEADERS
    has_header = any(value in known_headers for value in first_headers)
    url_index = 0
    title_index: int | None = 1
    artist_index: int | None = 2
    data_rows = rows
    if has_header:
        url_index = next(
            (index for index, value in enumerate(first_headers) if value in _URL_HEADERS),
            -1,
        )
        if url_index < 0:
            raise ValueError("CSV header must include a URL column")
        title_index = next(
            (
                index
                for index, value in enumerate(first_headers)
                if value in _TITLE_HEADERS
            ),
            None,
        )
        artist_index = next(
            (
                index
                for index, value in enumerate(first_headers)
                if value in _ARTIST_HEADERS
            ),
            None,
        )
        data_rows = rows[1:]
    if len(data_rows) > MAX_BATCH_IMPORT_ENTRIES:
        raise ValueError("batch import exceeds the 500-row limit")

    entries: list[BatchImportEntry] = []
    issues: list[BatchImportIssue] = []
    seen: set[str] = set()
    for row_number, row in data_rows:
        raw_url = row[url_index] if url_index < len(row) else ""
        raw_title = (
            row[title_index]
            if title_index is not None and title_index < len(row)
            else ""
        )
        raw_artist = (
            row[artist_index]
            if artist_index is not None and artist_index < len(row)
            else ""
        )
        _append_entry(
            entries,
            issues,
            seen,
            row_number=row_number,
            raw_url=raw_url,
            raw_title=raw_title,
            raw_artist=raw_artist,
        )
    return BatchImportResult(tuple(entries), tuple(issues))


def parse_batch_import(path: Path) -> BatchImportResult:
    """Parse a small local UTF-8 TXT or CSV list without executing content."""

    candidate = Path(path)
    if candidate.suffix.casefold() not in {".txt", ".csv"}:
        raise ValueError("batch import must be a TXT or CSV file")
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("batch import file is missing or is a symbolic link")
    size = candidate.stat().st_size
    if size > MAX_BATCH_IMPORT_BYTES:
        raise ValueError("batch import file exceeds the 2 MiB limit")
    try:
        with candidate.open("rb") as source:
            payload = source.read(MAX_BATCH_IMPORT_BYTES + 1)
        if len(payload) > MAX_BATCH_IMPORT_BYTES:
            raise ValueError("batch import file exceeds the 2 MiB limit")
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("batch import file must use UTF-8") from error
    return _parse_txt(text) if candidate.suffix.casefold() == ".txt" else _parse_csv(text)


def build_import_requests(
    entries: tuple[BatchImportEntry, ...],
    *,
    output_dir: Path,
    priority: int,
    start_time: float | None,
    end_time: float | None,
    format_preset: str,
    subtitle_mode: str,
    subtitle_languages: tuple[str, ...],
    timed_comment_mode: str = "none",
    container_preset: str = "auto",
    provider_options: tuple[tuple[str, str], ...] = (),
) -> tuple[DownloadRequest, ...]:
    if not entries:
        raise ValueError("at least one imported entry must be selected")
    if len(entries) > MAX_BATCH_IMPORT_ENTRIES:
        raise ValueError("batch import selection is too large")
    if len({entry.url for entry in entries}) != len(entries):
        raise ValueError("batch import selection contains duplicate URLs")
    return tuple(
        DownloadRequest(
            entry.url,
            output_dir,
            priority=priority,
            start_time=start_time,
            end_time=end_time,
            source_title=entry.title,
            source_artist=entry.artist,
            source_category="batch-import",
            format_preset=format_preset,
            subtitle_mode=subtitle_mode,
            subtitle_languages=subtitle_languages,
            timed_comment_mode=timed_comment_mode,
            container_preset=container_preset,
            provider_options=provider_options,
        )
        for entry in entries
    )
