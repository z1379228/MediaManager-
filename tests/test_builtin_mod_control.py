from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.models import DownloadRequest, DownloadTask
from core.downloads.provider_registry import DownloadProviderRegistry, ProviderStatus
from core.events.event_bus import EventBus
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
    context = SimpleNamespace(
        download_providers=Mock(),
        download_queue=Mock(),
        discovery=discovery,
        audit=Mock(),
        events=EventBus(),
    )

    assert set_builtin_mod_enabled(context, "youtube-player", True) == 0
    discovery.set_enabled.assert_called_once_with("youtube-player", True)


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
    download_panel = create_download_panel(context)
    search_panel = create_search_panel(context)
    download_panel.timer.stop()
    try:
        assert not download_panel.bilibili_enabled.isChecked()
        assert not search_panel.video_enabled.isChecked()

        set_builtin_mod_enabled(context, "bilibili", True)
        set_builtin_mod_enabled(context, "youtube-player", True)
        app.processEvents()

        assert download_panel.bilibili_enabled.isChecked()
        assert search_panel.video_enabled.isChecked()
    finally:
        search_panel.shutdown()
        search_panel.close()
        search_panel.deleteLater()
        download_panel.close()
        download_panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
