from __future__ import annotations

import pytest

from contracts.provider_capability_v1 import (
    ProviderCapabilityError,
    ProviderCapabilityV1,
)
from core.downloads.capabilities import builtin_provider_capability


def test_builtin_capability_round_trips_without_network_permissions() -> None:
    declaration = builtin_provider_capability("ani-gamer")
    restored = ProviderCapabilityV1.from_dict(declaration.to_dict())

    assert restored == declaration
    assert "local-playback" in restored.operations
    assert restored.requires_official_page is True


def test_capability_rejects_unknown_operations_and_inconsistent_flags() -> None:
    with pytest.raises(ProviderCapabilityError, match="unsupported"):
        ProviderCapabilityV1(
            provider_id="example",
            sites=("example",),
            operations=("network-unrestricted",),
            requires_official_page=False,
            supports_local_playback=False,
            supports_offline_archive=False,
            max_batch_size=1,
        )

    with pytest.raises(ProviderCapabilityError, match="local playback"):
        ProviderCapabilityV1(
            provider_id="example",
            sites=("example",),
            operations=("preview",),
            requires_official_page=True,
            supports_local_playback=True,
            supports_offline_archive=False,
            max_batch_size=1,
        )


def test_capability_rejects_extra_manifest_fields() -> None:
    payload = builtin_provider_capability("youtube").to_dict()
    payload["unexpected"] = True

    with pytest.raises(ProviderCapabilityError, match="fields"):
        ProviderCapabilityV1.from_dict(payload)
