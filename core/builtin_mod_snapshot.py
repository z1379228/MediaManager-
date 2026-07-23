"""Consistent, in-memory snapshot of built-in MOD registry state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltinModSnapshot:
    """One coherent read of all built-in MOD registries.

    UI and diagnostics consume this immutable object instead of reading the
    three registries independently during the same refresh cycle.
    """

    download: tuple[object, ...]
    discovery: tuple[object, ...]
    feature: tuple[object, ...]
    errors: Mapping[str, str]

    @classmethod
    def capture(
        cls,
        download_providers: object,
        discovery: object,
        features: object | None = None,
        errors: Mapping[str, str] | None = None,
    ) -> "BuiltinModSnapshot":
        def statuses(registry: object | None) -> tuple[object, ...]:
            method = getattr(registry, "statuses", None)
            if not callable(method):
                return ()
            return tuple(method())

        return cls(
            statuses(download_providers),
            statuses(discovery),
            statuses(features),
            dict(errors or {}),
        )

    def statuses(self, kind: str) -> tuple[object, ...]:
        if kind == "download":
            return self.download
        if kind == "discovery":
            return self.discovery
        if kind == "feature":
            return self.feature
        raise KeyError(kind)


def snapshot_for_context(context: object) -> BuiltinModSnapshot:
    """Return the cached snapshot, capturing it once when necessary."""

    snapshot = getattr(context, "builtin_mod_snapshot", None)
    if isinstance(snapshot, BuiltinModSnapshot):
        return snapshot
    snapshot = BuiltinModSnapshot.capture(
        getattr(context, "download_providers", None),
        getattr(context, "discovery", None),
        getattr(context, "features", None),
        getattr(context, "builtin_mod_errors", {}),
    )
    try:
        setattr(context, "builtin_mod_snapshot", snapshot)
    except (AttributeError, TypeError):
        pass
    return snapshot
