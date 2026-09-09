from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from trusted_ui.idle_state import BACKGROUND_IDLE_PROPERTY
from trusted_ui.media_preview_controls import (
    PreviewSource,
    create_media_preview_controls,
)


def test_prepared_preview_is_discarded_when_window_is_background_idle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    root = QWidget()
    root.setProperty(BACKGROUND_IDLE_PROPERTY, True)
    controls = create_media_preview_controls(
        root,
        source=lambda: PreviewSource("https://example.com/watch?v=1"),
        audio_provider=lambda _url: Mock(),
        video_provider=Mock,
        audio_available=lambda: True,
        video_available=lambda: True,
        object_prefix="test",
    )
    owner = Mock()
    preview_path = tmp_path / "preview.mp3"
    controls.generation = 4
    controls.busy_kind = "audio"

    try:
        assert controls.audio_player is None
        controls.show_prepared_preview(
            "audio",
            4,
            owner,
            str(preview_path),
            "",
        )

        owner.cleanup_audio_preview.assert_called_once_with(str(preview_path))
        assert controls.busy_kind == ""
        assert controls.audio_path == ""
        assert "背景待機" in controls.status.text()
    finally:
        controls.shutdown()
        root.deleteLater()
        app.processEvents()


def test_audio_player_is_created_only_for_valid_foreground_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    root = QWidget()
    controls = create_media_preview_controls(
        root,
        source=lambda: PreviewSource("https://example.com/watch?v=1"),
        audio_provider=lambda _url: Mock(),
        video_provider=Mock,
        audio_available=lambda: True,
        video_available=lambda: True,
        object_prefix="lazy",
    )
    owner = Mock()
    preview_path = tmp_path / "preview.mp3"
    preview_path.write_bytes(b"preview")
    controls.generation = 1
    controls.busy_kind = "audio"

    try:
        assert controls.audio_player is None
        assert controls.audio_output is None

        controls.show_prepared_preview(
            "audio",
            1,
            owner,
            str(preview_path),
            "",
        )

        assert controls.audio_player is not None
        assert controls.audio_output is not None
        controls.stop_audio()
        assert controls.audio_player is None
        assert controls.audio_output is None
        owner.cleanup_audio_preview.assert_called_once_with(str(preview_path))
    finally:
        controls.shutdown()
        root.deleteLater()
        app.processEvents()
