from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.downloads.provider_registry import ProviderStatus
from core.features import FeatureStatus
from trusted_ui.builtin_mod_control import (
    DISCOVERY_MOD_IDS,
    DOWNLOAD_MOD_IDS,
    FEATURE_MOD_IDS,
)
from trusted_ui.builtin_mod_panel import (
    BUILTIN_MOD_IDS,
    builtin_mod_rows,
    create_builtin_mod_panel,
)


def test_every_visible_builtin_mod_has_exactly_one_enable_route() -> None:
    groups = (DOWNLOAD_MOD_IDS, DISCOVERY_MOD_IDS, FEATURE_MOD_IDS)
    assert not any(left & right for index, left in enumerate(groups) for right in groups[index + 1 :])
    assert BUILTIN_MOD_IDS == frozenset().union(*groups)


def test_builtin_mod_rows_merge_download_and_discovery_statuses() -> None:
    rows = builtin_mod_rows(
        (
            ProviderStatus("youtube", "YouTube", True),
            ProviderStatus("generic-ytdlp", "Other Sites", False),
            ProviderStatus("bilibili", "Bilibili", False),
        ),
        (
            ProviderStatus("youtube-search", "Search", True),
            ProviderStatus("youtube-player", "Player", False),
            ProviderStatus("youtube-history", "History", False),
            ProviderStatus("youtube-recovery", "Recovery", True),
            ProviderStatus("youtube-similar", "Similar", True),
            ProviderStatus("youtube-auto-split", "Split", True),
        ),
        (
            FeatureStatus("media-convert", "Media Convert", False),
            FeatureStatus("speech-to-text", "Speech to Text", False),
            FeatureStatus("automation", "Automation", False),
        ),
    )
    assert len(rows) == 12
    assert all(row.available for row in rows)
    assert sum(row.enabled for row in rows) == 5
    assert rows[4].provider_id == "youtube-player"
    assert not rows[4].enabled


def test_builtin_mod_rows_keep_missing_expected_mod_visible() -> None:
    rows = builtin_mod_rows((), (), ())
    assert tuple(row.provider_id for row in rows) == (
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "youtube-search",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
        "media-convert",
        "speech-to-text",
        "automation",
    )
    assert not any(row.available for row in rows)


def test_builtin_mod_panel_renders_all_expected_rows(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget

    class StatusSource:
        def __init__(self, statuses: tuple[ProviderStatus, ...]) -> None:
            self._statuses = statuses

        def statuses(self) -> tuple[ProviderStatus, ...]:
            return self._statuses

    app = QApplication.instance() or QApplication([])
    context = SimpleNamespace(
        download_providers=StatusSource(
            (
                ProviderStatus("youtube", "YouTube", True),
                ProviderStatus("generic-ytdlp", "Other Sites", False),
                ProviderStatus("bilibili", "Bilibili", False),
            )
        ),
        discovery=StatusSource(
            tuple(
                ProviderStatus(provider_id, provider_id, True)
                for provider_id in (
                    "youtube-search",
                    "youtube-player",
                    "youtube-history",
                    "youtube-recovery",
                    "youtube-similar",
                    "youtube-auto-split",
                )
            )
        ),
        features=StatusSource(
            (
                FeatureStatus("media-convert", "Media Convert", False),
                FeatureStatus("speech-to-text", "Speech to Text", False),
                FeatureStatus("automation", "Automation", False),
            )
        ),
    )
    panel = create_builtin_mod_panel(context)
    table = panel.findChild(QTableWidget)
    summary = next(
        label
        for label in panel.findChildren(QLabel)
        if label.objectName() == "dependencySummary"
    )
    assert table.rowCount() == 12
    toggles = [
        button
        for button in panel.findChildren(QPushButton)
        if button.accessibleName().endswith("啟用狀態")
    ]
    assert len(toggles) == 12
    assert {button.text() for button in toggles} == {"啟用", "停用"}
    assert summary.text() == "內建 MOD 12/12 可用 · 7 個已啟用"
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_plugin_manager_defaults_to_actionable_builtin_mods(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget

    from core.bootstrap.bootstrap import Bootstrap
    from core.storage.paths import AppPaths
    from trusted_ui.plugin_manager import create_plugin_manager_dialog

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    dialog = create_plugin_manager_dialog(context)
    try:
        rows = builtin_mod_rows(
            context.download_providers.statuses(),
            context.discovery.statuses(),
            context.features.statuses(),
        )
        assert {row.provider_id for row in rows} == BUILTIN_MOD_IDS
        assert all(row.available for row in rows)
        tabs = dialog.findChild(QTabWidget, "pluginManagerTabs")
        assert tabs.currentIndex() == 1
        assert tabs.tabText(1) == "內建 MOD 狀態"
        assert any(
            label.text() == "尚無外部 MOD 介面"
            for label in dialog.findChildren(QLabel)
        )

        bilibili = next(
            toggle
            for toggle in dialog.findChildren(QPushButton)
            if toggle.accessibleName() == "Bilibili 啟用狀態"
        )
        assert not context.download_providers.is_enabled("bilibili")
        assert bilibili.text() == "啟用"
        bilibili.click()
        app.processEvents()
        assert context.download_providers.is_enabled("bilibili")
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
