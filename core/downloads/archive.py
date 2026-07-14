"""Durable successful-download archive and canonical request keys."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.downloads.models import DownloadRequest

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_MAX_ARCHIVE_ENTRIES = 100_000
_MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
_ARCHIVE_KIND = "mediamanager-download-archive"


@dataclass(frozen=True, slots=True)
class ArchiveImportPreview:
    """Validated archive payload that can be reviewed before it is applied."""

    keys: tuple[str, ...]
    incoming_count: int
    new_count: int
    duplicate_count: int


class DuplicateDownloadError(RuntimeError):
    pass


class DownloadArchive:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._keys = self._load()

    @staticmethod
    def request_key(request: DownloadRequest) -> str:
        parsed = urlparse(request.url)
        host = (parsed.hostname or "").casefold()
        video_id = ""
        if host in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.strip("/").split("/", 1)[0]
        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = (parse_qs(parsed.query).get("v") or [""])[0]
            else:
                parts = [part for part in parsed.path.split("/") if part]
                if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
                    video_id = parts[1]
        if not _VIDEO_ID.fullmatch(video_id):
            normalized_url = parsed._replace(fragment="").geturl()
            source = "url:" + normalized_url
        else:
            source = "youtube:" + video_id
        identity = [request.start_time, request.end_time]
        if request.audio_only:
            identity.append("audio")
        if request.format_preset != "best":
            identity.append(f"format:{request.format_preset}")
        if request.subtitle_mode != "none":
            identity.append(
                {
                    "subtitles": request.subtitle_mode,
                    "languages": request.subtitle_languages,
                }
            )
        if request.timed_comment_mode != "none":
            identity.append(
                {
                    "timed_comments": request.timed_comment_mode,
                    "container": request.container_preset,
                }
            )
        segment = json.dumps(identity, separators=(",", ":"))
        return hashlib.sha256(f"{source}|{segment}".encode()).hexdigest()

    def contains(self, request: DownloadRequest) -> bool:
        with self._lock:
            return self.request_key(request) in self._keys

    def record(self, request: DownloadRequest) -> bool:
        key = self.request_key(request)
        with self._lock:
            if key in self._keys:
                return False
            if len(self._keys) >= _MAX_ARCHIVE_ENTRIES:
                raise RuntimeError("download archive entry limit reached")
            self._keys.add(key)
            self._save_locked()
        return True

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._keys)

    def export_file(self, target: Path) -> int:
        """Atomically export canonical IDs without exposing download URLs."""

        with self._lock:
            keys = tuple(sorted(self._keys))
        self._write_payload(target, keys, portable=True)
        return len(keys)

    def preview_import(self, source: Path) -> ArchiveImportPreview:
        keys = tuple(sorted(self._read_keys(source)))
        with self._lock:
            new_count = sum(key not in self._keys for key in keys)
        return ArchiveImportPreview(
            keys=keys,
            incoming_count=len(keys),
            new_count=new_count,
            duplicate_count=len(keys) - new_count,
        )

    def apply_import(self, preview: ArchiveImportPreview) -> int:
        """Merge a previously validated preview and persist it atomically."""

        if not isinstance(preview, ArchiveImportPreview):
            raise TypeError("archive import preview is invalid")
        with self._lock:
            additions = set(preview.keys) - self._keys
            if len(self._keys) + len(additions) > _MAX_ARCHIVE_ENTRIES:
                raise ValueError("download archive entry limit reached")
            if not additions:
                return 0
            previous = self._keys.copy()
            self._keys.update(additions)
            try:
                self._save_locked()
            except Exception:
                self._keys = previous
                raise
        return len(additions)

    def _load(self) -> set[str]:
        if self.path is None or not self.path.is_file():
            return set()
        try:
            return self._read_keys(self.path)
        except (OSError, ValueError, TypeError):
            return set()

    def _save_locked(self) -> None:
        if self.path is None:
            return
        self._write_payload(self.path, tuple(sorted(self._keys)), portable=False)

    @staticmethod
    def _valid_key(key: object) -> bool:
        return (
            isinstance(key, str)
            and len(key) == 64
            and all(char in "0123456789abcdef" for char in key)
        )

    @classmethod
    def _read_keys(cls, source: Path) -> set[str]:
        if not source.is_file():
            raise ValueError("download archive file does not exist")
        if source.stat().st_size > _MAX_ARCHIVE_BYTES:
            raise ValueError("download archive file is too large")
        raw = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("download archive payload is invalid")
        if set(raw) not in (
            {"schema_version", "keys"},
            {"schema_version", "kind", "keys"},
        ):
            raise ValueError("download archive fields are invalid")
        if "kind" in raw and raw["kind"] != _ARCHIVE_KIND:
            raise ValueError("download archive kind is invalid")
        keys = raw.get("keys")
        if (
            raw.get("schema_version") != 1
            or not isinstance(keys, list)
            or len(keys) > _MAX_ARCHIVE_ENTRIES
            or not all(cls._valid_key(key) for key in keys)
            or len(set(keys)) != len(keys)
        ):
            raise ValueError("download archive keys are invalid")
        return set(keys)

    @staticmethod
    def _write_payload(
        target: Path, keys: tuple[str, ...], *, portable: bool
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        payload: dict[str, object] = {"schema_version": 1, "keys": keys}
        if portable:
            payload["kind"] = _ARCHIVE_KIND
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary.replace(target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
