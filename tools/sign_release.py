"""Offline release signing tool. Private keys must stay outside the repository."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.security.integrity_verifier import release_signed_payload
from core.security.release_key import RELEASE_KEY_ID, RELEASE_PUBLIC_KEY
from core.security.release_layout import DEFAULT_RELEASE_FILES


def load_private_key(path: Path) -> Ed25519PrivateKey:
    raw = path.read_bytes()
    try:
        key = serialization.load_pem_private_key(raw, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("release private key must be Ed25519")
        return key
    except ValueError:
        try:
            decoded = base64.b64decode(raw.strip(), validate=True)
            if len(decoded) != 32:
                raise ValueError("raw Ed25519 private key must be 32 bytes")
            return Ed25519PrivateKey.from_private_bytes(decoded)
        except Exception as error:
            raise ValueError("cannot decode release private key") from error


def sign_release(
    root: Path,
    private_key: Ed25519PrivateKey,
    *,
    key_id: str,
    expected_public_key: str,
    files: tuple[str, ...] = DEFAULT_RELEASE_FILES,
) -> tuple[Path, Path]:
    root = root.resolve()
    derived_public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    if not key_id or derived_public_key != expected_public_key:
        raise ValueError("private key does not match the compiled release identity")
    hashes: dict[str, str] = {}
    for name in files:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe release path: {name}")
        path = (root / Path(*relative.parts)).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            raise ValueError(f"release file missing or unsafe: {name}")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_bytes = json.dumps(
        {"schema_version": 1, "key_id": key_id, "files": hashes},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    security = root / "security"
    security.mkdir(parents=True, exist_ok=True)
    manifest = security / "release-manifest.json"
    signature = security / "release-manifest.sig"
    manifest_temp = manifest.with_suffix(".json.tmp")
    signature_temp = signature.with_suffix(".sig.tmp")
    manifest_temp.write_bytes(manifest_bytes)
    signature_temp.write_bytes(
        private_key.sign(release_signed_payload(manifest_bytes))
    )
    manifest_temp.replace(manifest)
    signature_temp.replace(signature)
    return manifest, signature


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--file", action="append", dest="files")
    args = parser.parse_args()
    if not RELEASE_KEY_ID or not RELEASE_PUBLIC_KEY:
        parser.error("compile a release public key and key id before signing")
    sign_release(
        args.root,
        load_private_key(args.private_key),
        key_id=RELEASE_KEY_ID,
        expected_public_key=RELEASE_PUBLIC_KEY,
        files=tuple(args.files or DEFAULT_RELEASE_FILES),
    )
    print("release manifest signed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
