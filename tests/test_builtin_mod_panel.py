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
from trusted_ui.planned_mod_catalog import PLANNED_MODS


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
            ProviderStatus("facebook", "Facebook", False),
            ProviderStatus("mega", "MEGA", False),
        ),
        (
            ProviderStatus("youtube-search", "Search", True),
            ProviderStatus("bilibili-search", "Bilibili Search", False),
            ProviderStatus("ani-gamer-search", "AniGamer Search", False),
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
    assert len(rows) == 16
    assert all(row.available for row in rows)
    assert sum(row.enabled for row in rows) == 5
    assert rows[8].provider_id == "youtube-player"
    assert not rows[8].enabled


def test_builtin_mod_rows_keep_missing_expected_mod_visible() -> None:
    rows = builtin_mod_rows((), (), ())
    assert tuple(row.provider_id for row in rows) == (
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "facebook",
        "mega",
        "youtube-search",
        "bilibili-search",
        "ani-gamer-search",
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


def test_download_mod_locations_do_not_mix_site_workspaces() -> None:
    rows = {row.provider_id: row for row in builtin_mod_rows((), (), ())}

    assert rows["youtube"].control_location == "YouTube 下載工作區"
    assert rows["bilibili"].control_location == "Bilibili 下載工作區"
    assert "Facebook 下載工作區" in rows["facebook"].control_location
    assert "MEGA 下載工作區" in rows["mega"].control_location
    assert "YouTube 下載工作區" not in rows["bilibili"].control_location
    assert "不顯示於網站工作區" in rows["generic-ytdlp"].control_location


def test_builtin_mod_rows_preserve_bounded_initialization_reason() -> None:
    rows = builtin_mod_rows(
        (ProviderStatus("youtube", "YouTube", False, False, "hash mismatch"),),
        (),
        (),
        {"youtube-search": "provider manifest invalid"},
    )

    youtube = next(row for row in rows if row.provider_id == "youtube")
    search = next(row for row in rows if row.provider_id == "youtube-search")
    assert not youtube.available
    assert youtube.unavailable_reason == "hash mismatch"
    assert not search.available
    assert search.unavailable_reason == "provider manifest invalid"


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
                ProviderStatus("facebook", "Facebook", False),
                ProviderStatus("mega", "MEGA", False),
            )
        ),
        discovery=StatusSource(
            tuple(
                ProviderStatus(provider_id, provider_id, True)
                for provider_id in (
                    "youtube-search",
                    "bilibili-search",
                    "ani-gamer-search",
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
    visible_planned = tuple(
        planned
        for planned in PLANNED_MODS
        if planned.provider_id != "bilibili-danmaku"
    )
    assert table.rowCount() == 15 + len(visible_planned)
    assert table.accessibleName() == "內建與製作中 MOD 狀態"
    toggles = [
        button
        for button in panel.findChildren(QPushButton)
        if button.accessibleName().endswith("啟用狀態")
    ]
    assert len(toggles) == 15
    assert {button.text() for button in toggles} == {"啟用", "停用"}
    assert summary.text() == (
        "內建 MOD 16/16 已註冊 · 9 個已啟用 · "
        f"目前顯示 15 個父／子 MOD · 製作中 {len(PLANNED_MODS)} 項"
    )
    planned_start = table.rowCount() - len(visible_planned)
    assert [
        table.item(row, 1).text()
        for row in range(planned_start, table.rowCount())
    ] == [f"{planned.state} · {planned.priority}" for planned in visible_planned]
    assert all(
        table.cellWidget(row, 4) is None
        for row in range(planned_start, table.rowCount())
    )
    assert {
        table.item(row, 4).text()
        for row in range(planned_start, table.rowCount())
    } == {"尚不可用"}
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_builtin_mod_panel_displays_failed_mod_reason(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget

    app = QApplication.instance() or QApplication([])
    context = SimpleNamespace(
        download_providers=SimpleNamespace(
            statuses=lambda: (
                ProviderStatus(
                    "youtube",
                    "YouTube",
                    False,
                    False,
                    "integrity mismatch: provider.py",
                ),
            )
        ),
        discovery=SimpleNamespace(statuses=lambda: ()),
        features=SimpleNamespace(statuses=lambda: ()),
        builtin_mod_errors={"youtube": "integrity mismatch: provider.py"},
    )
    panel = create_builtin_mod_panel(context)
    try:
        table = panel.findChild(QTableWidget)
        assert table.item(0, 1).text() == "初始化失敗"
        assert "integrity mismatch" in table.item(0, 1).toolTip()
        youtube_toggle = next(
            button
            for button in panel.findChildren(QPushButton)
            if button.objectName() == "builtinModToggle-youtube"
        )
        assert not youtube_toggle.isEnabled()
        assert "integrity mismatch" in youtube_toggle.toolTip()
        summary = next(
            label
            for label in panel.findChildren(QLabel)
            if label.objectName() == "dependencySummary"
        )
        assert "youtube：integrity mismatch" in summary.toolTip()
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_plugin_manager_defaults_to_actionable_builtin_mods(
    tmp_path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QPushButton,
        QTabWidget,
    )

    from core.bootstrap.bootstrap import Bootstrap
    from core.storage.paths import AppPaths
    from trusted_ui.plugin_manager import create_plugin_manager_dialog

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    dialog = create_plugin_manager_dialog(context)
    guided_dialog = None
    try:
        rows = builtin_mod_rows(
            context.download_providers.statuses(),
            context.discovery.statuses(),
            context.features.statuses(),
        )
        assert {row.provider_id for row in rows} == BUILTIN_MOD_IDS
        tabs = dialog.findChild(QTabWidget, "pluginManagerTabs")
        assert tabs.currentIndex() == 1
        assert tabs.tabText(1) == "內建 MOD 狀態"
        assert tabs.tabText(6) == "自我檢查"
        assert any(
            label.text() == "尚無外部 MOD 介面"
            for label in dialog.findChildren(QLabel)
        )

        bilibili = next(
            toggle
            for toggle in dialog.findChildren(QPushButton)
            if toggle.objectName() == "builtinModToggle-bilibili"
        )
        assert not context.download_providers.is_enabled("bilibili")
        assert bilibili.text() == "啟用"
        bilibili.click()
        app.processEvents()
        assert context.download_providers.is_enabled("bilibili")
        assert dialog.findChild(QPushButton, "builtinModToggle-bilibili-search")

        guided_dialog = create_plugin_manager_dialog(
            context,
            initial_tab="site-catalog",
            bridge_id="threads",
        )
        guided_tabs = guided_dialog.findChild(QTabWidget, "pluginManagerTabs")
        guided_site = guided_dialog.findChild(
            QComboBox,
            "officialSiteBridgeSelect",
        )
        assert guided_tabs.currentIndex() == 2
        assert guided_tabs.tabText(2) == "網站 MOD 備選"
        assert guided_site.currentData() == "threads"
    finally:
        if guided_dialog is not None:
            guided_dialog.close()
            guided_dialog.deleteLater()
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
