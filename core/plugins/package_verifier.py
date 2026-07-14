"""Fail-closed .modpkg ZIP verification without extraction."""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.plugins.manifest import ManifestError, PluginManifest

BLOCKED_SUFFIXES = frozenset(
    {".exe", ".dll", ".bat", ".cmd", ".ps1", ".com", ".msi", ".scr"}
)
_RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
_METADATA = frozenset({"plugin.json", "files.json", "plugin.sig"})
_SIGNING_DOMAIN = b"MediaManager-MOD-v1\0"


@dataclass(frozen=True, slots=True)
class PackageVerification:
    valid: bool
    manifest: PluginManifest | None = None
    errors: tuple[str, ...] = ()


def signed_payload(manifest_bytes: bytes, files_bytes: bytes) -> bytes:
    """Create the unambiguous byte sequence covered by plugin.sig."""
    return (
        _SIGNING_DOMAIN
        + len(manifest_bytes).to_bytes(8, "big")
        + manifest_bytes
        + len(files_bytes).to_bytes(8, "big")
        + files_bytes
    )


class PackageVerifier:
    def __init__(
        self,
        *,
        max_files: int = 1000,
        max_archive: int = 50_000_000,
        max_uncompressed: int = 100_000_000,
        max_compression_ratio: int = 200,
    ) -> None:
        self.max_files = max_files
        self.max_archive = max_archive
        self.max_uncompressed = max_uncompressed
        self.max_compression_ratio = max_compression_ratio

    def verify(self, package: str | Path) -> PackageVerification:
        try:
            path = Path(package)
            if path.stat().st_size > self.max_archive:
                return PackageVerification(False, errors=("package archive is too large",))
            return self.verify_bytes(path.read_bytes())
        except OSError as error:
            return PackageVerification(False, errors=(f"invalid package: {error}",))

    def verify_bytes(self, package: bytes) -> PackageVerification:
        if len(package) > self.max_archive:
            return PackageVerification(False, errors=("package archive is too large",))
        try:
            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                return self._verify_archive(archive)
        except (zipfile.BadZipFile, OSError) as error:
            return PackageVerification(False, errors=(f"invalid package: {error}",))

    def _verify_archive(self, archive: zipfile.ZipFile) -> PackageVerification:
        errors: list[str] = []
        try:
            infos = archive.infolist()
            file_infos = [item for item in infos if not item.is_dir()]
            if len(file_infos) > self.max_files:
                return PackageVerification(False, errors=("package file limit exceeded",))
            if sum(item.file_size for item in file_infos) > self.max_uncompressed:
                return PackageVerification(False, errors=("package size limit exceeded",))

            names: dict[str, str] = {}
            for info in infos:
                normalized = self._safe_name(info.filename, errors)
                folded = normalized.casefold()
                if folded in names:
                    errors.append(
                        f"case-insensitive duplicate path: {names[folded]} and {normalized}"
                    )
                names[folded] = normalized
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    errors.append(f"symbolic links are forbidden: {info.filename}")
                if info.flag_bits & 0x1:
                    errors.append(f"encrypted entries are forbidden: {info.filename}")
                if not info.is_dir() and info.file_size > max(info.compress_size, 1) * self.max_compression_ratio:
                    errors.append(f"compression ratio exceeded: {info.filename}")
                if PurePosixPath(normalized).suffix.lower() in BLOCKED_SUFFIXES:
                    errors.append(f"blocked executable content: {info.filename}")

            actual_files = {
                self._normalize(item.filename) for item in file_infos
            }
            if errors or not _METADATA.issubset(actual_files):
                return PackageVerification(
                    False,
                    errors=tuple(errors or ["required metadata missing"]),
                )

            manifest_bytes = archive.read("plugin.json")
            files_bytes = archive.read("files.json")
            manifest = PluginManifest.from_dict(json.loads(manifest_bytes))
            if manifest.files_manifest != "files.json":
                errors.append("files_manifest must be files.json")
            if manifest.signature != "plugin.sig":
                errors.append("signature must be plugin.sig")
            files = json.loads(files_bytes)
            declared = files.get("files") if isinstance(files, dict) else None
            if not isinstance(declared, dict) or set(files) != {"files"}:
                return PackageVerification(
                    False,
                    manifest,
                    tuple(errors + ["invalid files manifest"]),
                )

            declared_names: set[str] = set()
            for name, expected in declared.items():
                if not isinstance(name, str):
                    errors.append("declared file name must be a string")
                    continue
                normalized = self._safe_name(name, errors)
                if normalized in _METADATA:
                    errors.append(f"metadata cannot be declared as payload: {name}")
                    continue
                if normalized.casefold() in {item.casefold() for item in declared_names}:
                    errors.append(f"duplicate declared path: {name}")
                declared_names.add(normalized)
                if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
                    errors.append(f"invalid SHA-256 declaration: {name}")
                    continue
                if normalized not in actual_files:
                    errors.append(f"declared file missing: {name}")
                    continue
                actual = hashlib.sha256(archive.read(normalized)).hexdigest()
                if actual.lower() != expected.removeprefix("sha256:").lower():
                    errors.append(f"hash mismatch: {name}")

            payload_files = actual_files - _METADATA
            undeclared = payload_files - declared_names
            if undeclared:
                errors.append(f"undeclared files: {sorted(undeclared)}")
            if declared_names - payload_files:
                errors.append(
                    f"declared files absent from payload: {sorted(declared_names - payload_files)}"
                )
            if (
                manifest.plugin_type != "data-only"
                and manifest.entry_point not in declared_names
            ):
                errors.append("entry point must be declared in files.json")
            if (
                manifest.ui_descriptor
                and manifest.ui_descriptor not in declared_names
            ):
                errors.append("UI descriptor must be declared in files.json")
            if not archive.read("plugin.sig"):
                errors.append("plugin.sig must not be empty")
            return PackageVerification(not errors, manifest, tuple(errors))
        except (KeyError, ValueError, TypeError, ManifestError) as error:
            return PackageVerification(False, errors=(f"invalid package: {error}",))

    @classmethod
    def _safe_name(cls, value: str, errors: list[str]) -> str:
        normalized = cls._normalize(value)
        path = PurePosixPath(normalized)
        unsafe = (
            not normalized
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or any(":" in part or part.endswith((" ", ".")) for part in path.parts)
            or any(
                part.split(".", 1)[0].upper() in _RESERVED_WINDOWS_NAMES
                for part in path.parts
            )
        )
        if unsafe:
            errors.append(f"unsafe path: {value}")
        return normalized

    @staticmethod
    def _normalize(value: str) -> str:
        return PurePosixPath(value.replace("\\", "/")).as_posix()
