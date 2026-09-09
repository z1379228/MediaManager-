from __future__ import annotations

from unittest.mock import Mock

import pytest

from trusted_ui.idle_state import (
    BACKGROUND_IDLE_PROPERTY,
    PAUSE_IN_BACKGROUND_PROPERTY,
    IdleResourceController,
    is_background_idle,
)


def test_idle_controller_stops_only_active_repeating_timers(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    root = QWidget()
    repeating = QTimer(root)
    repeating.setInterval(1250)
    repeating.start()
    single_shot = QTimer(root)
    single_shot.setSingleShot(True)
    single_shot.start(10_000)
    paused_single_shot = QTimer(root)
    paused_single_shot.setSingleShot(True)
    paused_single_shot.setProperty(PAUSE_IN_BACKGROUND_PROPERTY, True)
    paused_single_shot.start(10_000)
    stopped = QTimer(root)
    stopped.setInterval(500)
    background = QTimer(root)
    background.setProperty("keepRunningInBackground", True)
    background.start(750)
    controller = IdleResourceController()

    try:
        assert controller.enter(root) == 2
        assert controller.idle
        assert root.property(BACKGROUND_IDLE_PROPERTY) is True
        assert is_background_idle(root)
        assert not repeating.isActive()
        assert single_shot.isActive()
        assert not paused_single_shot.isActive()
        assert not stopped.isActive()
        assert background.isActive()

        assert controller.leave() == 2
        assert not controller.idle
        assert root.property(BACKGROUND_IDLE_PROPERTY) is False
        assert not is_background_idle(root)
        assert repeating.isActive()
        assert repeating.interval() == 1250
        assert single_shot.isActive()
        assert paused_single_shot.isActive()
        assert not stopped.isActive()
        assert background.isActive()
    finally:
        repeating.stop()
        single_shot.stop()
        paused_single_shot.stop()
        background.stop()
        root.deleteLater()
        app.processEvents()


def test_idle_controller_is_idempotent(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    root = QWidget()
    timer = QTimer(root)
    timer.start(2000)
    controller = IdleResourceController()

    try:
        assert controller.enter(root) == 1
        assert controller.enter(root) == 0
        assert controller.leave() == 1
        assert controller.leave() == 0
    finally:
        timer.stop()
        root.deleteLater()
        app.processEvents()


def test_idle_controller_restores_a_playing_preview(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    class Player:
        def __init__(self) -> None:
            self.pause_calls = 0
            self.play_calls = 0

        def playbackState(self):
            return QMediaPlayer.PlaybackState.PlayingState

        def pause(self) -> None:
            self.pause_calls += 1

        def play(self) -> None:
            self.play_calls += 1

    player = Player()

    class Root:
        def findChildren(self, child_type):
            return [player] if child_type is QMediaPlayer else []

    controller = IdleResourceController()
    assert controller.enter(Root()) == 0
    assert player.pause_calls == 1

    assert controller.leave() == 0
    assert player.play_calls == 1
    app.processEvents()


def test_idle_controller_cancels_shared_thumbnail_work_and_cache(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    service = Mock()

    class Root:
        _media_manager_thumbnail_service = service

        def findChildren(self, _child_type):
            return []

    controller = IdleResourceController()
    assert controller.enter(Root()) == 0
    service.cancel_all_pending.assert_called_once_with()
    service.clear_cache.assert_called_once_with()
    controller.discard()
    app.processEvents()
