"""Security-gated plugin enable and disable operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.package_verifier import signed_payload
from core.plugins.registry import PluginRecord, PluginRegistry
from core.plugins.supervisor import PluginSupervisor
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureVerifier
from core.security.trust_store import TrustStore

_METADATA = frozenset({"plugin.json", "files.json", "plugin.sig"})


@dataclass(frozen=True, slots=True)
class PluginOperationResult:
    successful: bool
    errors: tuple[str, ...] = ()


class PluginManager:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        supervisor: PluginSupervisor,
        trust_store: TrustStore,
        *,
        signature_verifier: SignatureVerifier | None = None,
        allow_executable_plugins: bool = True,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.supervisor = supervisor
        self.trust_store = trust_store
        self.signature_verifier = signature_verifier or SignatureVerifier()
        self.allow_executable_plugins = allow_executable_plugins

    def set_enabled(
        self,
        plugin_id: str,
        enabled: bool,
        security_mode: SecurityMode,
    ) -> PluginOperationResult:
        record = self.registry.get(plugin_id)
        if record is None:
            return PluginOperationResult(False, ("plugin is not installed",))
        if not enabled:
            self.supervisor.stop(plugin_id)
            self.registry.set_enabled(plugin_id, False)
            return PluginOperationResult(True)
        if security_mode is not SecurityMode.NORMAL:
            return PluginOperationResult(
                False,
                ("plugins can only be enabled in NORMAL security mode",),
            )
        publisher = self.trust_store.get(record.publisher_id)
        if publisher is None:
            self.registry.set_enabled(plugin_id, False)
            return PluginOperationResult(False, ("publisher is no longer trusted",))
        errors = self.verify_directory(
            self.mod_root / "installed" / record.plugin_id, record
        )
        if errors:
            self.registry.set_enabled(plugin_id, False)
            return PluginOperationResult(False, errors)
        try:
            manifest = PluginManifest.load(
                self.mod_root / "installed" / record.plugin_id / "plugin.json"
            )
            if manifest.executable and not manifest.execution_ready:
                return PluginOperationResult(
                    False,
                    ("legacy executable MOD must be repackaged with manifest v2",),
                )
            if manifest.executable and not self.allow_executable_plugins:
                return PluginOperationResult(
                    False,
                    (
                        "external executable MOD runtime is disabled until "
                        "OS-level isolation is available",
                    ),
                )
            if not set(record.approved_permissions).issubset(manifest.permissions):
                return PluginOperationResult(
                    False, ("approved capabilities exceed the signed manifest",)
                )
            if manifest.executable:
                self.supervisor.start(record)
            self.registry.set_enabled(plugin_id, True)
            return PluginOperationResult(True)
        except (OSError, RuntimeError, TimeoutError, ValueError, ManifestError) as error:
            self.supervisor.stop(plugin_id)
            self.registry.set_enabled(plugin_id, False)
            return PluginOperationResult(False, (f"plugin failed to start: {error}",))

    def verify_directory(
        self,
        root: Path,
        record: PluginRecord,
        *,
        allow_disabled_publisher: bool = False,
    ) -> tuple[str, ...]:
        publisher = (
            self.trust_store.find(record.publisher_id)
            if allow_disabled_publisher
            else self.trust_store.get(record.publisher_id)
        )
        if publisher is None:
            return ("publisher is no longer trusted",)
        root = root.resolve()
        if not root.is_relative_to(self.mod_root) or not root.is_dir():
            return ("installed plugin directory is missing or unsafe",)
        try:
            manifest_bytes = (root / "plugin.json").read_bytes()
            files_bytes = (root / "files.json").read_bytes()
            signature_bytes = (root / "plugin.sig").read_bytes()
            if hashlib.sha256(manifest_bytes).hexdigest() != record.manifest_hash:
                return ("installed plugin manifest was modified",)
            signature = self.signature_verifier.verify(
                signed_payload(manifest_bytes, files_bytes),
                signature_bytes,
                publisher.public_key,
            )
            if not signature.valid:
                return (f"installed plugin signature rejected: {signature.reason}",)
            manifest = PluginManifest.from_dict(json.loads(manifest_bytes))
            if (
                manifest.id != record.plugin_id
                or manifest.version != record.installed_version
            ):
                return ("installed plugin identity does not match registry",)
            files = json.loads(files_bytes)
            declared = files.get("files") if isinstance(files, dict) else None
            if not isinstance(declared, dict):
                return ("installed files manifest is invalid",)
            errors: list[str] = []
            declared_names = {str(name).replace("\\", "/") for name in declared}
            actual_names: set[str] = set()
            for path in root.rglob("*"):
                relative_name = path.relative_to(root).as_posix()
                if path.is_symlink():
                    errors.append(
                        f"installed symbolic link is forbidden: {relative_name}"
                    )
                elif path.is_file():
                    actual_names.add(relative_name)
            unexpected = actual_names - declared_names - _METADATA
            if unexpected:
                errors.append(f"undeclared installed files: {sorted(unexpected)}")
            missing_metadata = _METADATA - actual_names
            if missing_metadata:
                errors.append(f"installed metadata missing: {sorted(missing_metadata)}")
            for name, expected in declared.items():
                relative = PurePosixPath(str(name).replace("\\", "/"))
                target = root.joinpath(*relative.parts).resolve()
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not target.is_relative_to(root)
                    or not target.is_file()
                    or target.is_symlink()
                ):
                    errors.append(f"installed file is missing or unsafe: {name}")
                    continue
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual.lower() != str(expected).removeprefix("sha256:").lower():
                    errors.append(f"installed file hash mismatch: {name}")
            return tuple(errors)
        except (OSError, ValueError, TypeError, ManifestError) as error:
            return (f"installed plugin verification failed: {error}",)
