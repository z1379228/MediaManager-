from __future__ import annotations

import json
from threading import Event, Thread

import pytest

from core.features import DeclarativeFeatureGate, FeatureModRegistry
from core.features.registry import FeatureModToggleError


class SampleFeature:
    provider_id = "sample"
    display_name = "Sample"
    available = True

    def __init__(self) -> None:
        self.is_enabled = False
        self.cancelled = 0
        self.closed = False

    def set_enabled(self, enabled: bool) -> int:
        self.is_enabled = enabled
        return self.cancelled if not enabled else 0

    def close(self) -> None:
        self.closed = True


class PartiallyFailingFeature(SampleFeature):
    def __init__(self) -> None:
        super().__init__()
        self.irreversible_cancellations = 0

    def set_enabled(self, enabled: bool) -> int:
        if not enabled and self.is_enabled:
            self.irreversible_cancellations += 1
            self.is_enabled = False
            raise RuntimeError("failed after cancelling work")
        self.is_enabled = enabled
        return 0


def test_feature_mod_state_persists_and_disable_returns_cancel_count(tmp_path) -> None:
    state = tmp_path / "feature-state.json"
    feature = SampleFeature()
    registry = FeatureModRegistry(state)
    registry.register(feature)
    registry.set_enabled("sample", True)
    assert registry.is_enabled("sample")
    feature.cancelled = 2
    assert registry.set_enabled("sample", False) == 2

    restored = SampleFeature()
    second = FeatureModRegistry(state)
    second.register(restored, enabled=True)
    assert not restored.is_enabled
    second.close()
    assert restored.closed


def test_feature_mod_save_failure_does_not_cancel_or_toggle_runtime(
    tmp_path, monkeypatch
) -> None:
    state = tmp_path / "feature-state.json"
    feature = SampleFeature()
    registry = FeatureModRegistry(state)
    registry.register(feature)
    registry.set_enabled("sample", True)
    feature.cancelled = 2

    def fail_save() -> None:
        raise OSError("deterministic persistence failure")

    monkeypatch.setattr(registry, "_save", fail_save)

    with pytest.raises(OSError, match="persistence failure"):
        registry.set_enabled("sample", False)

    assert feature.is_enabled
    assert registry.is_enabled("sample")
    assert json.loads(state.read_text(encoding="utf-8"))["sample"] is True


def test_feature_mod_failed_disable_reports_irreversible_side_effect_unknown(
    tmp_path,
) -> None:
    state = tmp_path / "feature-state.json"
    feature = PartiallyFailingFeature()
    registry = FeatureModRegistry(state)
    registry.register(feature)
    registry.set_enabled("sample", True)

    with pytest.raises(FeatureModToggleError) as captured:
        registry.set_enabled("sample", False)

    assert captured.value.irreversible_side_effect_unknown
    assert captured.value.rollback_failures == ()
    assert feature.is_enabled
    assert feature.irreversible_cancellations == 1
    assert json.loads(state.read_text(encoding="utf-8"))["sample"] is True


def test_feature_mod_stale_writer_merges_latest_state(tmp_path) -> None:
    state = tmp_path / "feature-state.json"
    first = FeatureModRegistry(state)
    second = FeatureModRegistry(state)
    first_feature = SampleFeature()
    second_feature = SampleFeature()
    second_feature.provider_id = "second"
    first.register(first_feature)
    second.register(second_feature)

    first.set_enabled("sample", True)
    second.set_enabled("second", True)

    assert json.loads(state.read_text(encoding="utf-8")) == {
        "sample": True,
        "second": True,
    }


def test_feature_mod_writer_lock_serializes_independent_registries(
    tmp_path, monkeypatch
) -> None:
    state = tmp_path / "feature-state.json"
    first = FeatureModRegistry(state)
    second = FeatureModRegistry(state)
    first_feature = SampleFeature()
    second_feature = SampleFeature()
    second_feature.provider_id = "second"
    first.register(first_feature)
    second.register(second_feature)
    first_entered = Event()
    second_entered = Event()
    release_first = Event()
    original_first_save = first._save
    original_second_save = second._save

    def blocked_first_save() -> None:
        first_entered.set()
        assert release_first.wait(2)
        original_first_save()

    def observed_second_save() -> None:
        second_entered.set()
        original_second_save()

    monkeypatch.setattr(first, "_save", blocked_first_save)
    monkeypatch.setattr(second, "_save", observed_second_save)
    first_thread = Thread(target=first.set_enabled, args=("sample", True))
    second_thread = Thread(target=second.set_enabled, args=("second", True))
    first_thread.start()
    assert first_entered.wait(2)
    second_thread.start()

    assert not second_entered.wait(0.1)
    release_first.set()
    first_thread.join(2)
    second_thread.join(2)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "sample": True,
        "second": True,
    }


def test_declarative_feature_gate_validates_parent_and_addon_manifests(
    tmp_path,
) -> None:
    path = tmp_path / "feature.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider_id": "site-addon",
                "display_name": "Site Addon",
                "kind": "site-addon",
                "parent_provider_id": "site",
            }
        ),
        encoding="utf-8",
    )

    feature = DeclarativeFeatureGate.from_file(path)

    assert feature.provider_id == "site-addon"
    assert feature.parent_provider_id == "site"
    assert not feature.is_enabled
    assert feature.set_enabled(True) == 0
    assert feature.is_enabled


def test_declarative_feature_gate_rejects_addon_without_parent(tmp_path) -> None:
    path = tmp_path / "feature.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider_id": "site-addon",
                "display_name": "Site Addon",
                "kind": "site-addon",
                "parent_provider_id": "",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="identity"):
        DeclarativeFeatureGate.from_file(path)
