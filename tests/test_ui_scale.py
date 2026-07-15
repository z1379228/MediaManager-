from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.settings import (
    Settings,
    SettingsService,
    normalized_download_workers,
)
from core.storage.paths import AppPaths
from trusted_ui.download_panel import create_download_panel
from trusted_ui.search_panel import create_search_panel
from trusted_ui.theme import (
    apply_application_theme,
    application_stylesheet,
    normalized_ui_scale,
    ui_scale_stylesheet,
)


def test_ui_scale_is_normalized_and_changes_font_density() -> None:
    assert normalized_ui_scale("compact") == "compact"
    assert normalized_ui_scale("standard") == "standard"
    assert normalized_ui_scale("large") == "large"
    assert normalized_ui_scale("unknown") == "standard"
    assert normalized_ui_scale(16) == "standard"

    assert "font-size: 13px" in ui_scale_stylesheet("compact")
    assert ui_scale_stylesheet("standard") == ""
    assert "font-size: 15px" in ui_scale_stylesheet("large")
    assert application_stylesheet("unknown") == application_stylesheet("standard")
    assert "QComboBox QAbstractItemView" in application_stylesheet()
    assert "QFileDialog" in application_stylesheet()


def test_application_palette_keeps_popup_and_viewport_surfaces_dark(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea

    app = QApplication.instance() or QApplication([])
    apply_application_theme(app)
    palette = app.palette()
    assert palette.color(QPalette.ColorRole.Window).name() == "#0a0f1d"
    assert palette.color(QPalette.ColorRole.Base).name() == "#080f1c"

    combo = QComboBox()
    combo.addItems(("MP3", "MP4"))
    scroll = QScrollArea()
    assert combo.view().palette().color(QPalette.ColorRole.Base).lightness() < 40
    assert scroll.viewport().palette().color(QPalette.ColorRole.Base).lightness() < 40
    combo.deleteLater()
    scroll.deleteLater()


def test_dark_palette_text_contrast_exceeds_accessibility_baseline(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication

    def luminance(color) -> float:
        channels = []
        for value in (color.redF(), color.greenF(), color.blueF()):
            channels.append(
                value / 12.92
                if value <= 0.04045
                else ((value + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    app = QApplication.instance() or QApplication([])
    apply_application_theme(app)
    palette = app.palette()
    foreground = luminance(palette.color(QPalette.ColorRole.Text))
    background = luminance(palette.color(QPalette.ColorRole.Base))
    ratio = (max(foreground, background) + 0.05) / (
        min(foreground, background) + 0.05
    )
    assert ratio >= 7.0


def test_core_panels_expose_accessible_controls_at_minimum_width(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    apply_application_theme(app)
    context = Bootstrap(portable=True).initialize(start_background=False)
    download = create_download_panel(context)
    search = create_search_panel(context)
    download.timer.stop()
    try:
        for panel in (download, search):
            panel.resize(916, 500)
            panel.show()
        app.processEvents()
        assert download.urls.accessibleName() == "YouTube 下載網址清單"
        assert download.format_preset.accessibleName() == "下載格式"
        assert download.table.accessibleName() == "下載工作佇列"
        assert search.query.accessibleName() == "單一網站搜尋文字"
        assert search.search_source.accessibleName() == "搜尋來源"
        assert search.next_page_button.accessibleName() == "搜尋下一頁"
        assert search.limit.accessibleName() == "搜尋結果數量"
        assert search.table.accessibleName() == "單一網站搜尋結果"
        assert (
            download.scroll_area.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
    finally:
        search.shutdown()
        search.close()
        download.close()
        search.deleteLater()
        download.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_ui_scale_setting_round_trip_and_legacy_default(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.save(Settings(ui_scale="large"))
    assert service.load().ui_scale == "large"

    service.path.write_text(json.dumps({"language": "zh-TW"}), encoding="utf-8")
    assert service.load().ui_scale == "standard"


def test_download_worker_setting_is_bounded() -> None:
    assert normalized_download_workers(1) == 1
    assert normalized_download_workers(4) == 4
    assert normalized_download_workers(0) == 1
    assert normalized_download_workers(99) == 4
    assert normalized_download_workers(True) == 2
    assert normalized_download_workers("4") == 2


def test_large_ui_keeps_download_controls_scrollable(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(application_stylesheet("large"))
    context = Bootstrap(portable=True).initialize()
    panel = create_download_panel(context)
    panel.timer.stop()
    try:
        panel.resize(916, 450)
        panel.show()
        app.processEvents()

        scroll = panel.scroll_area
        assert scroll.verticalScrollBar().maximum() > 0
        enabled_bottom = panel.enabled.mapTo(panel, QPoint(0, 0)).y() + panel.enabled.height()
        output_top = panel.output.mapTo(panel, QPoint(0, 0)).y()
        assert output_top >= enabled_bottom
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
