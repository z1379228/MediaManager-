"""SQLite-backed local media library with conservative filesystem operations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import time
import uuid

from core.library.models import DuplicateGroup, LibraryItem, MovePlan, PlaylistPreview
from core.media_library import scan_media

MAX_PLAYLIST_BYTES = 2 * 1024 * 1024
MAX_PLAYLIST_ENTRIES = 5_000
FINGERPRINT_CHUNK = 1024 * 1024
ARTWORK_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _resolved(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


class ArtworkCache:
    """Bounded cache for user-selected local artwork copies."""

    def __init__(
        self,
        root: Path,
        *,
        max_bytes: int = 256 * 1024 * 1024,
        max_source_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        if max_bytes < 1 or max_source_bytes < 1:
            raise ValueError("artwork limits must be positive")
        self.root = _resolved(root)
        self.max_bytes = max_bytes
        self.max_source_bytes = max_source_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, source: Path) -> Path:
        source = _resolved(source)
        if (
            source.suffix.lower() not in ARTWORK_EXTENSIONS
            or source.is_symlink()
            or not source.is_file()
        ):
            raise ValueError("artwork must be a supported regular image file")
        size = source.stat().st_size
        if size > self.max_source_bytes or size > self.max_bytes:
            raise ValueError("artwork exceeds the source size limit")
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(256 * 1024), b""):
                digest.update(chunk)
        target = self.root / f"{digest.hexdigest()}{source.suffix.lower()}"
        if not target.exists():
            temporary = self.root / f".{target.name}.{uuid.uuid4().hex}.tmp"
            try:
                shutil.copyfile(source, temporary)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        os.utime(target, None)
        self._evict(protect=target)
        return target

    def _evict(self, *, protect: Path) -> None:
        files = [
            item
            for item in self.root.iterdir()
            if item.is_file() and not item.is_symlink() and not item.name.startswith(".")
        ]
        total = sum(item.stat().st_size for item in files)
        for item in sorted(files, key=lambda path: path.stat().st_mtime):
            if total <= self.max_bytes:
                return
            if item == protect:
                continue
            size = item.stat().st_size
            item.unlink(missing_ok=True)
            total -= size


class LibraryService:
    """Owns the persistent library index; it never rewrites media-file tags."""

    def __init__(self, database: Path, artwork_root: Path) -> None:
        self.database = _resolved(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.artwork = ArtworkCache(artwork_root)
        self._lock = threading.RLock()
        self._closed = False
        self._connection = sqlite3.connect(self.database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    media_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    modified REAL NOT NULL,
                    available INTEGER NOT NULL DEFAULT 1,
                    fingerprint TEXT,
                    title TEXT NOT NULL DEFAULT '',
                    artist TEXT NOT NULL DEFAULT '',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    play_count INTEGER NOT NULL DEFAULT 0,
                    last_played REAL,
                    artwork_path TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_items_size ON items(size);
                CREATE INDEX IF NOT EXISTS idx_items_fingerprint ON items(fingerprint);
                CREATE TABLE IF NOT EXISTS roots (
                    path TEXT PRIMARY KEY,
                    recursive INTEGER NOT NULL DEFAULT 1,
                    last_scan REAL
                );
                CREATE TABLE IF NOT EXISTS playlists (
                    playlist_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    query_json TEXT,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS playlist_items (
                    playlist_id TEXT NOT NULL REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                    item_id TEXT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (playlist_id, position)
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def scan(self, root: Path, *, limit: int = 50_000) -> tuple[LibraryItem, ...]:
        root = _resolved(root)
        discovered = scan_media(root, limit=limit)
        now = time.time()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO roots(path, recursive, last_scan) VALUES(?, 1, ?) "
                "ON CONFLICT(path) DO UPDATE SET last_scan=excluded.last_scan",
                (str(root), now),
            )
            rows = self._connection.execute(
                "SELECT item_id, path FROM items WHERE available=1"
            ).fetchall()
            unavailable = [row["item_id"] for row in rows if _is_within(Path(row["path"]), root)]
            self._connection.executemany(
                "UPDATE items SET available=0 WHERE item_id=?",
                ((item_id,) for item_id in unavailable),
            )
            for media in discovered:
                existing = self._connection.execute(
                    "SELECT item_id, size, modified FROM items WHERE path=?",
                    (str(media.path),),
                ).fetchone()
                if existing is None:
                    self._connection.execute(
                        "INSERT INTO items(item_id,path,media_type,size,modified,available) "
                        "VALUES(?,?,?,?,?,1)",
                        (
                            uuid.uuid4().hex,
                            str(media.path),
                            media.media_type,
                            media.size,
                            media.modified,
                        ),
                    )
                else:
                    changed = (
                        existing["size"] != media.size
                        or existing["modified"] != media.modified
                    )
                    self._connection.execute(
                        "UPDATE items SET media_type=?,size=?,modified=?,available=1,"
                        "fingerprint=CASE WHEN ? THEN NULL ELSE fingerprint END WHERE item_id=?",
                        (
                            media.media_type,
                            media.size,
                            media.modified,
                            int(changed),
                            existing["item_id"],
                        ),
                    )
        return self.search(root=root)

    def roots(self) -> tuple[Path, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT path FROM roots ORDER BY path COLLATE NOCASE"
            ).fetchall()
        return tuple(Path(row["path"]) for row in rows)

    def search(
        self,
        query: str = "",
        *,
        media_type: str | None = None,
        tags: Iterable[str] = (),
        available_only: bool = True,
        root: Path | None = None,
    ) -> tuple[LibraryItem, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM items ORDER BY title COLLATE NOCASE, path COLLATE NOCASE"
            ).fetchall()
        wanted = {tag.strip().casefold() for tag in tags if tag.strip()}
        needle = query.strip().casefold()
        root = _resolved(root) if root is not None else None
        items: list[LibraryItem] = []
        for row in rows:
            item = self._row_item(row)
            if available_only and not item.available:
                continue
            if root is not None and not _is_within(item.path, root):
                continue
            if media_type and item.media_type != media_type:
                continue
            item_tags = {tag.casefold() for tag in item.tags}
            if wanted and not wanted.issubset(item_tags):
                continue
            searchable = " ".join(
                (item.name, item.title, item.artist, " ".join(item.tags))
            ).casefold()
            if needle and needle not in searchable:
                continue
            items.append(item)
        return tuple(items)

    def get(self, item_id: str) -> LibraryItem:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM items WHERE item_id=?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._row_item(row)

    def update_metadata(
        self,
        item_id: str,
        *,
        title: str = "",
        artist: str = "",
        tags: Iterable[str] = (),
    ) -> LibraryItem:
        title = self._clean_text(title, "title", 300)
        artist = self._clean_text(artist, "artist", 300)
        normalized_tags = tuple(
            dict.fromkeys(
                self._clean_text(tag, "tag", 80)
                for tag in tags
                if str(tag).strip()
            )
        )
        if len(normalized_tags) > 64:
            raise ValueError("too many library tags")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE items SET title=?,artist=?,tags_json=? WHERE item_id=?",
                (title, artist, json.dumps(normalized_tags, ensure_ascii=False), item_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)
        return self.get(item_id)

    def record_play(self, item_id: str, *, played_at: float | None = None) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE items SET play_count=play_count+1,last_played=? WHERE item_id=?",
                (played_at if played_at is not None else time.time(), item_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)

    def set_artwork(self, item_id: str, source: Path) -> Path:
        cached = self.artwork.store(source)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE items SET artwork_path=? WHERE item_id=?",
                (str(cached), item_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)
        return cached

    def duplicate_groups(self) -> tuple[DuplicateGroup, ...]:
        candidates: dict[int, list[LibraryItem]] = defaultdict(list)
        for item in self.search():
            candidates[item.size].append(item)
        for same_size in candidates.values():
            if len(same_size) < 2:
                continue
            for item in same_size:
                fingerprint = item.fingerprint or self._fingerprint(item.path, item.size)
                if item.fingerprint != fingerprint:
                    with self._lock, self._connection:
                        self._connection.execute(
                            "UPDATE items SET fingerprint=? WHERE item_id=?",
                            (fingerprint, item.item_id),
                        )
        grouped: dict[str, list[LibraryItem]] = defaultdict(list)
        for item in self.search():
            if item.fingerprint:
                grouped[item.fingerprint].append(item)
        return tuple(
            DuplicateGroup(fingerprint, items[0].size, tuple(items))
            for fingerprint, items in sorted(grouped.items())
            if len(items) > 1
        )

    def create_playlist(
        self,
        name: str,
        item_ids: Iterable[str] = (),
        *,
        query: Mapping[str, object] | None = None,
    ) -> str:
        name = self._clean_text(name, "playlist name", 200)
        if not name:
            raise ValueError("playlist name is required")
        ids = tuple(dict.fromkeys(item_ids))
        if len(ids) > MAX_PLAYLIST_ENTRIES:
            raise ValueError("playlist entry limit exceeded")
        if query is not None and ids:
            raise ValueError("smart playlists cannot include fixed entries")
        allowed_query = {"query", "media_type", "tags", "available_only"}
        if query is not None and not set(query).issubset(allowed_query):
            raise ValueError("unsupported smart playlist query")
        playlist_id = uuid.uuid4().hex
        query_json = json.dumps(query, ensure_ascii=False) if query is not None else None
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO playlists(playlist_id,name,query_json,created_at) VALUES(?,?,?,?)",
                (playlist_id, name, query_json, time.time()),
            )
            for position, item_id in enumerate(ids):
                if self._connection.execute(
                    "SELECT 1 FROM items WHERE item_id=?", (item_id,)
                ).fetchone() is None:
                    raise KeyError(item_id)
                self._connection.execute(
                    "INSERT INTO playlist_items(playlist_id,item_id,position) VALUES(?,?,?)",
                    (playlist_id, item_id, position),
                )
        return playlist_id

    def playlists(self) -> tuple[tuple[str, str, bool], ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT playlist_id,name,query_json FROM playlists ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return tuple((row["playlist_id"], row["name"], row["query_json"] is not None) for row in rows)

    def playlist_items(self, playlist_id: str) -> tuple[LibraryItem, ...]:
        with self._lock:
            playlist = self._connection.execute(
                "SELECT query_json FROM playlists WHERE playlist_id=?", (playlist_id,)
            ).fetchone()
            if playlist is None:
                raise KeyError(playlist_id)
            if playlist["query_json"] is None:
                rows = self._connection.execute(
                    "SELECT i.* FROM playlist_items p JOIN items i ON i.item_id=p.item_id "
                    "WHERE p.playlist_id=? ORDER BY p.position",
                    (playlist_id,),
                ).fetchall()
                return tuple(self._row_item(row) for row in rows)
            query = json.loads(playlist["query_json"])
        return self.search(
            str(query.get("query", "")),
            media_type=query.get("media_type") or None,
            tags=query.get("tags", ()),
            available_only=bool(query.get("available_only", True)),
        )

    def preview_playlist_import(self, source: Path) -> PlaylistPreview:
        source = _resolved(source)
        if source.is_symlink() or not source.is_file():
            raise ValueError("playlist must be a regular file")
        if source.stat().st_size > MAX_PLAYLIST_BYTES:
            raise ValueError("playlist file exceeds the size limit")
        raw = source.read_text(encoding="utf-8-sig")
        if source.suffix.lower() == ".json":
            document = json.loads(raw)
            if not isinstance(document, dict) or document.get("schema_version") != 1:
                raise ValueError("unsupported library playlist schema")
            name = self._clean_text(str(document.get("name", source.stem)), "playlist name", 200)
            entries = document.get("paths")
            if not isinstance(entries, list) or not all(isinstance(path, str) for path in entries):
                raise ValueError("library playlist paths are invalid")
            source_format = "json"
        else:
            name = source.stem
            entries = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]
            source_format = "m3u"
        if len(entries) > MAX_PLAYLIST_ENTRIES:
            raise ValueError("playlist entry limit exceeded")
        paths: list[Path] = []
        duplicates: list[Path] = []
        seen: set[str] = set()
        for value in entries:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = source.parent / candidate
            candidate = _resolved(candidate)
            key = os.path.normcase(str(candidate))
            if key in seen:
                duplicates.append(candidate)
                continue
            seen.add(key)
            paths.append(candidate)
        indexed = {os.path.normcase(str(item.path)): item for item in self.search(available_only=False)}
        missing = tuple(path for path in paths if os.path.normcase(str(path)) not in indexed or not indexed[os.path.normcase(str(path))].available)
        return PlaylistPreview(name, tuple(paths), missing, tuple(duplicates), source_format)

    def apply_playlist_import(self, preview: PlaylistPreview) -> str:
        indexed = {os.path.normcase(str(item.path)): item for item in self.search()}
        item_ids = [indexed[os.path.normcase(str(path))].item_id for path in preview.paths if os.path.normcase(str(path)) in indexed]
        return self.create_playlist(preview.name, item_ids)

    def export_playlist(self, playlist_id: str, destination: Path) -> Path:
        destination = _resolved(destination)
        items = self.playlist_items(playlist_id)
        with self._lock:
            row = self._connection.execute(
                "SELECT name FROM playlists WHERE playlist_id=?", (playlist_id,)
            ).fetchone()
        if row is None:
            raise KeyError(playlist_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            if destination.suffix.lower() == ".json":
                payload = {
                    "schema_version": 1,
                    "name": row["name"],
                    "paths": [str(item.path) for item in items],
                }
                temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                temporary.write_text("#EXTM3U\n" + "\n".join(str(item.path) for item in items) + "\n", encoding="utf-8")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    def preview_move(self, item_id: str, target: Path) -> MovePlan:
        item = self.get(item_id)
        target = _resolved(target)
        if not item.available or item.path.is_symlink() or not item.path.is_file():
            raise ValueError("source media is not an available regular file")
        if target.suffix.casefold() != item.path.suffix.casefold():
            raise ValueError("move must preserve the media file extension")
        if target == item.path:
            raise ValueError("source and target are the same")
        if target.exists():
            raise FileExistsError(target)
        if not target.parent.is_dir() or target.parent.is_symlink():
            raise ValueError("target folder must already exist and be a regular folder")
        if item.path.drive.casefold() != target.drive.casefold():
            raise ValueError("cross-volume moves are not supported")
        return MovePlan(item_id, item.path, target, item.size, item.modified)

    def apply_move(self, plan: MovePlan) -> LibraryItem:
        current = self.get(plan.item_id)
        if current.path != plan.source or not current.path.is_file() or current.path.is_symlink():
            raise ValueError("move source changed after preview")
        stat = current.path.stat()
        if stat.st_size != plan.size or stat.st_mtime != plan.modified:
            raise ValueError("move source changed after preview")
        if plan.target.exists():
            raise FileExistsError(plan.target)
        plan.source.rename(plan.target)
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    "UPDATE items SET path=?,modified=? WHERE item_id=?",
                    (str(plan.target), plan.target.stat().st_mtime, plan.item_id),
                )
        except Exception:
            if not plan.source.exists() and plan.target.exists():
                plan.target.rename(plan.source)
            raise
        return self.get(plan.item_id)

    @staticmethod
    def _fingerprint(path: Path, size: int) -> str:
        if path.is_symlink() or not path.is_file():
            raise ValueError("cannot fingerprint unavailable media")
        digest = hashlib.sha256(str(size).encode("ascii"))
        with path.open("rb") as stream:
            digest.update(stream.read(FINGERPRINT_CHUNK))
            if size > FINGERPRINT_CHUNK:
                stream.seek(max(0, size - FINGERPRINT_CHUNK))
                digest.update(stream.read(FINGERPRINT_CHUNK))
        return digest.hexdigest()

    @staticmethod
    def _clean_text(value: object, field: str, maximum: int) -> str:
        text = str(value).strip()
        if any(ord(character) < 32 and character not in "\t" for character in text):
            raise ValueError(f"{field} contains control characters")
        if len(text) > maximum:
            raise ValueError(f"{field} is too long")
        return text

    @staticmethod
    def _row_item(row: sqlite3.Row) -> LibraryItem:
        try:
            tags_document = json.loads(row["tags_json"])
            tags = tuple(str(tag) for tag in tags_document if isinstance(tag, str))
        except (json.JSONDecodeError, TypeError):
            tags = ()
        artwork = Path(row["artwork_path"]) if row["artwork_path"] else None
        return LibraryItem(
            item_id=row["item_id"],
            path=Path(row["path"]),
            media_type=row["media_type"],
            size=int(row["size"]),
            modified=float(row["modified"]),
            available=bool(row["available"]),
            fingerprint=row["fingerprint"],
            title=row["title"],
            artist=row["artist"],
            tags=tags,
            play_count=int(row["play_count"]),
            last_played=float(row["last_played"]) if row["last_played"] is not None else None,
            artwork_path=artwork,
        )
