"""Transactional, fail-closed installation of verified MOD packages."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.plugins.dependency_graph import (
    MAX_DEPENDENCIES_PER_PLUGIN,
    candidate_dependency_graph_errors,
)
from core.plugins.lifecycle import PluginLifecycleLock, PluginLifecycleLockError
from core.plugins.manifest import PluginManifest
from core.plugins.package_verifier import PackageVerifier, signed_payload
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.security.safe_mode import SecurityMode
from core.security.signature_verifier import SignatureVerifier
from core.security.trust_store import TrustStore
from core.version import CORE_VERSION, is_core_compatible


@dataclass(frozen=True, slots=True)
class InstallationResult:
    installed: bool
    plugin_id: str | None = None
    version: str | None = None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedPackage:
    valid: bool
    package_bytes: bytes = b""
    manifest: PluginManifest | None = None
    manifest_hash: str = ""
    errors: tuple[str, ...] = ()


class PluginInstaller:
    def __init__(
        self,
        mod_root: Path,
        registry: PluginRegistry,
        trust_store: TrustStore,
        *,
        package_verifier: PackageVerifier | None = None,
        signature_verifier: SignatureVerifier | None = None,
        lifecycle_lock: PluginLifecycleLock | None = None,
    ) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.trust_store = trust_store
        self.package_verifier = package_verifier or PackageVerifier()
        self.signature_verifier = signature_verifier or SignatureVerifier()
        self.lifecycle_lock = lifecycle_lock or PluginLifecycleLock(self.mod_root)

    def prepare(
        self,
        package: Path,
        security_mode: SecurityMode,
    ) -> PreparedPackage:
        try:
            with self.lifecycle_lock.hold():
                return self._prepare_locked(package, security_mode)
        except PluginLifecycleLockError:
            return PreparedPackage(False, errors=("plugin lifecycle is busy",))

    def _prepare_locked(
        self,
        package: Path,
        security_mode: SecurityMode,
    ) -> PreparedPackage:
        if security_mode is SecurityMode.BLOCKED:
            return PreparedPackage(
                False,
                errors=("plugins cannot be installed in BLOCKED security mode",),
            )
        package = package.resolve()
        if package.suffix.lower() != ".modpkg":
            return PreparedPackage(False, errors=("package must use .modpkg",))
        try:
            package_bytes = package.read_bytes()
        except OSError as error:
            return PreparedPackage(False, errors=(f"cannot read package: {error}",))
        verification = self.package_verifier.verify_bytes(package_bytes)
        manifest = verification.manifest
        if not verification.valid or manifest is None:
            return PreparedPackage(False, errors=verification.errors)
        if not is_core_compatible(
            manifest.minimum_core_version,
            manifest.maximum_core_version,
        ):
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=(f"plugin is incompatible with core {CORE_VERSION}",),
            )
        if len(manifest.dependencies) > MAX_DEPENDENCIES_PER_PLUGIN:
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=(
                    "plugin dependency graph is invalid: too many dependencies "
                    f"for {manifest.id}",
                ),
            )
        missing_dependencies = tuple(
            dependency
            for dependency in manifest.dependencies
            if (dependency_record := self.registry.get(dependency)) is None
            or dependency_record.pending_action is not PendingAction.NONE
        )
        if missing_dependencies:
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=(f"plugin dependencies are missing: {missing_dependencies}",),
            )
        try:
            self.trust_store.load()
        except (OSError, TypeError, ValueError):
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=("publisher trust store could not be refreshed",),
            )
        publisher = self.trust_store.get(manifest.publisher)
        if publisher is None:
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=("publisher is not trusted",),
            )
        try:
            with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
                manifest_bytes = archive.read("plugin.json")
                files_bytes = archive.read("files.json")
                signature = self.signature_verifier.verify(
                    signed_payload(manifest_bytes, files_bytes),
                    archive.read("plugin.sig"),
                    publisher.public_key,
                )
                if not signature.valid:
                    return PreparedPackage(
                        False,
                        manifest=manifest,
                        errors=(f"signature rejected: {signature.reason}",),
                    )
                return PreparedPackage(
                    True,
                    package_bytes,
                    manifest,
                    hashlib.sha256(manifest_bytes).hexdigest(),
                )
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as error:
            return PreparedPackage(
                False,
                manifest=manifest,
                errors=(f"package preparation failed: {error}",),
            )

    def install(
        self,
        package: Path,
        *,
        approved_permissions: tuple[str, ...] = (),
        security_mode: SecurityMode,
    ) -> InstallationResult:
        try:
            with self.lifecycle_lock.hold():
                return self._install_locked(
                    package,
                    approved_permissions=approved_permissions,
                    security_mode=security_mode,
                )
        except PluginLifecycleLockError:
            return InstallationResult(False, errors=("plugin lifecycle is busy",))

    def _install_locked(
        self,
        package: Path,
        *,
        approved_permissions: tuple[str, ...],
        security_mode: SecurityMode,
    ) -> InstallationResult:
        prepared = self._prepare_locked(package, security_mode)
        manifest = prepared.manifest
        if not prepared.valid or manifest is None:
            return InstallationResult(
                False,
                manifest.id if manifest else None,
                manifest.version if manifest else None,
                prepared.errors,
            )
        if self.registry.get(manifest.id) is not None:
            return InstallationResult(
                False,
                manifest.id,
                manifest.version,
                ("plugin is already installed; use the update workflow",),
            )
        if not set(approved_permissions).issubset(manifest.permissions):
            return InstallationResult(
                False,
                manifest.id,
                manifest.version,
                ("approved permissions exceed the manifest request",),
            )
        graph_errors = candidate_dependency_graph_errors(
            self.mod_root,
            self.registry,
            manifest,
        )
        if graph_errors:
            return InstallationResult(
                False,
                manifest.id,
                manifest.version,
                graph_errors,
            )
        try:
            with zipfile.ZipFile(io.BytesIO(prepared.package_bytes)) as archive:
                return self._commit(
                    archive,
                    manifest,
                    approved_permissions,
                    prepared.manifest_hash,
                )
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as error:
            return InstallationResult(
                False,
                manifest.id,
                manifest.version,
                (f"installation failed: {error}",),
            )

    def _commit(
        self,
        archive: zipfile.ZipFile,
        manifest: PluginManifest,
        approved_permissions: tuple[str, ...],
        manifest_hash: str,
    ) -> InstallationResult:
        installed_root = self.mod_root / "installed"
        installed_root.mkdir(parents=True, exist_ok=True)
        target = installed_root / manifest.id
        if target.exists():
            return InstallationResult(
                False,
                manifest.id,
                manifest.version,
                ("plugin target already exists",),
            )
        staging = Path(tempfile.mkdtemp(prefix=f".{manifest.id}-", dir=installed_root))
        committed = False
        try:
            self.extract_archive(archive, staging)
            os.replace(staging, target)
            committed = True
            try:
                self.registry.upsert(
                    PluginRecord(
                        plugin_id=manifest.id,
                        installed_version=manifest.version,
                        enabled=False,
                        pending_action=PendingAction.NONE,
                        trust_level="TRUSTED_PUBLISHER",
                        publisher_id=manifest.publisher,
                        approved_permissions=approved_permissions,
                        manifest_hash=manifest_hash,
                    )
                )
            except Exception:
                shutil.rmtree(target, ignore_errors=True)
                committed = False
                raise
            return InstallationResult(True, manifest.id, manifest.version)
        finally:
            if not committed:
                shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def extract_archive(archive: zipfile.ZipFile, destination: Path) -> None:
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = PurePosixPath(info.filename.replace("\\", "/"))
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
