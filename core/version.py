"""MediaManager core version and compatibility helpers."""

from __future__ import annotations

CORE_VERSION = "24.0.0"
BUILD_CHANNEL = "development"
DEVELOPMENT_GENERATION = "24.0"
TESTING_VERSION = "1.0.0"
SUPPORTED_BUILD_CHANNELS = frozenset({"development", "testing", "stable"})


def display_version() -> str:
    if BUILD_CHANNEL == "development":
        return f"開發版 {DEVELOPMENT_GENERATION}"
    if BUILD_CHANNEL == "testing":
        return f"測試版 {TESTING_VERSION.rsplit('.', 1)[0]}"
    return f"正式版 {CORE_VERSION.rsplit('.', 1)[0]}"


def release_track(channel: str = BUILD_CHANNEL) -> str:
    if channel not in SUPPORTED_BUILD_CHANNELS:
        raise ValueError("release channel must be development, testing, or stable")
    return {
        "development": "Development",
        "testing": "Testing",
        "stable": "Stable",
    }[channel]


def release_identity_version(channel: str = BUILD_CHANNEL) -> str:
    if channel not in SUPPORTED_BUILD_CHANNELS:
        raise ValueError("release channel must be development, testing, or stable")
    return TESTING_VERSION if channel == "testing" else CORE_VERSION


def release_version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("core version must use major.minor.patch")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def is_core_compatible(minimum: str, maximum: str) -> bool:
    current = release_version(CORE_VERSION)
    return release_version(minimum) <= current <= release_version(maximum)


def plugin_version_key(
    value: str,
) -> tuple[tuple[int, int, int], int, tuple[tuple[int, object], ...]]:
    without_build = value.split("+", 1)[0]
    release_text, separator, prerelease_text = without_build.partition("-")
    release = release_version(release_text)
    if not separator:
        return release, 1, ()
    prerelease: list[tuple[int, object]] = []
    for item in prerelease_text.split("."):
        prerelease.append((0, int(item)) if item.isdigit() else (1, item))
    return release, 0, tuple(prerelease)


def is_newer_plugin_version(candidate: str, current: str) -> bool:
    return plugin_version_key(candidate) > plugin_version_key(current)
