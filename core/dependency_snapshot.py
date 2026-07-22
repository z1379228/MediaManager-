"""Cached, bounded dependency snapshot shared by UI and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
from threading import RLock
from typing import Callable

from core.builtin_mod_catalog import BUILTIN_MOD_CATALOG
from core.dependency_health import DependencyReport, check_dependencies


@dataclass(frozen=True, slots=True)
class FeatureReadiness:
    provider_id: str
    ready: bool
    missing: tuple[str, ...]
    optional_missing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DependencySnapshot:
    report: DependencyReport
    readiness: tuple[FeatureReadiness, ...]
    fingerprint: str

    def readiness_for(self, provider_id: str) -> FeatureReadiness:
        for item in self.readiness:
            if item.provider_id == provider_id:
                return item
        raise KeyError(provider_id)


ReportFactory = Callable[[Path, Path], DependencyReport]


def _default_report_factory(application_root: Path, data_root: Path) -> DependencyReport:
    return check_dependencies(application_root, data_root=data_root)


class DependencySnapshotService:
    """Refresh explicitly; warm reads never start a process or create files."""

    def __init__(
        self,
        application_root: Path,
        data_root: Path,
        *,
        report_factory: ReportFactory = _default_report_factory,
    ) -> None:
        self.application_root = application_root.resolve()
        self.data_root = data_root.resolve()
        self._report_factory = report_factory
        self._cached: DependencySnapshot | None = None
        self._lock = RLock()

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(os.environ.get("PATH", "").encode("utf-8", errors="replace"))
        for name in (
            "deno", "node", "qjs", "ffmpeg", "ffprobe", "mega-get", "whisper-cli"
        ):
            executable = f"{name}.exe" if os.name == "nt" else name
            raw = next(
                (
                    str(candidate.resolve())
                    for candidate in (
                        self.application_root / "tools" / executable,
                        self.application_root / executable,
                    )
                    if candidate.is_file()
                ),
                shutil.which(name),
            )
            digest.update(name.encode("ascii"))
            digest.update(str(raw or "").encode("utf-8", errors="replace"))
            if raw:
                try:
                    stat = Path(raw).stat()
                    digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode("ascii"))
                except OSError:
                    digest.update(b"missing")
        model_root = self.data_root / "models" / "speech-to-text"
        try:
            models = sorted(model_root.iterdir(), key=lambda path: path.name)[:64]
        except OSError:
            models = []
        for path in models:
            try:
                stat = path.stat()
                digest.update(path.name.encode("utf-8", errors="replace"))
                digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode("ascii"))
            except OSError:
                continue
        return digest.hexdigest()

    @staticmethod
    def _readiness(report: DependencyReport) -> tuple[FeatureReadiness, ...]:
        available = {
            status.dependency_id
            for status in report.statuses
            if status.available
        }
        readiness = []
        for descriptor in BUILTIN_MOD_CATALOG:
            missing = tuple(
                dependency_id
                for dependency_id in descriptor.dependency_ids
                if dependency_id not in available
            )
            optional_missing = tuple(
                dependency_id
                for dependency_id in descriptor.optional_dependency_ids
                if dependency_id not in available
            )
            readiness.append(
                FeatureReadiness(
                    descriptor.provider_id,
                    not missing,
                    missing,
                    optional_missing,
                )
            )
        return tuple(readiness)

    def refresh(self) -> DependencySnapshot:
        with self._lock:
            report = self._report_factory(self.application_root, self.data_root)
            snapshot = DependencySnapshot(
                report,
                self._readiness(report),
                self._fingerprint(),
            )
            self._cached = snapshot
            return snapshot

    def snapshot(self) -> DependencySnapshot:
        with self._lock:
            cached = self._cached
            if cached is not None and cached.fingerprint == self._fingerprint():
                return cached
        return self.refresh()

    def peek(self) -> DependencySnapshot | None:
        """Return the warm snapshot without probing tools or starting processes."""

        with self._lock:
            return self._cached

    def invalidate(self) -> None:
        with self._lock:
            self._cached = None
