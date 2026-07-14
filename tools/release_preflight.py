"""Fail-closed checks for a complete, signed MediaManager release."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping
from collections.abc import Callable

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.security.integrity_verifier import IntegrityVerifier
from core.security.release_key import RELEASE_KEY_ID, RELEASE_PUBLIC_KEY
from core.security.release_layout import DEFAULT_RELEASE_FILES

_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True, slots=True)
class PreflightResult:
    ready: bool
    checked: int
    errors: tuple[str, ...]


def authenticode_status(path: Path) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "& { param([string]$p) "
        "(Get-AuthenticodeSignature -LiteralPath $p).Status.ToString() }",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"Unavailable: {error}"
    return result.stdout.strip() or result.stderr.strip() or "Unknown"


def _valid_identity(key_id: str, public_key: str) -> bool:
    if not _KEY_ID.fullmatch(key_id):
        return False
    try:
        return len(base64.b64decode(public_key, validate=True)) == 32
    except (ValueError, TypeError):
        return False


def check_release(
    root: Path,
    *,
    key_id: str = RELEASE_KEY_ID,
    public_key: str = RELEASE_PUBLIC_KEY,
    files: tuple[str, ...] = DEFAULT_RELEASE_FILES,
    builtin_hashes: Mapping[str, Mapping[str, str]] = BUILTIN_PROVIDER_HASHES,
    require_authenticode: bool = True,
    authenticode_checker: Callable[[Path], str] = authenticode_status,
) -> PreflightResult:
    root = root.resolve()
    errors: list[str] = []
    checked = 0
    identity_valid = _valid_identity(key_id, public_key)
    if not identity_valid:
        errors.append("compiled release key id or Ed25519 public key is invalid")

    for name in files:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"unsafe required release path: {name}")
            continue
        candidate = (root / Path(*relative.parts)).resolve()
        if (
            not candidate.is_relative_to(root)
            or not candidate.is_file()
            or candidate.is_symlink()
        ):
            errors.append(f"required release file missing or unsafe: {name}")
            continue
        checked += 1

    for provider_id, expected_files in builtin_hashes.items():
        for filename, expected_hash in expected_files.items():
            name = f"mod/builtin/{provider_id}/{filename}"
            candidate = root / Path(*PurePosixPath(name).parts)
            if not candidate.is_file() or candidate.is_symlink():
                continue
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected_hash:
                errors.append(f"built-in MOD hash mismatch: {name}")

    manifest = root / "security" / "release-manifest.json"
    if identity_valid:
        integrity = IntegrityVerifier(
            root,
            public_key=public_key,
            key_id=key_id,
        ).verify(manifest)
        checked += integrity.checked
        errors.extend(integrity.errors)
        if integrity.valid:
            try:
                declared = set(json.loads(manifest.read_bytes())["files"])
            except (OSError, ValueError, KeyError, TypeError):
                errors.append("cannot inspect signed release file coverage")
            else:
                required = set(files)
                if declared != required:
                    errors.append("signed release file list does not match required files")

    executable = root / "MediaManager.exe"
    if require_authenticode and identity_valid and executable.is_file():
        status = authenticode_checker(executable)
        if status != "Valid":
            errors.append(f"Authenticode signature is not valid: {status}")

    return PreflightResult(not errors, checked, tuple(dict.fromkeys(errors)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that a MediaManager directory is ready to publish."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    result = check_release(args.root)
    if args.as_json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print("READY" if result.ready else "BLOCKED")
        print(f"Checked files: {result.checked}")
        for error in result.errors:
            print(f"- {error}")
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
