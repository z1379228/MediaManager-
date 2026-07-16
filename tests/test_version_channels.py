import pytest

from core.version import display_version, release_identity_version, release_track


def test_development_display_and_release_tracks_are_explicit() -> None:
    assert display_version() == "開發版 21.0"
    assert release_track("development") == "Development"
    assert release_track("testing") == "Testing"
    assert release_track("stable") == "Stable"
    assert release_identity_version("development") == "21.0.0"
    assert release_identity_version("testing") == "1.0.0"
    with pytest.raises(ValueError):
        release_track("preview")
