"""Centralized application and user-data path service."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    application: Path
    data: Path
    cache: Path
    temp: Path
    downloads: Path
    logs: Path
    settings: Path
    mod: Path
    security: Path

    @property
    def builtin_mod(self) -> Path:
        return self.application / "mod" / "builtin"

    @property
    def release_security(self) -> Path:
        return self.application / "security"

    @property
    def plugin_packages(self) -> Path:
        return self.mod / "packages"

    @property
    def installed_plugins(self) -> Path:
        return self.mod / "installed"

    @property
    def quarantined_plugins(self) -> Path:
        return self.mod / "quarantine"

    @property
    def removed_plugins(self) -> Path:
        return self.quarantined_plugins / "removed"

    @property
    def plugin_backups(self) -> Path:
        return self.mod / "backups"

    @property
    def purge_staging(self) -> Path:
        return self.quarantined_plugins / "purge"

    @property
    def plugin_registry(self) -> Path:
        return self.mod / "registry.sqlite3"

    @classmethod
    def discover(
        cls, *, portable: bool = False, app_root: Path | None = None
    ) -> "AppPaths":
        application = (app_root or Path(sys.argv[0]).resolve().parent).resolve()
        if portable:
            base = application / "UserData"
            names = {
                name: base / name.title()
                for name in (
                    "data",
                    "cache",
                    "temp",
                    "downloads",
                    "logs",
                    "settings",
                    "security",
                )
            }
            names["mod"] = base / "Mods"
        else:
            local = (
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                / "MediaManager"
            )
            roaming = (
                Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                / "MediaManager"
            )
            names = {
                "data": roaming / "Data",
                "settings": roaming / "Settings",
                "cache": local / "Cache",
                "temp": local / "Temp",
                "downloads": Path.home() / "Downloads" / "MediaManager",
                "logs": local / "Logs",
                "security": roaming / "Security",
                "mod": roaming / "Mods",
            }
        return cls(application=application, **names)

    def migrate_legacy_user_data(self) -> tuple[str, ...]:
        user_data = (self.application / "UserData").resolve()
        if self.data.resolve().parent != user_data:
            return ()
        migrated: list[str] = []
        for name, destination in (
            ("Data", self.data),
            ("Downloads", self.downloads),
            ("Settings", self.settings),
        ):
            source = self.application / name
            if (
                source.is_dir()
                and not source.is_symlink()
                and not destination.exists()
            ):
                shutil.copytree(source, destination)
                migrated.append(name)
        legacy_trust_store = self.application / "Security" / "trust-store.json"
        new_trust_store = self.security / "trust-store.json"
        if (
            legacy_trust_store.is_file()
            and not legacy_trust_store.is_symlink()
            and not new_trust_store.exists()
        ):
            self.security.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_trust_store, new_trust_store)
            migrated.append("Security/trust-store.json")
        return tuple(migrated)

    def migrate_legacy_mod_state(self) -> tuple[str, ...]:
        legacy = (self.application / "mod").resolve()
        destination_root = self.mod.resolve()
        if legacy == destination_root or not legacy.is_dir():
            return ()
        migrated: list[str] = []
        destination_root.mkdir(parents=True, exist_ok=True)
        for name in (
            "provider-state.json",
            "discovery-state.json",
            "registry.sqlite3",
            "packages",
            "installed",
            "quarantine",
            "backups",
        ):
            source = legacy / name
            destination = destination_root / name
            if not source.exists() or source.is_symlink() or destination.exists():
                continue
            if source.is_dir():
                shutil.copytree(source, destination)
            elif source.is_file():
                shutil.copy2(source, destination)
            else:
                continue
            migrated.append(name)
        return tuple(migrated)

    def ensure_runtime_directories(self) -> None:
        for path in (
            self.data,
            self.cache,
            self.temp,
            self.downloads,
            self.logs,
            self.settings,
            self.security,
            self.mod,
            self.plugin_packages,
            self.installed_plugins,
            self.quarantined_plugins,
            self.removed_plugins,
            self.plugin_backups,
            self.purge_staging,
        ):
            path.mkdir(parents=True, exist_ok=True)
