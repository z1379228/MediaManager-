from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from pathlib import Path

from core.plugins.installer import PluginInstaller
from core.plugins.registry import PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureResult
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION


class AcceptingSignatureVerifier:
    def verify(
        self, payload: bytes, signature: bytes, public_key: str
    ) -> SignatureResult:
        assert payload
        assert signature == b"test-signature"
        assert public_key == base64.b64encode(b"k" * 32).decode("ascii")
        return SignatureResult(True, "accepted for test")


def build_package(
    path: Path,
    *,
    publisher: str = "trusted.example",
    minimum_core_version: str = "0.1.0",
    maximum_core_version: str = CORE_VERSION,
    dependencies: list[str] | None = None,
) -> None:
    plugin_source = b"def handle_request(request):\n    return request\n"
    manifest = {
        "schema_version": 1,
        "id": "example.plugin",
        "name": "Example",
        "version": "1.0.0",
        "publisher": publisher,
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": minimum_core_version,
        "maximum_core_version": maximum_core_version,
        "permissions": ["media.read"],
        "external_tools": [],
        "dependencies": dependencies or [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }
    files = {"files": {"plugin.py": hashlib.sha256(plugin_source).hexdigest()}}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr("files.json", json.dumps(files))
        archive.writestr("plugin.sig", b"test-signature")
        archive.writestr("plugin.py", plugin_source)


def trust_store(path: Path) -> TrustStore:
    path.write_text(
        json.dumps(
            {
                "publishers": [
                    {
                        "publisher_id": "trusted.example",
                        "public_key": base64.b64encode(b"k" * 32).decode("ascii"),
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    store = TrustStore(path)
    store.load()
    return store


def test_installs_verified_package_disabled(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(
        package,
        approved_permissions=("media.read",),
        security_mode=SecurityMode.SAFE_MODE,
    )
    record = registry.get("example.plugin")
    assert result.installed
    assert (tmp_path / "mod" / "installed" / "example.plugin" / "plugin.py").is_file()
    assert record is not None
    assert not record.enabled
    assert record.approved_permissions == ("media.read",)
    registry.close()


def test_rejects_untrusted_publisher_without_extracting(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package, publisher="unknown.example")
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == ("publisher is not trusted",)
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_default_signature_verifier_fails_closed(tmp_path: Path) -> None:
    package = tmp_path / "example.modpkg"
    build_package(package)
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors[0].startswith("signature rejected:")
    assert not (tmp_path / "mod" / "installed" / "example.plugin").exists()
    registry.close()


def test_blocked_mode_rejects_before_reading_package(tmp_path: Path) -> None:
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(
        tmp_path / "missing.modpkg",
        security_mode=SecurityMode.BLOCKED,
    )
    assert not result.installed
    assert result.errors == ("plugins cannot be installed in BLOCKED security mode",)
    registry.close()


def test_rejects_incompatible_core_version(tmp_path: Path) -> None:
    package = tmp_path / "future.modpkg"
    build_package(
        package,
        minimum_core_version="9.0.0",
        maximum_core_version="9.9.9",
    )
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == (f"plugin is incompatible with core {CORE_VERSION}",)
    registry.close()


def test_rejects_missing_plugin_dependency(tmp_path: Path) -> None:
    package = tmp_path / "dependent.modpkg"
    build_package(package, dependencies=["required.plugin"])
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    installer = PluginInstaller(
        tmp_path / "mod",
        registry,
        trust_store(tmp_path / "trust-store.json"),
        signature_verifier=AcceptingSignatureVerifier(),
    )
    result = installer.install(package, security_mode=SecurityMode.SAFE_MODE)
    assert not result.installed
    assert result.errors == ("plugin dependencies are missing: ('required.plugin',)",)
    registry.close()
