"""Create a deterministic, self-contained ZIP from one audited staged release.

This tool does not build an executable, alter a staged release, sign content, or
publish to GitHub.  Its only input is an immutable ``Version`` release folder
that already passes :func:`tools.audit_versions.audit_version`.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from uuid import uuid4
import zipfile

from tools.audit_versions import audit_version
from tools.audit_staged_runtime import audit_staged_runtime


_RELEASE_VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
_REVISION_PATTERN = re.compile(r"^r[1-9][0-9]*$")
_SOURCE_REVISION_PATTERN = re.compile(
    r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"
)
_RELEASE_TRACKS = frozenset({"Development", "Testing", "Stable"})
_RUNTIME_DATA_PARTS = frozenset(
    {
        "cache",
        "downloads",
        "logs",
        "settings",
        "temp",
        "userdata",
    }
)
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_JSON_LIMIT = 64 * 1024
_SENSITIVE_FILENAMES = frozenset(
    {
        ".env",
        "cookie.txt",
        "cookies.txt",
        "cookies.json",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "id_xmss",
        "secrets.json",
    }
)
_SENSITIVE_SUFFIXES = frozenset(
    {".jks", ".key", ".keystore", ".p12", ".pfx", ".ppk"}
)
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)
_WINDOWS_RESERVED_BASE_NAMES = frozenset(
    {
        "aux",
        "con",
        "conin$",
        "conout$",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
        "com¹",
        "com²",
        "com³",
        "lpt¹",
        "lpt²",
        "lpt³",
    }
)
_WINDOWS_UNSAFE_CHARACTERS = frozenset('<>:"/\\|?*')


@dataclass(frozen=True, slots=True)
class SelfContainedZipPackage:
    archive: str
    checksum: str
    sha256: str
    top_level: str
    files: int
    bytes: int
    source_revision: str


@dataclass(frozen=True, slots=True)
class _ReleaseFile:
    relative: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class _PublishedFileIdentity:
    device: int
    inode: int
    size: int


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _is_linklike(path: Path) -> bool:
    """Return whether *path* is a symlink, junction, or Windows reparse point."""

    metadata = os.lstat(path)
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    is_junction = getattr(path, "is_junction", None)
    return (
        path.is_symlink()
        or bool(attributes & reparse)
        or bool(is_junction is not None and is_junction())
    )


def _load_release_info(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        payload = stream.read(_JSON_LIMIT + 1)
    if len(payload) > _JSON_LIMIT:
        raise ValueError("release-info.json exceeds the size limit")

    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        document: dict[str, object] = {}
        for key, value in pairs:
            if key in document:
                raise ValueError(f"duplicate release-info key: {key}")
            document[key] = value
        return document

    document = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(document, dict):
        raise ValueError("release-info.json root must be an object")
    return document


def _archive_stem(
    info: dict[str, object],
    revision: str | None,
) -> str:
    track = info.get("release_track")
    version = info.get("release_version")
    if track not in _RELEASE_TRACKS:
        raise ValueError("release-info.json has an unsupported release track")
    if (
        not isinstance(version, str)
        or _RELEASE_VERSION_PATTERN.fullmatch(version) is None
    ):
        raise ValueError("release-info.json has an invalid release version")
    suffix = ""
    if revision is not None:
        if _REVISION_PATTERN.fullmatch(revision) is None:
            raise ValueError("revision must match r[1-9][0-9]*")
        suffix = f"-{revision}"
    stem = f"MediaManager-{track}-{version}{suffix}"
    _validate_windows_component(stem, label="archive stem")
    return stem


def _validate_source_revision(
    info: dict[str, object],
    expected: str,
) -> str:
    if _SOURCE_REVISION_PATTERN.fullmatch(expected) is None:
        raise ValueError(
            "expected source revision must be 40 or 64 lowercase hex characters"
        )
    actual = info.get("source_revision")
    if actual != expected:
        raise ValueError(
            "release-info.json source revision does not match the expected "
            "source freeze"
        )
    return expected


def _validate_windows_component(value: str, *, label: str) -> None:
    try:
        utf16_units = len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} is not valid Unicode") from error
    if (
        not value
        or value in {".", ".."}
        or value.endswith((".", " "))
        or utf16_units > 255
        or any(
            ord(character) < 32
            or character in _WINDOWS_UNSAFE_CHARACTERS
            for character in value
        )
        or value.split(".", 1)[0].casefold()
        in _WINDOWS_RESERVED_BASE_NAMES
    ):
        raise ValueError(
            f"{label} is not a Windows-safe path component"
        )


def _contains_private_key_marker(path: Path) -> bool:
    overlap = max(len(marker) for marker in _PRIVATE_KEY_MARKERS) - 1
    tail = b""
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            window = tail + chunk
            if any(marker in window for marker in _PRIVATE_KEY_MARKERS):
                return True
            tail = window[-overlap:]
    return False


def _validate_windows_relative_paths(
    relatives: Iterable[PurePosixPath],
) -> None:
    folded_paths: dict[str, str] = {}
    for relative in relatives:
        display = relative.as_posix()
        for component in relative.parts:
            _validate_windows_component(
                component,
                label=f"release path {display}",
            )
        folded_relative = display.casefold()
        previous = folded_paths.setdefault(folded_relative, display)
        if previous != display:
            raise ValueError(
                "case-insensitive release path collision: "
                f"{previous} and {display}"
            )


def _safe_release_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir() or _is_linklike(root):
        raise ValueError("staged release folder is missing or link-like")
    resolved_root = root.resolve(strict=True)
    entries = tuple(root.rglob("*"))
    _validate_windows_relative_paths(
        PurePosixPath(*path.relative_to(root).parts) for path in entries
    )
    files: list[Path] = []
    for path in entries:
        relative = path.relative_to(root)
        if _is_linklike(path):
            raise ValueError(
                f"link-like release entry is not allowed: {relative.as_posix()}"
            )
        if any(part.casefold() in _RUNTIME_DATA_PARTS for part in relative.parts):
            raise ValueError(
                f"runtime or user data is not allowed: {relative.as_posix()}"
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(
                f"non-regular release entry is not allowed: {relative.as_posix()}"
            )
        if not path.resolve(strict=True).is_relative_to(resolved_root):
            raise ValueError(
                f"release entry escapes the staged folder: {relative.as_posix()}"
            )
        folded_name = path.name.casefold()
        if (
            folded_name in _SENSITIVE_FILENAMES
            or path.suffix.casefold() in _SENSITIVE_SUFFIXES
        ):
            raise ValueError(
                f"sensitive file is not allowed: {relative.as_posix()}"
            )
        if (
            path.suffix.casefold() == ".pem"
            and _contains_private_key_marker(path)
        ):
            raise ValueError(
                f"private key is not allowed: {relative.as_posix()}"
            )
        files.append(path)
    return tuple(
        sorted(files, key=lambda item: item.relative_to(root).as_posix())
    )


def _snapshot_release_files(root: Path) -> tuple[_ReleaseFile, ...]:
    snapshot: list[_ReleaseFile] = []
    for path in _safe_release_files(root):
        before = path.stat()
        digest = _sha256(path)
        after = path.stat()
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError(
                "staged release changed while its file snapshot was read: "
                f"{path.relative_to(root).as_posix()}"
            )
        snapshot.append(
            _ReleaseFile(
                relative=path.relative_to(root).as_posix(),
                sha256=digest,
                size=after.st_size,
            )
        )
    return tuple(snapshot)


def _prepare_output_directory(output_dir: Path, release_root: Path) -> Path:
    resolved_release = release_root.resolve(strict=True)
    prospective_output = output_dir.resolve(strict=False)
    if (
        prospective_output == resolved_release
        or prospective_output.is_relative_to(resolved_release)
        or resolved_release.is_relative_to(prospective_output)
    ):
        raise ValueError(
            "output directory must not overlap the staged release"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir() or _is_linklike(output_dir):
        raise ValueError("output directory is missing or link-like")
    resolved_output = output_dir.resolve(strict=True)
    if (
        resolved_output == resolved_release
        or resolved_output.is_relative_to(resolved_release)
        or resolved_release.is_relative_to(resolved_output)
    ):
        raise ValueError(
            "output directory must not overlap the staged release"
        )
    return resolved_output


def _write_zip(
    archive_path: Path,
    *,
    release_root: Path,
    files: tuple[_ReleaseFile, ...],
    top_level: str,
) -> None:
    with zipfile.ZipFile(
        archive_path,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for file in files:
            relative = PurePosixPath(file.relative)
            path = release_root.joinpath(*relative.parts)
            entry_name = PurePosixPath(top_level, relative).as_posix()
            if len(entry_name.encode("utf-8")) > 65_535:
                raise ValueError(
                    f"ZIP entry name exceeds the format limit: {file.relative}"
                )
            entry = zipfile.ZipInfo(
                entry_name,
                date_time=_FIXED_ZIP_TIMESTAMP,
            )
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.compress_level = 9
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.flag_bits |= 0x800
            with path.open("rb") as source, archive.open(
                entry,
                mode="w",
                force_zip64=True,
            ) as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)


def _verify_zip(
    archive_path: Path,
    *,
    files: tuple[_ReleaseFile, ...],
    top_level: str,
) -> None:
    expected = tuple(
        PurePosixPath(top_level, file.relative).as_posix()
        for file in files
    )
    with zipfile.ZipFile(archive_path, mode="r") as archive:
        names = tuple(info.filename for info in archive.infolist())
        if names != expected or len(names) != len(set(names)):
            raise ValueError("ZIP entries do not exactly match the staged release")
        for name in names:
            relative = PurePosixPath(name)
            if (
                relative.is_absolute()
                or "\\" in name
                or not relative.parts
                or relative.parts[0] != top_level
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise ValueError(f"ZIP contains an unsafe path: {name}")
        if f"{top_level}/MediaManager.exe" not in names:
            raise ValueError("ZIP does not contain MediaManager.exe")
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC validation failed")
        for file, name in zip(files, names, strict=True):
            digest = hashlib.sha256()
            with archive.open(name, mode="r") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != file.sha256:
                raise ValueError(
                    "ZIP content changed while the staged release was packaged"
                )


def _sync_file(path: Path) -> None:
    with path.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())


def _file_identity(path: Path) -> _PublishedFileIdentity:
    metadata = path.stat(follow_symlinks=False)
    return _PublishedFileIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        size=metadata.st_size,
    )


def _unlink_if_owned(
    path: Path,
    identity: _PublishedFileIdentity,
) -> None:
    try:
        current = _file_identity(path)
    except FileNotFoundError:
        return
    if current == identity:
        path.unlink()


def _publish_without_overwrite(
    temporary: Path,
    final: Path,
) -> _PublishedFileIdentity:
    """Publish one owned temporary file without replacing an existing output."""

    if temporary.parent.resolve(strict=True) != final.parent.resolve(strict=True):
        raise ValueError("temporary and final output must share one directory")
    _sync_file(temporary)
    try:
        if os.name == "nt":
            os.rename(temporary, final)
        else:
            os.link(temporary, final)
            try:
                temporary.unlink()
            except OSError:
                final.unlink(missing_ok=True)
                raise
    except FileExistsError:
        raise
    except OSError as error:
        raise OSError(
            "atomic no-overwrite publication is unavailable"
        ) from error
    return _file_identity(final)


def package_self_contained_zip(
    release_root: Path,
    output_dir: Path,
    *,
    expected_source_revision: str,
    revision: str | None = None,
) -> SelfContainedZipPackage:
    """Package one audited staged release without changing the source folder."""

    raw_release_root = release_root.expanduser()
    if not raw_release_root.is_dir() or _is_linklike(raw_release_root):
        raise ValueError("staged release folder is missing or link-like")
    release_root = raw_release_root.resolve(strict=True)
    audit = audit_version(release_root)
    if not audit.valid:
        details = "; ".join(audit.errors)
        raise ValueError(f"staged release audit failed: {details}")
    runtime_audit = audit_staged_runtime(release_root)
    if not runtime_audit.valid:
        details = "; ".join(runtime_audit.errors)
        raise ValueError(f"staged runtime audit failed: {details}")

    files = _snapshot_release_files(release_root)
    if not files:
        raise ValueError("staged release has no files")
    info = _load_release_info(release_root / "release-info.json")
    source_revision = _validate_source_revision(
        info,
        expected_source_revision,
    )
    stem = _archive_stem(info, revision)
    output_dir = _prepare_output_directory(output_dir.expanduser(), release_root)
    final_archive = output_dir / f"{stem}.zip"
    final_checksum = output_dir / f"{stem}.zip.sha256"
    if final_archive.exists() or final_checksum.exists():
        raise FileExistsError("refusing to overwrite an existing ZIP or checksum")

    nonce = uuid4().hex
    temporary_archive = output_dir / f".{stem}.{nonce}.zip.tmp"
    temporary_checksum = output_dir / f".{stem}.{nonce}.sha256.tmp"
    archive_published: _PublishedFileIdentity | None = None
    checksum_published: _PublishedFileIdentity | None = None
    try:
        _write_zip(
            temporary_archive,
            release_root=release_root,
            files=files,
            top_level=stem,
        )
        _verify_zip(
            temporary_archive,
            files=files,
            top_level=stem,
        )
        final_audit = audit_version(release_root)
        if not final_audit.valid:
            details = "; ".join(final_audit.errors)
            raise ValueError(
                f"staged release changed during packaging: {details}"
            )
        if _load_release_info(release_root / "release-info.json") != info:
            raise ValueError("release-info.json changed during packaging")
        if _snapshot_release_files(release_root) != files:
            raise ValueError(
                "staged release files changed during packaging"
            )
        final_runtime_audit = audit_staged_runtime(release_root)
        if not final_runtime_audit.valid:
            details = "; ".join(final_runtime_audit.errors)
            raise ValueError(
                f"staged runtime changed during packaging: {details}"
            )
        digest = _sha256(temporary_archive)
        temporary_checksum.write_text(
            f"{digest}  {final_archive.name}\n",
            encoding="ascii",
            newline="\n",
        )
        archive_size = temporary_archive.stat().st_size
        checksum_published = _publish_without_overwrite(
            temporary_checksum,
            final_checksum,
        )
        archive_published = _publish_without_overwrite(
            temporary_archive,
            final_archive,
        )
    except BaseException:
        temporary_archive.unlink(missing_ok=True)
        temporary_checksum.unlink(missing_ok=True)
        if archive_published is not None:
            _unlink_if_owned(final_archive, archive_published)
        if checksum_published is not None:
            _unlink_if_owned(final_checksum, checksum_published)
        raise

    return SelfContainedZipPackage(
        archive=str(final_archive),
        checksum=str(final_checksum),
        sha256=digest,
        top_level=stem,
        files=len(files),
        bytes=archive_size,
        source_revision=source_revision,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--expected-source-revision",
        required=True,
        help=(
            "independently confirmed 40- or 64-character lowercase source "
            "revision that must match release-info.json"
        ),
    )
    parser.add_argument(
        "--revision",
        help=(
            "optional immutable revision suffix matching r[1-9][0-9]*; "
            "the track and version always come from release-info.json"
        ),
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        result = package_self_contained_zip(
            args.release_root,
            args.output_dir,
            expected_source_revision=args.expected_source_revision,
            revision=args.revision,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1
    if args.as_json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(f"PASS: {result.archive}")
        print(f"SHA256: {result.sha256}")
        print(f"FILES: {result.files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
