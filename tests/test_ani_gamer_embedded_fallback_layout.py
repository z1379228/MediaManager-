from __future__ import annotations

import sys
from types import ModuleType

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.storage.paths import AppPaths
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled


def _install_fake_webengine(monkeypatch, widget_class):
    class FakeSignal:
        def __init__(self) -> None:
            self.callbacks: list[object] = []

        def connect(self, callback) -> None:
            self.callbacks.append(callback)

    class FakePage:
        def __init__(self, _parent=None) -> None:
            pass

        def runJavaScript(self, _script, _world_id, callback) -> None:
            callback(None)

    class FakeSettings:
        def setAttribute(self, _attribute, _enabled) -> None:
            pass

    class FakeWebEngineView(widget_class):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.loadFinished = FakeSignal()
            self.renderProcessTerminated = FakeSignal()
            self._page = None
            self._settings = FakeSettings()

        def setPage(self, page) -> None:
            self._page = page

        def page(self):
            return self._page

        def settings(self):
            return self._settings

        def setUrl(self, url) -> None:
            self.loaded_url = url

    class FakeWebAttribute:
        JavascriptEnabled = object()
        LocalStorageEnabled = object()
        FullScreenSupportEnabled = object()
        PlaybackRequiresUserGesture = object()

    class FakeWebEngineSettings:
        WebAttribute = FakeWebAttribute

    core_module = ModuleType("PySide6.QtWebEngineCore")
    core_module.QWebEnginePage = FakePage
    core_module.QWebEngineSettings = FakeWebEngineSettings
    widgets_module = ModuleType("PySide6.QtWebEngineWidgets")
    widgets_module.QWebEngineView = FakeWebEngineView
    monkeypatch.setitem(sys.modules, core_module.__name__, core_module)
    monkeypatch.setitem(sys.modules, widgets_module.__name__, widgets_module)
    return FakeWebEngineView


def test_embedded_system_browser_fallback_stays_above_web_view(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton, QWidget

    fake_web_view_class = _install_fake_webengine(monkeypatch, QWidget)
    from trusted_ui.ani_gamer_workspace import create_ani_gamer_workspace

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    set_builtin_mod_enabled(context, "ani-gamer", True)
    panel = create_ani_gamer_workspace(context)
    try:
        panel.open_embedded_url(
            "https://ani.gamer.com.tw/animeVideo.php?sn=49944",
            "AniGamer episode",
        )
        app.processEvents()
        dialog = panel._browser_dialogs[-1]
        fallback = next(
            (
                button
                for button in dialog.findChildren(QPushButton)
                if button.property("controlId")
                == "aniGamerEmbeddedSystemBrowserFallback"
            ),
            None,
        )
        close_button = dialog.findChild(
            QPushButton,
            "aniGamerEmbeddedCloseButton",
        )
        view = dialog.findChild(fake_web_view_class)

        assert fallback is not None
        assert fallback.objectName() == "primary"
        assert fallback.accessibleName()
        assert close_button is not None
        assert close_button.accessibleName()
        assert view is not None
        assert fallback.isVisibleTo(dialog)
        assert fallback.geometry().bottom() < view.geometry().top()
    finally:
        for dialog in tuple(panel._browser_dialogs):
            dialog.close()
            dialog.deleteLater()
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
