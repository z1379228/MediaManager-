from __future__ import annotations

from types import SimpleNamespace

from core.builtin_mod_snapshot import BuiltinModSnapshot, snapshot_for_context


class _Registry:
    def __init__(self, statuses: tuple[object, ...]) -> None:
        self._statuses = statuses
        self.calls = 0

    def statuses(self) -> tuple[object, ...]:
        self.calls += 1
        return self._statuses


def test_capture_reads_each_registry_once_and_copies_errors() -> None:
    download = _Registry(("download",))
    discovery = _Registry(("discovery",))
    features = _Registry(("feature",))
    errors = {"youtube": "bad manifest"}

    snapshot = BuiltinModSnapshot.capture(download, discovery, features, errors)
    errors["youtube"] = "changed"

    assert snapshot.download == ("download",)
    assert snapshot.discovery == ("discovery",)
    assert snapshot.feature == ("feature",)
    assert snapshot.errors["youtube"] == "bad manifest"
    assert (download.calls, discovery.calls, features.calls) == (1, 1, 1)


def test_context_snapshot_is_cached_until_invalidated() -> None:
    download = _Registry(())
    discovery = _Registry(())
    features = _Registry(())
    context = SimpleNamespace(
        download_providers=download,
        discovery=discovery,
        features=features,
        builtin_mod_errors={},
    )

    first = snapshot_for_context(context)
    second = snapshot_for_context(context)
    assert first is second
    assert (download.calls, discovery.calls, features.calls) == (1, 1, 1)

    context.builtin_mod_snapshot = None
    assert snapshot_for_context(context) is not first
    assert (download.calls, discovery.calls, features.calls) == (2, 2, 2)
