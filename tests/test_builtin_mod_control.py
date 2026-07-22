from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.models import DownloadRequest, DownloadTask
from core.downloads.provider_registry import DownloadProviderRegistry, ProviderStatus
from core.events.event_bus import EventBus
from core.features import FeatureModRegistry, FeatureStatus
from core.features.registry import FeatureModToggleError
from core.storage.paths import AppPaths
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.download_panel import create_download_panel
from trusted_ui.search_panel import create_search_panel


def test_disabling_download_mod_cancels_owned_tasks_and_publishes(tmp_path) -> None:
    provider = Mock()
    provider.provider_id = "youtube"
    provider.display_name = "YouTube"
    provider.supports.side_effect = lambda url: "youtube.com" in url
    registry = DownloadProviderRegistry(tmp_path / "providers.json")
    registry.register(provider, enabled=True)
    task = DownloadTask(
        "task-1",
        DownloadRequest("https://youtube.com/watch?v=x", tmp_path),
    )
    queue = Mock()
    queue.snapshots.return_value = (task,)
    queue.cancel.return_value = True
    events = EventBus()
    received = []
    events.subscribe("builtin_mod.changed", received.append)
    context = SimpleNamespace(
        download_providers=registry,
        download_queue=queue,
        discovery=Mock(),
        audit=Mock(),
        events=events,
    )

    cancelled = set_builtin_mod_enabled(context, "youtube", False)

    assert cancelled == 1
    assert not registry.is_enabled("youtube")
    queue.cancel.assert_called_once_with("task-1")
    assert received == [
        {
            "provider_id": "youtube",
            "enabled": False,
            "cancelled_tasks": 1,
        }
    ]


def test_discovery_mod_toggle_uses_discovery_registry() -> None:
    discovery = Mock()
    discovery.statuses.return_value = (
        ProviderStatus("youtube-player", "YouTube Player", False),
    )
    downloads = Mock()
    downloads.statuses.return_value = (
        ProviderStatus("youtube", "YouTube", True),
    )
    context = SimpleNamespace(
        download_providers=downloads,
        download_queue=Mock(),
        discovery=discovery,
        audit=Mock(),
        events=EventBus(),
    )

    assert set_builtin_mod_enabled(context, "youtube-player", True) == 0
    discovery.set_enabled.assert_called_once_with("youtube-player", True)


def test_site_child_requires_enabled_parent_and_parent_disable_cascades(
    tmp_path, monkeypatch
) -> None:
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    context = Bootstrap(portable=True).initialize(start_background=False)
    try:
        set_builtin_mod_enabled(context, "bilibili", False)
        with pytest.raises(RuntimeError, match="bilibili 主 MOD"):
            set_builtin_mod_enabled(context, "bilibili-search", True)

        set_builtin_mod_enabled(context, "bilibili", True)
        set_builtin_mod_enabled(context, "bilibili-search", True)
        set_builtin_mod_enabled(context, "bilibili-danmaku", True)
        assert context.discovery.is_enabled("bilibili-search")
        assert context.features.is_enabled("bilibili-danmaku")

        set_builtin_mod_enabled(context, "bilibili", False)
        assert not context.download_providers.is_enabled("bilibili")
        assert not context.discovery.is_enabled("bilibili-search")
        assert not context.features.is_enabled("bilibili-danmaku")

    finally:
        context.lifecycle.shutdown()


def test_feature_mod_toggle_uses_shared_event_and_reports_cancelled_work() -> None:
    features = Mock()
    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", True),
    )
    features.set_enabled.return_value = 2
    events = EventBus()
    received = []
    events.subscribe("builtin_mod.changed", received.append)
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=events,
    )

    assert set_builtin_mod_enabled(context, "media-convert", False) == 2
    features.set_enabled.assert_called_once_with("media-convert", False)
    assert received == [
        {
            "provider_id": "media-convert",
            "enabled": False,
            "cancelled_tasks": 2,
        }
    ]


