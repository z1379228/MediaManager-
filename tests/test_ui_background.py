from __future__ import annotations

import json
from pathlib import Path

import pytest

from trusted_ui.background import (
    appearance_settings_path,
    clear_background_copy,
    create_background_widget,
    load_background_path,
    save_background_path,
    store_background_copy,
    valid_background_path,
)


def test_background_preference_round_trip_and_reset(tmp_path: Path) -> None:
    image = tmp_path / "background.png"
    image.write_bytes(b"not-decoded-in-preference-test")
    assert valid_background_path(image) == image.resolve()
    save_background_path(tmp_path / "settings", image)
    assert load_background_path(tmp_path / "settings") == image.resolve()
    save_background_path(tmp_path / "settings", None)
    assert load_background_path(tmp_path / "settings") is None


def test_background_preference_rejects_unsupported_or_invalid_data(
    tmp_path: Path,
) -> None:
    unsupported = tmp_path / "background.txt"
    unsupported.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        save_background_path(tmp_path / "settings", unsupported)
    settings = appearance_settings_path(tmp_path / "settings")
    settings.parent.mkdir(exist_ok=True)
    settings.write_text(json.dumps({"background_image": 42}), encoding="utf-8")
    assert load_background_path(settings.parent) is None


def test_managed_background_copy_survives_source_removal(tmp_path: Path) -> None:
    source = tmp_path / "selected.jpg"
    source.write_bytes(b"managed background")
    settings = tmp_path / "settings"

    stored = store_background_copy(settings, source)
    assert stored.parent == settings.resolve()
    assert stored.read_bytes() == b"managed background"
    source.unlink()
    assert load_background_path(settings) == stored

    clear_background_copy(settings)
    assert load_background_path(settings) is None
    assert not stored.exists()


def test_background_widget_decodes_images_before_accepting_them(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    widget = create_background_widget(None)
    invalid = tmp_path / "invalid.png"
    invalid.write_bytes(b"not an image")
    assert not widget.set_background(invalid)

    image_path = tmp_path / "valid.png"
    image = QImage(32, 24, QImage.Format.Format_RGB32)
    image.fill(QColor("#345678"))
    assert image.save(str(image_path))
    assert widget.set_background(image_path)
    widget.resize(320, 180)
    assert not widget.grab().isNull()
    widget.close()
    widget.deleteLater()
    app.processEvents()
