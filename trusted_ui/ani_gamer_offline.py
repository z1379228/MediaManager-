"""Safe, explicit offline records for selected AniGamer episodes.

This module never resolves or downloads AniGamer streams.  It stores bounded
public metadata, an already-decoded cover image, and—only after an explicit
file selection—a copy of media the user already has locally.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from contracts.discovery_v1 import DiscoveryItemV1
from core.site_routing import classify_site_url


OFFLINE_SCHEMA = 1
MAX_COVER_BYTES = 2 * 1024 * 1024
MAX_LOCAL_MEDIA_BYTES = 64 * 1024**3
ALLOWED_LOCAL_MEDIA_SUFFIXES = frozenset(
    {
        ".avi",
        ".flac",
        ".m4a",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp3",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".ogg",
        ".opus",
        ".ts",
        ".wav",
        ".webm",
    }
)
_WINDOWS_RESERVED_NAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_UNSAFE_COMPONENT = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")


class OfflineImportCancelled(RuntimeError):
    """Raised after an explicit local-media import cancellation."""


@dataclass(frozen=True, slots=True)
class AniGamerEpisodeArchive:
    root: Path
    metadata: Path
    cover: Path | None
    local_media: Path | None = None


@dataclass(frozen=True, slots=True)
class AniGamerArchiveVerification:
    root: Path
    valid: bool
    media_state: str
    media_path: Path | None
    expected_bytes: int | None = None
    actual_bytes: int | None = None
    expected_sha256: str = ""
    actual_sha256: str = ""


def _safe_component(value: str, fallback: str, *, limit: int = 96) -> str:
    normalized = " ".join(str(value).split())
    normalized = _UNSAFE_COMPONENT.sub("_", normalized).strip(" ._")
    if not normalized:
        normalized = fallback
    if normalized.casefold() in _WINDOWS_RESERVED_NAMES:
        normalized = f"_{normalized}"
    return normalized[:limit].rstrip(" ._") or fallback


def _validated_item(item: DiscoveryItemV1, resource_kind: str) -> None:
    if not isinstance(item, DiscoveryItemV1):
        raise TypeError("AniGamer offline item type is invalid")
    route = classify_site_url(item.url)
    if (
        route is None
        or route.site_family != "ani-gamer"
        or route.resource_kind != resource_kind
    ):
        raise ValueError(f"AniGamer {resource_kind} URL is invalid")


def _prepare_directory(path: Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.exists() and (candidate.is_symlink() or not candidate.is_dir()):
        raise ValueError("AniGamer offline destination is unsafe")
    candidate.mkdir(parents=True, exist_ok=True)
    resolved = candidate.resolve()
    if resolved.is_symlink() or not resolved.is_dir():
        raise ValueError("AniGamer offline destination is unsafe")
    return resolved


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(payload)
            output.flush()
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_metadata(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
        raise ValueError("AniGamer offline metadata is missing or unsafe")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError("AniGamer offline metadata is invalid") from error
    if (
        not isinstance(document, dict)
        or document.get("schema") != OFFLINE_SCHEMA
        or document.get("kind") != "ani-gamer-selected-episode"
        or not isinstance(document.get("series"), dict)
        or not isinstance(document.get("episode"), dict)
    ):
        raise ValueError("AniGamer offline metadata contract is invalid")
    return document


def create_episode_archive(
    destination: Path,
    series: DiscoveryItemV1,
    episode: DiscoveryItemV1,
    *,
    cover_png: bytes | None = None,
) -> AniGamerEpisodeArchive:
    """Atomically save one explicitly selected episode record and optional cover."""

    _validated_item(series, "series")
    _validated_item(episode, "episode")
    if cover_png is not None and (
        not isinstance(cover_png, bytes)
        or not cover_png.startswith(b"\x89PNG\r\n\x1a\n")
        or len(cover_png) > MAX_COVER_BYTES
    ):
        raise ValueError("AniGamer cover PNG is invalid or too large")

    output = _prepare_directory(destination)
    series_name = _safe_component(
        f"{series.title}-{series.video_id}", "ani-gamer-series"
    )
    episode_name = _safe_component(
        f"{episode.title}-{episode.video_id}", "ani-gamer-episode"
    )
    series_root = _prepare_directory(output / series_name)
    episode_root = _prepare_directory(series_root / episode_name)
    if not episode_root.is_relative_to(output):
        raise ValueError("AniGamer offline path escaped its destination")

    metadata_path = episode_root / "episode.json"
    existing_media: object = None
    if metadata_path.exists():
        existing_media = _read_metadata(metadata_path).get("local_media")

    cover_path: Path | None = None
    if cover_png is not None:
        cover_path = episode_root / "cover.png"
        if cover_path.is_symlink():
            raise ValueError("AniGamer cover output is unsafe")
        _atomic_write(cover_path, cover_png)
    elif (episode_root / "cover.png").is_file():
        cover_path = episode_root / "cover.png"

    document = {
        "schema": OFFLINE_SCHEMA,
        "kind": "ani-gamer-selected-episode",
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "boundary": "public-metadata-cover-and-user-local-media-only",
        "series": {
            "id": series.video_id,
            "title": series.title,
            "official_url": series.url,
            "thumbnail_url": series.thumbnail_url,
        },
        "episode": {
            "id": episode.video_id,
            "title": episode.title,
            "official_url": episode.url,
        },
        "cover": cover_path.name if cover_path is not None else None,
        "local_media": existing_media,
    }
    encoded = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    if len(encoded) > 64 * 1024:
        raise ValueError("AniGamer offline metadata is too large")
    if metadata_path.is_symlink():
        raise ValueError("AniGamer metadata output is unsafe")
    _atomic_write(metadata_path, encoded)
    return AniGamerEpisodeArchive(episode_root, metadata_path, cover_path)


def import_local_media(
    archive_root: Path,
    source: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> AniGamerEpisodeArchive:
    """Copy explicitly selected local media into an existing episode archive."""

    root = Path(archive_root).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("AniGamer episode archive is unsafe")
    metadata_path = root / "episode.json"
    document = _read_metadata(metadata_path)
    candidate = Path(source).expanduser()
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("selected local media is missing or unsafe")
    candidate = candidate.resolve()
    suffix = candidate.suffix.casefold()
    initial = candidate.stat()
    if (
        suffix not in ALLOWED_LOCAL_MEDIA_SUFFIXES
        or initial.st_size <= 0
        or initial.st_size > MAX_LOCAL_MEDIA_BYTES
    ):
        raise ValueError("selected local media type or size is unsupported")

    media_root = _prepare_directory(root / "media")
    if not media_root.is_relative_to(root):
        raise ValueError("AniGamer local media path escaped its archive")
    base_name = _safe_component(candidate.stem, "episode-media", limit=80)
    target = media_root / f"{base_name}{suffix}"
    counter = 2
    while target.exists():
        target = media_root / f"{base_name}-{counter:02d}{suffix}"
        counter += 1
        if counter > 999:
            raise ValueError("AniGamer local media destination is full")
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.part")
    digest = hashlib.sha256()
    written = 0
    try:
        with candidate.open("rb") as input_file, temporary.open("xb") as output_file:
            while chunk := input_file.read(1024 * 1024):
                if cancelled is not None and cancelled():
                    raise OfflineImportCancelled("local media import cancelled")
                written += len(chunk)
                if written > initial.st_size or written > MAX_LOCAL_MEDIA_BYTES:
                    raise ValueError("selected local media changed during import")
                digest.update(chunk)
                output_file.write(chunk)
            output_file.flush()
        final = candidate.stat()
        if (
            written != initial.st_size
            or final.st_size != initial.st_size
            or final.st_mtime_ns != initial.st_mtime_ns
        ):
            raise ValueError("selected local media changed during import")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)

    document["local_media"] = {
        "path": target.relative_to(root).as_posix(),
        "bytes": written,
        "sha256": digest.hexdigest(),
        "source_name": candidate.name,
    }
    encoded = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    try:
        _atomic_write(metadata_path, encoded)
    except OSError:
        target.unlink(missing_ok=True)
        raise
    cover = root / "cover.png"
    return AniGamerEpisodeArchive(
        root,
        metadata_path,
        cover if cover.is_file() and not cover.is_symlink() else None,
        target,
    )


def verify_episode_archive(
    archive_root: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> AniGamerArchiveVerification:
    """Verify one archive and its optional local media without network access."""

    candidate = Path(archive_root).expanduser()
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("AniGamer episode archive is unsafe")
    root = candidate.resolve()
    document = _read_metadata(root / "episode.json")
    local_media = document.get("local_media")
    if local_media is None:
        return AniGamerArchiveVerification(root, True, "not-linked", None)
    if not isinstance(local_media, dict):
        raise ValueError("AniGamer local media metadata is invalid")
    raw_path = local_media.get("path")
    expected_bytes = local_media.get("bytes")
    expected_sha256 = local_media.get("sha256")
    if (
        not isinstance(raw_path, str)
        or not raw_path
        or "\\" in raw_path
        or Path(raw_path).is_absolute()
        or ".." in Path(raw_path).parts
        or not isinstance(expected_bytes, int)
        or isinstance(expected_bytes, bool)
        or not 0 < expected_bytes <= MAX_LOCAL_MEDIA_BYTES
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        raise ValueError("AniGamer local media metadata is invalid")
    media_path = root.joinpath(*raw_path.split("/"))
    resolved_media = media_path.resolve()
    if not resolved_media.is_relative_to(root):
        raise ValueError("AniGamer local media path escaped its archive")
    if media_path.is_symlink() or not media_path.is_file():
        return AniGamerArchiveVerification(
            root,
            False,
            "missing",
            media_path,
            expected_bytes,
            None,
            expected_sha256,
        )
    initial = media_path.stat()
    if initial.st_size != expected_bytes:
        return AniGamerArchiveVerification(
            root,
            False,
            "size-mismatch",
            media_path,
            expected_bytes,
            initial.st_size,
            expected_sha256,
        )
    digest = hashlib.sha256()
    read_bytes = 0
    with media_path.open("rb") as input_file:
        while chunk := input_file.read(1024 * 1024):
            if cancelled is not None and cancelled():
                raise OfflineImportCancelled("offline archive verification cancelled")
            read_bytes += len(chunk)
            if read_bytes > expected_bytes:
                raise ValueError("AniGamer local media changed during verification")
            digest.update(chunk)
    final = media_path.stat()
    if final.st_size != initial.st_size or final.st_mtime_ns != initial.st_mtime_ns:
        raise ValueError("AniGamer local media changed during verification")
    actual_sha256 = digest.hexdigest()
    valid = actual_sha256 == expected_sha256
    return AniGamerArchiveVerification(
        root,
        valid,
        "ok" if valid else "hash-mismatch",
        media_path,
        expected_bytes,
        read_bytes,
        expected_sha256,
        actual_sha256,
    )