def test_feature_child_uses_generic_parent_gate_and_disable_cascade() -> None:
    features = Mock()
    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", False),
        FeatureStatus("media-ad-trim", "Local Ad Segment Trim", False),
    )
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
    )

    with pytest.raises(RuntimeError, match="media-convert 主 MOD"):
        set_builtin_mod_enabled(context, "media-ad-trim", True)

    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", True),
        FeatureStatus("media-ad-trim", "Local Ad Segment Trim", True),
    )
    features.set_enabled.return_value = 2
    assert set_builtin_mod_enabled(context, "media-convert", False) == 4
    assert features.set_enabled.call_args_list == [
        call("media-convert", False),
        call("media-ad-trim", False),
    ]


def test_parent_disable_rolls_back_when_child_registry_fails() -> None:
    features = Mock()
    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", True),
        FeatureStatus("media-ad-trim", "Local Ad Segment Trim", True),
    )
    calls: list[tuple[str, bool]] = []

    def set_enabled(provider_id: str, enabled: bool) -> int:
        calls.append((provider_id, enabled))
        if len(calls) == 2:
            raise RuntimeError("child registry unavailable")
        return 0

    features.set_enabled.side_effect = set_enabled
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
    )

    with pytest.raises(RuntimeError, match="已回復"):
        set_builtin_mod_enabled(context, "media-convert", False)

    assert calls == [
        ("media-convert", False),
        ("media-ad-trim", False),
        ("media-ad-trim", True),
        ("media-convert", True),
    ]
    context.audit.write.assert_any_call(
        "builtin_mod.enabled_change_failed",
        provider_id="media-convert",
        enabled=False,
        affected_children=("media-ad-trim",),
        changed=("media-convert", "media-ad-trim"),
        error_type="RuntimeError",
    )


def test_parent_disable_compensates_registry_that_mutates_before_save_failure() -> None:
    states = {"media-convert": True, "media-ad-trim": True}
    features = Mock()
    features.statuses.side_effect = lambda: tuple(
        FeatureStatus(provider_id, provider_id, enabled)
        for provider_id, enabled in states.items()
    )
    failed = False

    def set_enabled(provider_id: str, enabled: bool) -> int:
        nonlocal failed
        states[provider_id] = enabled
        if provider_id == "media-ad-trim" and not enabled and not failed:
            failed = True
            raise OSError("state persistence failed after mutation")
        return 0

    features.set_enabled.side_effect = set_enabled
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
    )

    with pytest.raises(RuntimeError, match="已回復"):
        set_builtin_mod_enabled(context, "media-convert", False)

    assert states == {"media-convert": True, "media-ad-trim": True}


def test_parent_disable_reports_incomplete_rollback() -> None:
    features = Mock()
    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", True),
        FeatureStatus("media-ad-trim", "Local Ad Segment Trim", True),
    )
    calls: list[tuple[str, bool]] = []

    def set_enabled(provider_id: str, enabled: bool) -> int:
        calls.append((provider_id, enabled))
        if len(calls) == 2:
            raise RuntimeError("child registry unavailable")
        if len(calls) == 4:
            raise RuntimeError("parent rollback unavailable")
        return 0

    features.set_enabled.side_effect = set_enabled
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
        builtin_mod_snapshot=object(),
    )

    with pytest.raises(RuntimeError, match="回復不完整") as captured:
        set_builtin_mod_enabled(context, "media-convert", False)

    assert "已回復" not in str(captured.value)
    assert calls == [
        ("media-convert", False),
        ("media-ad-trim", False),
        ("media-ad-trim", True),
        ("media-convert", True),
    ]
    assert context.builtin_mod_snapshot is None
    context.audit.write.assert_any_call(
        "builtin_mod.rollback_failed",
        provider_id="media-convert",
        error_type="RuntimeError",
    )


