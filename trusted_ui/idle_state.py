"""Suspend invisible UI polling while background services remain available."""

from __future__ import annotations

import gc
import sys


BACKGROUND_IDLE_PROPERTY = "mediaManagerBackgroundIdle"
PAUSE_IN_BACKGROUND_PROPERTY = "pauseInBackground"


def is_background_idle(target: object) -> bool:
    """Return whether a QObject or one of its owners is in background idle."""

    current: object | None = target
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        property_reader = getattr(current, "property", None)
        if callable(property_reader):
            try:
                if property_reader(BACKGROUND_IDLE_PROPERTY) is True:
                    return True
            except RuntimeError:
                return False
        parent_reader = getattr(current, "parent", None)
        if not callable(parent_reader):
            break
        try:
            current = parent_reader()
        except RuntimeError:
            break
    return False


class IdleResourceController:
    """Pause active repeating Qt timers and release disposable UI caches."""

    def __init__(self) -> None:
        self._suspended: list[tuple[object, int]] = []
        self._paused_players: list[object] = []
        self._root: object | None = None
        self.idle = False

    @property
    def suspended_timer_count(self) -> int:
        """Return the bounded timer count currently held for restoration."""

        return len(self._suspended)

    def enter(self, root: object) -> int:
        if self.idle:
            return 0
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QPixmapCache

        self.idle = True
        self._root = root
        property_writer = getattr(root, "setProperty", None)
        if callable(property_writer):
            property_writer(BACKGROUND_IDLE_PROPERTY, True)
        for timer in root.findChildren(QTimer):
            if (
                not timer.isActive()
                or timer.property("keepRunningInBackground") is True
                or (
                    timer.isSingleShot()
                    and timer.property(PAUSE_IN_BACKGROUND_PROPERTY) is not True
                )
            ):
                continue
            interval = (
                max(1, timer.remainingTime())
                if timer.isSingleShot()
                else timer.interval()
            )
            self._suspended.append((timer, interval))
            timer.stop()

        multimedia = sys.modules.get("PySide6.QtMultimedia")
        QMediaPlayer = getattr(multimedia, "QMediaPlayer", None)
        if QMediaPlayer is not None:
            for player in root.findChildren(QMediaPlayer):
                if (
                    player.playbackState()
                    == QMediaPlayer.PlaybackState.PlayingState
                ):
                    player.pause()
                    self._paused_players.append(player)

        thumbnail_service = getattr(
            root,
            "_media_manager_thumbnail_service",
            None,
        )
        if thumbnail_service is not None:
            thumbnail_service.cancel_all_pending()
            thumbnail_service.clear_cache()

        QPixmapCache.clear()
        gc.collect()
        return len(self._suspended)

    def leave(self) -> int:
        if not self.idle:
            return 0
        suspended = tuple(self._suspended)
        paused_players = tuple(self._paused_players)
        self._suspended.clear()
        self._paused_players.clear()
        self.idle = False
        root = self._root
        self._root = None
        property_writer = getattr(root, "setProperty", None)
        if callable(property_writer):
            try:
                property_writer(BACKGROUND_IDLE_PROPERTY, False)
            except RuntimeError:
                pass
        restarted = 0
        for timer, interval in suspended:
            try:
                timer.start(interval)
            except RuntimeError:
                continue
            restarted += 1
        for player in paused_players:
            try:
                player.play()
            except RuntimeError:
                continue
        return restarted

    def discard(self) -> None:
        """Forget stopped timers during final shutdown without restarting them."""

        self._suspended.clear()
        self._paused_players.clear()
        root = self._root
        self._root = None
        property_writer = getattr(root, "setProperty", None)
        if callable(property_writer):
            try:
                property_writer(BACKGROUND_IDLE_PROPERTY, False)
            except RuntimeError:
                pass
        self.idle = False
