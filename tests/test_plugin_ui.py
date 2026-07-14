from __future__ import annotations

import json

import pytest
from unittest.mock import Mock

from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry
from core.plugins.ui_descriptor import PluginPage, PluginUIError, PluginUIService
from trusted_ui.mod_pages import create_mod_pages_panel
from trusted_ui.theme import apply_application_theme


def descriptor(**changes):
    value = {
        "schema_version": 1,
        "page_id": "example.page",
        "title": "Example",
        "blocks": [{"type": "heading", "text": "Overview"}, {"type": "text", "text": "Safe content"}],
    }
    value.update(changes)
    return value


def record(enabled=True):
    return PluginRecord("example.plugin", "1.0.0", enabled, PendingAction.NONE, "TRUSTED_PUBLISHER", "trusted.example", (), "hash")


def test_descriptor_accepts_bounded_static_blocks() -> None:
    page = PluginPage.from_dict(descriptor())
    assert page.page_id == "example.page"
    assert tuple(block.type for block in page.blocks) == ("heading", "text")


def test_localized_descriptor_supports_only_four_languages_and_falls_back() -> None:
    localized = {
        "schema_version": 2,
        "page_id": "example.page",
        "default_locale": "en",
        "translations": {
            "en": {
                "title": "Example",
                "blocks": [{"type": "text", "text": "English"}],
            },
            "zh-TW": {
                "title": "範例",
                "blocks": [{"type": "text", "text": "繁體中文"}],
            },
        },
    }

    translated = PluginPage.from_dict(localized, locale="zh-TW")
    fallback = PluginPage.from_dict(localized, locale="ja")

    assert translated.title == "範例" and translated.locale == "zh-TW"
    assert fallback.title == "Example" and fallback.locale == "en"
    assert translated.available_locales == ("en", "zh-TW")


def test_localized_descriptor_rejects_unplanned_language() -> None:
    localized = {
        "schema_version": 2,
        "page_id": "example.page",
        "default_locale": "fr",
        "translations": {
            "fr": {
                "title": "Exemple",
                "blocks": [{"type": "text", "text": "Texte"}],
            }
        },
    }

    with pytest.raises(PluginUIError, match="languages"):
        PluginPage.from_dict(localized)


@pytest.mark.parametrize("change", [
    {"blocks": [{"type": "html", "text": "<b>x</b>"}]},
    {"blocks": [{"type": "text", "text": "x" * 2001}]},
    {"url": "https://example.invalid"},
])
def test_descriptor_rejects_active_content_and_unknown_fields(change) -> None:
    with pytest.raises(PluginUIError):
        PluginPage.from_dict(descriptor(**change))


def test_service_only_lists_enabled_plugin_pages(tmp_path) -> None:
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry.upsert(record())
    root = tmp_path / "mod" / "installed" / "example.plugin"
    root.mkdir(parents=True)
    (root / "ui.json").write_text(json.dumps(descriptor()), encoding="utf-8")
    manager = Mock()
    manager.verify_directory.return_value = ()
    service = PluginUIService(tmp_path / "mod", registry, manager)
    assert service.list_pages()[0][0] == "example.plugin"
    registry.set_enabled("example.plugin", False)
    assert service.list_pages() == ()
    registry.close()


def test_service_rejects_page_when_installed_files_fail_verification(tmp_path) -> None:
    registry = PluginRegistry(tmp_path / "mod" / "registry.sqlite3")
    registry.upsert(record())
    root = tmp_path / "mod" / "installed" / "example.plugin"
    root.mkdir(parents=True)
    (root / "ui.json").write_text(json.dumps(descriptor()), encoding="utf-8")
    manager = Mock()
    manager.verify_directory.return_value = ("installed file hash mismatch: ui.json",)
    service = PluginUIService(tmp_path / "mod", registry, manager)
    with pytest.raises(PluginUIError, match="verification failed"):
        service.load_page("example.plugin")
    registry.close()


def test_external_mod_page_uses_dark_accessible_scroll_surface(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea

    app = QApplication.instance() or QApplication([])
    apply_application_theme(app)
    context = Mock()
    context.plugin_ui.list_pages.return_value = ()
    panel = create_mod_pages_panel(context)
    try:
        scroll = panel.findChild(QScrollArea, "modPageScroll")
        selector = panel.findChild(QComboBox)
        assert scroll is not None
        assert selector is not None
        assert scroll.accessibleName() == "外部 MOD 介面內容"
        assert selector.accessibleName() == "外部 MOD 介面選擇"
        assert (
            scroll.viewport().palette().color(QPalette.ColorRole.Base).lightness()
            < 40
        )
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()

