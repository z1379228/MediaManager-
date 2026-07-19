import pytest

from core.version import (
    display_version,
    is_core_compatible,
    release_identity_version,
    release_track,
)


def test_development_display_and_release_tracks_are_explicit() -> None:
    assert display_version() == "開發版 38.0"
    assert release_track("development") == "Development"
    assert release_track("testing") == "Testing"
    assert release_track("stable") == "Stable"
    assert release_identity_version("development") == "38.0.0"
    assert release_identity_version("testing") == "1.1.0"
    with pytest.raises(ValueError):
        release_track("preview")


def test_development_38_rejects_manifest_upper_bound_32_1() -> None:
    assert is_core_compatible("0.1.0", "38.0.0")
    assert not is_core_compatible("0.1.0", "32.1.0")
