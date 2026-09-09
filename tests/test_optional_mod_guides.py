from __future__ import annotations

from unittest.mock import Mock

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.storage.paths import AppPaths
from trusted_ui.automation_panel import create_automation_panel
from trusted_ui.conversion_panel import create_conversion_panel
from trusted_ui.transcription_panel import create_transcription_panel


def test_optional_mod_panels_have_visible_chinese_usage_guides(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    panels = (
        create_conversion_panel(context),
        create_transcription_panel(context),
        create_automation_panel(context),
    )
    try:
        guides = [
            panel.findChild(QLabel, "modUsageGuide").text() for panel in panels
        ]
        assert all("使用方式" in guide for guide in guides)
        assert "FFmpeg" in guides[0]
        assert "whisper-cli" in guides[1]
        assert "對應 MOD" in guides[2]
        assert (
            panels[2].timer.property("keepRunningInBackground") is not True
        )
        assert callable(panels[2].observe_clipboard_change)
        assert panels[2].timer.interval() == 10_000
        observe_clipboard = Mock(return_value=0)
        context.automation.observe_clipboard = observe_clipboard
        panels[2].observe_clipboard_change()
        observe_clipboard.assert_called_once()
    finally:
        for panel in panels:
            panel.shutdown()
            panel.close()
            panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
