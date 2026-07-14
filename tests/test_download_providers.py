from __future__ import annotations

from threading import Event
from unittest.mock import Mock

import pytest

from contracts.download_capability_v2 import DownloadCapabilityError, DownloadCapabilityV2
from core.downloads.models import DownloadRequest
from core.downloads.provider_registry import DownloadProviderRegistry, ProviderUnavailableError


def provider(provider_id="youtube"):
    value = Mock()
    value.provider_id = provider_id
    value.display_name = "YouTube"
    value.supports.side_effect = lambda url: "youtube" in url
    value.analyze.return_value = {"title": "Example"}
    value.download.return_value = "result.mp4"
    return value


def test_registry_routes_only_to_enabled_provider(tmp_path) -> None:
    registry = DownloadProviderRegistry()
    youtube = provider()
    registry.register(youtube)
    with pytest.raises(ProviderUnavailableError):
        registry.analyze("https://youtube.com/watch?v=x")
    registry.set_enabled("youtube", True)
    assert registry.analyze("https://youtube.com/watch?v=x")["title"] == "Example"
    youtube.playlist.return_value = ()
    assert registry.playlist("https://youtube.com/playlist?list=x") == ()
    request = DownloadRequest("https://youtube.com/watch?v=x", tmp_path)
    assert registry.download(request, Mock(), Event()) == "result.mp4"


def test_registry_identifies_disabled_provider_owner() -> None:
    registry = DownloadProviderRegistry()
    registry.register(provider(), enabled=False)

    assert (
        registry.matching_provider_id("https://youtube.com/watch?v=x")
        == "youtube"
    )
    assert registry.matching_provider_id("https://example.com/video") is None


def test_registry_rejects_duplicate_and_unknown_provider() -> None:
    registry = DownloadProviderRegistry()
    registry.register(provider())
    with pytest.raises(ValueError):
        registry.register(provider())
    with pytest.raises(KeyError):
        registry.set_enabled("missing", True)


def test_registry_enforces_registered_download_capability(tmp_path) -> None:
    registry = DownloadProviderRegistry()
    registry.register(provider(), enabled=True)
    capability = DownloadCapabilityV2(
        "youtube",
        ("youtube",),
        ("audio-mp3",),
        ("none",),
        ("none",),
        True,
        False,
        True,
        20,
    )
    registry.register_capability(capability)
    assert registry.capability_for("https://youtube.com/watch?v=x") == capability
    with pytest.raises(ValueError, match="already registered"):
        registry.register_capability(capability)
    with pytest.raises(DownloadCapabilityError, match="format"):
        registry.download(
            DownloadRequest("https://youtube.com/watch?v=x", tmp_path),
            Mock(),
            Event(),
        )


def test_close_disables_and_closes_every_provider() -> None:
    registry = DownloadProviderRegistry()
    youtube = provider()
    registry.register(youtube, enabled=True)
    registry.close()
    youtube.close.assert_called_once_with()
    assert not registry.is_enabled("youtube")


def test_provider_enabled_state_persists(tmp_path) -> None:
    state = tmp_path / "providers.json"
    registry = DownloadProviderRegistry(state)
    registry.register(provider(), enabled=True)
    registry.set_enabled("youtube", False)
    restored = DownloadProviderRegistry(state)
    restored.register(provider(), enabled=True)
    assert not restored.is_enabled("youtube")

