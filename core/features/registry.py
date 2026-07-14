"""Persistent enable state for built-in local feature MODs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from threading import RLock
from typing import Protocol


class FeatureMod(Protocol):
    provider_id: str
    display_name: str

    @property
    def available(self) -> bool: ...

    def set_enabled(self, enabled: bool) -> int: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class FeatureStatus:
    provider_id: str
    display_name: str
    enabled: bool
    available: bool = True


class FeatureModRegistry:
    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path.resolve()
        self._lock = RLock()
        self._features: dict[str, FeatureMod] = {}
        self._saved = self._load()

    def register(self, feature: FeatureMod, *, enabled: bool = False) -> None:
        if not feature.provider_id or feature.provider_id in self._features:
            raise ValueError("feature MOD id is empty or already registered")
        with self._lock:
            self._features[feature.provider_id] = feature
            requested = self._saved.get(feature.provider_id, enabled)
            try:
                feature.set_enabled(requested)
            except RuntimeError:
                feature.set_enabled(False)
                self._saved[feature.provider_id] = False
                self._save()

    def statuses(self) -> tuple[FeatureStatus, ...]:
        with self._lock:
            return tuple(
                FeatureStatus(
                    feature_id,
                    feature.display_name,
                    feature.is_enabled,
                    feature.available,
                )
                for feature_id, feature in sorted(self._features.items())
            )

    def is_enabled(self, feature_id: str) -> bool:
        with self._lock:
            if feature_id not in self._features:
                raise KeyError(feature_id)
            return self._features[feature_id].is_enabled

    def set_enabled(self, feature_id: str, enabled: bool) -> int:
        with self._lock:
            feature = self._features.get(feature_id)
            if feature is None:
                raise KeyError(feature_id)
            cancelled = feature.set_enabled(enabled)
            self._saved[feature_id] = enabled
            self._save()
            return cancelled

    def close(self) -> None:
        with self._lock:
            features = tuple(reversed(tuple(self._features.values())))
        for feature in features:
            feature.close()

    def _load(self) -> dict[str, bool]:
        if not self.state_path.is_file():
            return {}
        try:
            document = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(document, dict):
            return {}
        return {
            str(key): value for key, value in document.items() if isinstance(value, bool)
        }

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._saved, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)
