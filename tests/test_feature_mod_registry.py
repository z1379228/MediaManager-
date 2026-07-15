from __future__ import annotations

import json

import pytest

from core.features import DeclarativeFeatureGate, FeatureModRegistry


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
