"""Persistent enable state for built-in local feature MODs."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from threading import RLock
from typing import Protocol
import uuid

from core.settings import settings_file_lock


class FeatureMod(Protocol):
    provider_id: str
    display_name: str

    @property
    def available(self) -> bool: ...

    def set_enabled(self, enabled: bool) -> int: ...

    def close(self) -> None: ...


class FeatureModToggleError(RuntimeError):
    """Report a failed toggle without claiming reversible work was restored."""

    def __init__(
        self,
        message: str,
        *,
        irreversible_side_effect_unknown: bool,
        rollback_failures: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.irreversible_side_effect_unknown = irreversible_side_effect_unknown
        self.rollback_failures = rollback_failures


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
            with settings_file_lock(self.state_path):
                # Another process may have changed a different feature after this
                # registry was constructed. Always use the latest document while
                # holding the shared writer lock.
                self._saved = self._load()
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
            with settings_file_lock(self.state_path):
                self._saved = self._load()
                previous_enabled = bool(feature.is_enabled)
                previous_saved = self._saved.get(feature_id)
                self._saved[feature_id] = enabled
                try:
                    # Persist before invoking a feature toggle because disabling a
                    # feature may cancel work that cannot be reconstructed if the
                    # state write fails afterwards.
                    self._save()
                except Exception:
                    if previous_saved is None:
                        self._saved.pop(feature_id, None)
                    else:
                        self._saved[feature_id] = previous_saved
                    raise
                try:
                    cancelled = feature.set_enabled(enabled)
                except Exception as error:
                    rollback_failures: list[str] = []
                    try:
                        feature.set_enabled(previous_enabled)
                    except Exception:
                        rollback_failures.append("runtime")
                    if previous_saved is None:
                        self._saved.pop(feature_id, None)
                    else:
                        self._saved[feature_id] = previous_saved
                    try:
                        self._save()
                    except Exception:
                        rollback_failures.append("persistence")
                    detail = (
                        f"; rollback incomplete: {', '.join(rollback_failures)}"
                        if rollback_failures
                        else ""
                    )
                    raise FeatureModToggleError(
                        f"feature MOD toggle failed{detail}",
                        # The protocol returns a cancellation count only after a
                        # successful call. A failed disable may already have
                        # cancelled work, even when enabled state compensation
                        # succeeds, so that side effect must remain unknown.
                        irreversible_side_effect_unknown=not enabled,
                        rollback_failures=tuple(rollback_failures),
                    ) from error
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
        temporary = self.state_path.with_name(
            f".{self.state_path.name}.{uuid.uuid4().hex}.tmp"
        )
        payload = (
            json.dumps(self._saved, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        try:
            with temporary.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(self.state_path)
        finally:
            temporary.unlink(missing_ok=True)
