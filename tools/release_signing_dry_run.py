"""Exercise release signing with an in-memory disposable Ed25519 identity."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.security.integrity_verifier import IntegrityVerifier
from core.security.release_layout import DEFAULT_RELEASE_FILES
from tools.sign_release import sign_release


def run_dry_run(
    root: Path,
    *,
    files: tuple[str, ...] = DEFAULT_RELEASE_FILES,
    temp_root: Path | None = None,
) -> dict[str, object]:
    """Copy, sign, verify and tamper a release without retaining private keys.

    ``temp_root`` lets callers select a writable user-local directory when the
    process-wide temporary directory is protected by Windows ACLs.
    """

    root = root.resolve()
    if not files:
        raise ValueError("release signing dry run needs at least one file")
    temp_directory = None if temp_root is None else str(temp_root.resolve())
    with tempfile.TemporaryDirectory(
        prefix="mediamanager-signing-",
        dir=temp_directory,
    ) as raw_temp:
        temporary_root = Path(raw_temp).resolve()
        for name in files:
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe release path: {name}")
            source = (root / Path(*relative.parts)).resolve()
            if (
                not source.is_relative_to(root)
                or not source.is_file()
                or source.is_symlink()
            ):
                raise ValueError(f"release file missing or unsafe: {name}")
            target = temporary_root / Path(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        private_key = Ed25519PrivateKey.generate()
        public_key = base64.b64encode(
            private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        key_id = "dry-run-disposable"
        manifest, _signature = sign_release(
            temporary_root,
            private_key,
            key_id=key_id,
            expected_public_key=public_key,
            files=files,
        )
        verifier = IntegrityVerifier(
            temporary_root,
            public_key=public_key,
            key_id=key_id,
        )
        valid = verifier.verify(manifest)
        if not valid.valid or valid.checked != len(files):
            raise RuntimeError(f"dry-run verification failed: {valid.errors}")

        tampered = temporary_root / Path(*PurePosixPath(files[0]).parts)
        with tampered.open("ab") as stream:
            stream.write(b"\nMediaManager signing dry-run tamper marker")
        tamper_result = verifier.verify(manifest)
        if tamper_result.valid or not any(
            error.startswith("hash mismatch:") for error in tamper_result.errors
        ):
            raise RuntimeError("dry-run tamper detection failed")
        return {
            "status": "PASS",
            "checked_files": valid.checked,
            "tamper_detected": True,
            "key_persisted": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--file", action="append", dest="files")
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="Writable user-local directory for the disposable signing workspace",
    )
    args = parser.parse_args()
    try:
        result = run_dry_run(
            args.root,
            files=tuple(args.files or DEFAULT_RELEASE_FILES),
            temp_root=args.temp_root,
        )
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
