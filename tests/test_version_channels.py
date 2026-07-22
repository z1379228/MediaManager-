import pytest

from core import version as version_module
from core.version import (
    display_version,
    is_core_compatible,
    release_identity_version,
    release_track,
)


def test_development_display_and_release_tracks_are_explicit() -> None:
    assert display_version() == "開發版 39.0.6"
    assert release_track("development") == "Development"
    assert release_track("testing") == "Testing"
    assert release_track("stable") == "Stable"
    assert release_identity_version("development") == "39.0.6"
    assert release_identity_version("testing") == "1.1.0"
    assert release_identity_version("stable") == "1.0.0"
    with pytest.raises(ValueError):
        release_track("preview")


def test_development_display_preserves_the_correction_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(version_module, "CORE_VERSION", "38.1.8")

    assert version_module.display_version() == "開發版 38.1.8"


def test_stable_display_uses_the_public_stable_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(version_module, "BUILD_CHANNEL", "stable")

    assert version_module.display_version() == "正式版 1.0"


def test_development_39_rejects_manifest_upper_bound_32_1() -> None:
    assert is_core_compatible("0.1.0", "39.0.6")
    assert not is_core_compatible("0.1.0", "32.1.0")
