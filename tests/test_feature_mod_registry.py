from __future__ import annotations

from core.features import FeatureModRegistry


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
