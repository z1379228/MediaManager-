"""Signed offline update bundles installed into Version/<major>.<minor>."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.security.signature_verifier import SignatureVerifier
from core.version import release_version


_UPDATE_DOMAIN = b"MediaManager-Offline-Update-v1\0"
_UPDATE_KIND = "mediamanager-offline-update"
_METADATA = frozenset({"update.json", "update.sig"})
_MAX_ARCHIVE_BYTES = 1_000_000_000
_MAX_UNCOMPRESSED_BYTES = 2_000_000_000
_MAX_FILES = 10_000
_MAX_COMPRESSION_RATIO = 250


def update_signed_payload(manifest_bytes: bytes) -> bytes:
    return _UPDATE_DOMAIN + len(manifest_bytes).to_bytes(8, "big") + manifest_bytes


@dataclass(frozen=True, slots=True)
class OfflineUpdateManifest:
    key_id: str
    minimum_source_version: str
    maximum_source_version: str
    target_version: str
    version_folder: str
    files: dict[str, str]


@dataclass(frozen=True, slots=True)
class OfflineUpdateVerification:
    valid: bool
    manifest: OfflineUpdateManifest | None = None
    package_bytes: bytes = b""
    errors: tuple[str, ...] = ()


def create_offline_bundle(
    release_root: Path,
    target: Path,
    private_key: Ed25519PrivateKey,
    *,
    key_id: str,
    minimum_source_version: str,
    maximum_source_version: str,
    target_version: str,
) -> Path:
    """Create an atomic bundle; callers keep the private key outside the repo."""

    release_root = release_root.resolve()
    expected_folder = _version_folder(target_version)
    if not key_id or release_root.name != expected_folder:
        raise ValueError("release folder or update key id is invalid")
    if release_version(minimum_source_version) > release_version(
        maximum_source_version
    ):
        raise ValueError("offline update source version range is invalid")
    files: dict[str, str] = {}
    sources: list[tuple[str, Path]] = []
    for source in sorted(release_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(release_root).as_posix()
        if source.is_symlink() or not _safe_relative(relative):
            raise ValueError(f"release file is unsafe: {relative}")
        files[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
        sources.append((relative, source))
    if not files or len(files) > _MAX_FILES:
        raise ValueError("offline update file count is invalid")
    manifest_bytes = json.dumps(
        {
            "schema_version": 1,
            "kind": _UPDATE_KIND,
            "key_id": key_id,
            "minimum_source_version": minimum_source_version,
            "maximum_source_version": maximum_source_version,
            "target_version": target_version,
            "version_folder": expected_folder,
            "files": files,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            archive.writestr("update.json", manifest_bytes)
            archive.writestr(
                "update.sig", private_key.sign(update_signed_payload(manifest_bytes))
            )
            for relative, source in sources:
                archive.write(source, f"payload/{relative}")
        if temporary.stat().st_size > _MAX_ARCHIVE_BYTES:
            raise ValueError("offline update archive is too large")
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target


class OfflineUpdateInstaller:
    def __init__(
        self,
        version_root: Path,
        *,
        public_key: str,
        key_id: str,
        signature_verifier: SignatureVerifier | None = None,
    ) -> None:
        self.version_root = version_root.resolve()
        self.public_key = public_key
        self.key_id = key_id
        self.signature_verifier = signature_verifier or SignatureVerifier()

    def verify(
        self, package: Path, *, current_version: str
    ) -> OfflineUpdateVerification:
        try:
            package = package.resolve()
            if (
                package.suffix.casefold() != ".mmupdate"
                or not package.is_file()
                or package.is_symlink()
                or package.stat().st_size > _MAX_ARCHIVE_BYTES
            ):
                return OfflineUpdateVerification(
                    False, errors=("offline update package is missing or unsafe",)
                )
            data = package.read_bytes()
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                return self._verify_archive(archive, data, current_version)
        except (OSError, ValueError, TypeError, zipfile.BadZipFile) as error:
            return OfflineUpdateVerification(
                False, errors=(f"offline update package is invalid: {error}",)
            )

    def install(self, verified: OfflineUpdateVerification) -> Path:
        manifest = verified.manifest
        if not verified.valid or manifest is None or not verified.package_bytes:
            raise ValueError("offline update has not passed verification")
        self.version_root.mkdir(parents=True, exist_ok=True)
        target = self.version_root / manifest.version_folder
        staging = self.version_root / f".{manifest.version_folder}.staging"
        backup = self.version_root / f".{manifest.version_folder}.backup"
        for candidate in (target, staging, backup):
            if candidate.parent != self.version_root:
                raise ValueError("offline update target escaped version root")
        if staging.exists() or backup.exists():
            raise RuntimeError("unfinished offline update transaction requires review")
        staging.mkdir()
        replaced = False
        try:
            with zipfile.ZipFile(io.BytesIO(verified.package_bytes)) as archive:
                for name, expected in manifest.files.items():
                    output = staging / Path(*PurePosixPath(name).parts)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    content = archive.read(f"payload/{name}")
                    if hashlib.sha256(content).hexdigest() != expected:
                        raise ValueError(f"offline update changed after verification: {name}")
                    output.write_bytes(content)
            if target.exists():
                os.replace(target, backup)
                replaced = True
            os.replace(staging, target)
            if backup.exists():
                shutil.rmtree(backup)
            return target
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            if replaced and backup.exists() and not target.exists():
                os.replace(backup, target)
            raise

    def _verify_archive(
        self,
        archive: zipfile.ZipFile,
        package_bytes: bytes,
        current_version: str,
    ) -> OfflineUpdateVerification:
        infos = archive.infolist()
        files = [info for info in infos if not info.is_dir()]
        if (
            len(files) > _MAX_FILES + len(_METADATA)
            or sum(info.file_size for info in files) > _MAX_UNCOMPRESSED_BYTES
        ):
            return OfflineUpdateVerification(False, errors=("offline update limits exceeded",))
        names: set[str] = set()
        for info in files:
            normalized = PurePosixPath(info.filename.replace("\\", "/")).as_posix()
            mode = info.external_attr >> 16
            if (
                not _safe_relative(normalized)
                or normalized.casefold() in names
                or stat.S_ISLNK(mode)
                or info.flag_bits & 0x1
                or info.file_size
                > max(info.compress_size, 1) * _MAX_COMPRESSION_RATIO
            ):
                return OfflineUpdateVerification(
                    False, errors=(f"offline update entry is unsafe: {info.filename}",)
                )
            names.add(normalized.casefold())
        if not _METADATA.issubset({info.filename for info in files}):
            return OfflineUpdateVerification(False, errors=("offline update metadata is missing",))
        manifest_bytes = archive.read("update.json")
        signature = archive.read("update.sig")
        signature_result = self.signature_verifier.verify(
            update_signed_payload(manifest_bytes), signature, self.public_key
        )
        if not signature_result.valid:
            return OfflineUpdateVerification(
                False, errors=(f"offline update signature rejected: {signature_result.reason}",)
            )
        raw = json.loads(manifest_bytes)
        expected_fields = {
            "schema_version",
            "kind",
            "key_id",
            "minimum_source_version",
            "maximum_source_version",
            "target_version",
            "version_folder",
            "files",
        }
        if not isinstance(raw, dict) or set(raw) != expected_fields:
            return OfflineUpdateVerification(False, errors=("offline update manifest fields are invalid",))
        declared = raw["files"]
        if (
            raw["schema_version"] != 1
            or raw["kind"] != _UPDATE_KIND
            or raw["key_id"] != self.key_id
            or not isinstance(declared, dict)
            or not declared
            or len(declared) > _MAX_FILES
        ):
            return OfflineUpdateVerification(False, errors=("offline update manifest is invalid",))
        target_version = str(raw["target_version"])
        minimum = str(raw["minimum_source_version"])
        maximum = str(raw["maximum_source_version"])
        if (
            not release_version(minimum)
            <= release_version(current_version)
            <= release_version(maximum)
            or release_version(target_version) <= release_version(current_version)
            or raw["version_folder"] != _version_folder(target_version)
        ):
            return OfflineUpdateVerification(False, errors=("offline update version range is invalid",))
        actual_payload = {
            info.filename.removeprefix("payload/")
            for info in files
            if info.filename.startswith("payload/")
        }
        if set(declared) != actual_payload or any(
            not _safe_relative(name)
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for name, digest in declared.items()
        ):
            return OfflineUpdateVerification(False, errors=("offline update file declarations are invalid",))
        for name, expected in declared.items():
            if hashlib.sha256(archive.read(f"payload/{name}")).hexdigest() != expected:
                return OfflineUpdateVerification(False, errors=(f"offline update hash mismatch: {name}",))
        manifest = OfflineUpdateManifest(
            key_id=self.key_id,
            minimum_source_version=minimum,
            maximum_source_version=maximum,
            target_version=target_version,
            version_folder=str(raw["version_folder"]),
            files={str(name): str(digest) for name, digest in declared.items()},
        )
        return OfflineUpdateVerification(True, manifest, package_bytes)


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _version_folder(version: str) -> str:
    major, minor, _patch = release_version(version)
    return f"{major}.{minor}"