def test_parent_disable_reports_cancelled_work_as_irreversible() -> None:
    features = Mock()
    features.statuses.return_value = (
        FeatureStatus("media-convert", "Media Convert", True),
        FeatureStatus("media-ad-trim", "Local Ad Segment Trim", True),
    )
    calls: list[tuple[str, bool]] = []

    def set_enabled(provider_id: str, enabled: bool) -> int:
        calls.append((provider_id, enabled))
        if len(calls) == 1:
            return 2
        if len(calls) == 2:
            raise RuntimeError("child registry unavailable")
        return 0

    features.set_enabled.side_effect = set_enabled
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
        builtin_mod_snapshot=object(),
    )

    with pytest.raises(RuntimeError, match="回復不完整") as captured:
        set_builtin_mod_enabled(context, "media-convert", False)

    assert "已取消 2 個工作，無法復原" in str(captured.value)
    context.audit.write.assert_any_call(
        "builtin_mod.rollback_irreversible",
        provider_id="media-convert",
        cancelled_work=2,
    )
    assert context.builtin_mod_snapshot is None


def test_failed_feature_disable_reports_irreversible_side_effect_unknown(
    tmp_path,
) -> None:
    class PartiallyFailingFeature:
        provider_id = "media-convert"
        display_name = "Media Convert"
        available = True

        def __init__(self) -> None:
            self.is_enabled = False
            self.cancelled = 0

        def set_enabled(self, enabled: bool) -> int:
            if not enabled and self.is_enabled:
                self.cancelled += 1
                self.is_enabled = False
                raise RuntimeError("failed after cancelling work")
            self.is_enabled = enabled
            return 0

        def close(self) -> None:
            self.is_enabled = False

    feature = PartiallyFailingFeature()
    features = FeatureModRegistry(tmp_path / "feature-state.json")
    features.register(feature)
    features.set_enabled("media-convert", True)
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=Mock(),
        features=features,
        audit=Mock(),
        events=EventBus(),
        builtin_mod_snapshot=object(),
    )

    with pytest.raises(RuntimeError, match="不可逆副作用狀態未知") as captured:
        set_builtin_mod_enabled(context, "media-convert", False)

    assert isinstance(captured.value.__cause__, FeatureModToggleError)
    assert feature.is_enabled
    assert feature.cancelled == 1
    assert context.builtin_mod_snapshot is None
    context.audit.write.assert_any_call(
        "builtin_mod.rollback_irreversible_unknown",
        provider_id="media-convert",
        failed_operation="media-convert",
    )


def test_builtin_mod_events_sync_download_and_search_controls(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    # New profiles now enable every built-in MOD except Automation and Speech
    # to Text. Establish this test's disabled starting state explicitly so it
    # continues to exercise live event synchronization rather than defaults.
    set_builtin_mod_enabled(context, "bilibili", False)
    set_builtin_mod_enabled(context, "youtube-player", False)
    download_panel = create_download_panel(context, site_family="bilibili")
    search_panel = create_search_panel(context)
    download_panel.timer.stop()
    try:
        assert not download_panel.enabled.isChecked()
        assert not search_panel.video_enabled.isChecked()
        assert not search_panel.bilibili_search_enabled.isVisible()

        set_builtin_mod_enabled(context, "bilibili", True)
        set_builtin_mod_enabled(context, "youtube-player", True)
        app.processEvents()

        assert download_panel.enabled.isChecked()
        assert search_panel.video_enabled.isChecked()
        assert search_panel.bilibili_search_enabled.isVisible()

        set_builtin_mod_enabled(context, "bilibili-search", True)
        set_builtin_mod_enabled(context, "bilibili", False)
        app.processEvents()
        assert not context.discovery.is_enabled("bilibili-search")
        assert not search_panel.bilibili_search_enabled.isVisible()
    finally:
        search_panel.shutdown()
        search_panel.close()
        search_panel.deleteLater()
        download_panel.close()
        download_panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
