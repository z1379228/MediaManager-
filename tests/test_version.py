from core.version import is_newer_plugin_version


def test_stable_release_is_newer_than_prerelease() -> None:
    assert is_newer_plugin_version("1.0.0", "1.0.0-rc.1")
    assert not is_newer_plugin_version("1.0.0-rc.1", "1.0.0")


def test_numeric_prerelease_identifiers_compare_numerically() -> None:
    assert is_newer_plugin_version("1.0.0-beta.10", "1.0.0-beta.2")


def test_build_metadata_does_not_create_update() -> None:
    assert not is_newer_plugin_version("1.0.0+build.2", "1.0.0+build.1")
