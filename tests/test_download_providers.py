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
    with pytest.raises(
        ProviderUnavailableError,
        match="YouTube MOD 尚未啟用",
    ):
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


def test_registry_exposes_failed_provider_reason_for_owned_hosts() -> None:
    registry = DownloadProviderRegistry()
    registry.register_unavailable(
        "youtube",
        "YouTube",
        "integrity mismatch: provider.py",
        hosts=("youtube.com", "music.youtube.com"),
    )

    status = registry.statuses()[0]
    assert status.provider_id == "youtube"
    assert not status.available
    assert not status.enabled
    assert status.reason == "integrity mismatch: provider.py"
    assert (
        registry.matching_provider_id(
            "https://music.youtube.com/playlist?list=example"
        )
        == "youtube"
    )
    with pytest.raises(
        ProviderUnavailableError,
        match="YouTube MOD 初始化失敗.*integrity mismatch",
    ):
        registry.provider_for(
            "https://music.youtube.com/playlist?list=example"
        )
    with pytest.raises(ProviderUnavailableError, match="初始化失敗"):
        registry.set_enabled("youtube", True)


def test_registry_rejects_duplicate_and_unknown_provider() -> None:
    registry = DownloadProviderRegistry()
    with pytest.raises(
        ProviderUnavailableError,
        match="沒有已啟用的下載 MOD 支援此網址",
    ):
        registry.provider_for("https://example.com/video")
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


def test_playlist_and_batch_limits_are_enforced_before_queueing(tmp_path) -> None:
    registry = DownloadProviderRegistry()
    youtube = provider()
    youtube.playlist.return_value = ()
    registry.register(youtube, enabled=True)
    capability = DownloadCapabilityV2(
        "youtube",
        ("youtube",),
        ("best",),
        ("none",),
        ("none",),
        True,
        False,
        True,
        2,
    )
    registry.register_capability(capability)

    registry.playlist("https://youtube.com/playlist?list=x", limit=500)
    youtube.playlist.assert_called_once_with(
        "https://youtube.com/playlist?list=x", limit=2
    )

    requests = tuple(
        DownloadRequest(f"https://youtube.com/watch?v={index}", tmp_path)
        for index in range(3)
    )
    with pytest.raises(DownloadCapabilityError, match="exceeds youtube limit"):
        registry.validate_batch(requests)


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

