"""Signed SHA-256 release-manifest verification."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.security.signature_verifier import SignatureVerifier

_RELEASE_DOMAIN = b"MediaManager-Release-v1\0"
_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


def release_signed_payload(manifest_bytes: bytes) -> bytes:
    return (
        _RELEASE_DOMAIN
        + len(manifest_bytes).to_bytes(8, "big")
        + manifest_bytes
    )


@dataclass(frozen=True, slots=True)
class IntegrityResult:
    valid: bool
    checked: int
    errors: tuple[str, ...] = ()


class IntegrityVerifier:
    def __init__(
        self,
        root: Path,
        *,
        public_key: str | None = None,
        key_id: str | None = None,
        signature_verifier: SignatureVerifier | None = None,
    ) -> None:
        self.root = root.resolve()
        self.public_key = public_key
        self.key_id = key_id
        self.signature_verifier = signature_verifier or SignatureVerifier()

    def verify(self, manifest_path: Path) -> IntegrityResult:
        signature_path = manifest_path.with_name("release-manifest.sig")
        if not manifest_path.is_file() or not signature_path.is_file():
            return IntegrityResult(
                False, 0, ("signed release manifest is missing",)
            )
        if not self.public_key or not self.key_id:
            return IntegrityResult(
                False, 0, ("release verification key is not configured",)
            )
        try:
            manifest_bytes = manifest_path.read_bytes()
            signature = signature_path.read_bytes()
            manifest = json.loads(manifest_bytes)
        except (OSError, ValueError) as error:
            return IntegrityResult(
                False, 0, (f"invalid release manifest: {error}",)
            )
        signature_result = self.signature_verifier.verify(
            release_signed_payload(manifest_bytes),
            signature,
            self.public_key,
        )
        if not signature_result.valid:
            return IntegrityResult(
                False,
                0,
                (f"release manifest signature invalid: {signature_result.reason}",),
            )
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version",
            "key_id",
            "files",
        }:
            return IntegrityResult(False, 0, ("release manifest fields invalid",))
        if manifest["schema_version"] != 1 or manifest["key_id"] != self.key_id:
            return IntegrityResult(
                False, 0, ("release manifest schema or key id invalid",)
            )
        files = manifest["files"]
        if not isinstance(files, dict) or not files or len(files) > 10_000:
            return IntegrityResult(False, 0, ("release file list invalid",))
        errors: list[str] = []
        checked = 0
        for name, expected in files.items():
            if not isinstance(name, str) or not isinstance(expected, str):
                errors.append("release file declaration invalid")
                continue
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts:
                errors.append(f"unsafe manifest path: {name}")
                continue
            if not _SHA256.fullmatch(expected):
                errors.append(f"invalid SHA-256 declaration: {name}")
                continue
            candidate = (self.root / Path(*relative.parts)).resolve()
            if not candidate.is_relative_to(self.root) or not candidate.is_file():
                errors.append(f"missing file: {name}")
                continue
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            checked += 1
            if actual.lower() != expected.removeprefix("sha256:").lower():
                errors.append(f"hash mismatch: {name}")
        return IntegrityResult(not errors, checked, tuple(errors))
