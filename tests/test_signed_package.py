from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.plugins.installer import PluginInstaller
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION


def test_real_ed25519_signed_package_installs(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    public_key = "ed25519:" + base64.b64encode(public_bytes).decode("ascii")
    source = b"def handle_request(request):\n    return request\n"
    manifest = {
        "schema_version": 1,
        "id": "signed.plugin",
        "name": "Signed",
        "version": "1.0.0",
        "publisher": "signed.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": CORE_VERSION,
        "permissions": [],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
    files_bytes = json.dumps(
        {"files": {"plugin.py": hashlib.sha256(source).hexdigest()}},
        separators=(",", ":"),
    ).encode()
    signature = private_key.sign(signed_payload(manifest_bytes, files_bytes))
    package = tmp_path / "signed.modpkg"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", manifest_bytes)
        archive.writestr("files.json", files_bytes)
        archive.writestr("plugin.sig", signature)
        archive.writestr("plugin.py", source)
    store = TrustStore(tmp_path / "trust-store.json")
    store.add("signed.example", public_key)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(tmp_path / "mod", registry, store)
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert result.installed
    assert registry.get("signed.plugin") is not None
    registry.close()
