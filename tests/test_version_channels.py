import pytest

from core.version import display_version, release_track


def test_development_display_and_release_track_are_explicit() -> None:
    assert display_version() == "開發版 9.0"
    assert release_track("development") == "Development"
    assert release_track("stable") == "Stable"
    with pytest.raises(ValueError):
        release_track("preview")
