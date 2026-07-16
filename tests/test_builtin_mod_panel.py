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
            ProviderStatus("direct-http", "Direct HTTP", False),
        ),
        (
            ProviderStatus("youtube-search", "Search", True),
            ProviderStatus("bilibili-search", "Bilibili Search", False),
            ProviderStatus("ani-gamer-search", "AniGamer Search", False),
            ProviderStatus("ani-gamer-episodes", "AniGamer Episodes", False),
            ProviderStatus("youtube-player", "Player", False),
            ProviderStatus("youtube-history", "History", False),
            ProviderStatus("youtube-recovery", "Recovery", True),
            ProviderStatus("youtube-similar", "Similar", True),
            ProviderStatus("youtube-auto-split", "Split", True),
        ),
        (
            FeatureStatus("ani-gamer", "AniGamer", False),
            FeatureStatus("ani-gamer-offline", "AniGamer Offline", False),
            FeatureStatus("bilibili-danmaku", "Bilibili Danmaku", False),
            FeatureStatus("instagram", "Instagram", False),
            FeatureStatus("instagram-page", "Instagram Page", False),
            FeatureStatus("instagram-export", "Instagram Export", False),
            FeatureStatus("threads", "Threads", False),
            FeatureStatus("threads-page", "Threads Page", False),
            FeatureStatus("threads-export", "Threads Export", False),
            FeatureStatus("twitter", "X / Twitter", False),
            FeatureStatus("twitter-page", "X Page", False),
            FeatureStatus("twitter-export", "X Export", False),
            FeatureStatus("media-convert", "Media Convert", False),
            FeatureStatus("media-ad-trim", "Local Ad Segment Trim", False),
            FeatureStatus("speech-to-text", "Speech to Text", False),
            FeatureStatus("automation", "Automation", False),
        ),
    )
    assert len(rows) == 31
    assert all(row.available for row in rows)
    assert sum(row.enabled for row in rows) == 5
    player = next(row for row in rows if row.provider_id == "youtube-player")
    assert not player.enabled


def test_builtin_mod_rows_keep_missing_expected_mod_visible() -> None:
    rows = builtin_mod_rows((), (), ())
    assert tuple(row.provider_id for row in rows) == (
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "ani-gamer",
        "facebook",
        "mega",
        "direct-http",
        "instagram",
        "threads",
        "twitter",
        "youtube-search",
        "bilibili-search",
        "bilibili-danmaku",
        "ani-gamer-search",
        "ani-gamer-episodes",
        "ani-gamer-offline",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
        "instagram-page",
        "instagram-export",
        "threads-page",
        "threads-export",
        "twitter-page",
        "twitter-export",
        "media-convert",
        "media-ad-trim",
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
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QTreeWidget

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
                ProviderStatus("direct-http", "Direct HTTP", False),
            )
        ),
        discovery=StatusSource(
            tuple(
                ProviderStatus(provider_id, provider_id, True)
                for provider_id in (
                    "youtube-search",
                    "bilibili-search",
                        "ani-gamer-search",
                        "ani-gamer-episodes",
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
                FeatureStatus("ani-gamer", "AniGamer", False),
                FeatureStatus("ani-gamer-offline", "AniGamer Offline", False),
                FeatureStatus("bilibili-danmaku", "Bilibili Danmaku", False),
                FeatureStatus("instagram", "Instagram", False),
                FeatureStatus("instagram-page", "Instagram Page", False),
                FeatureStatus("instagram-export", "Instagram Export", False),
                FeatureStatus("threads", "Threads", False),
                FeatureStatus("threads-page", "Threads Page", False),
                FeatureStatus("threads-export", "Threads Export", False),
                FeatureStatus("twitter", "X / Twitter", False),
                FeatureStatus("twitter-page", "X Page", False),
                FeatureStatus("twitter-export", "X Export", False),
                FeatureStatus("media-convert", "Media Convert", False),
                FeatureStatus(
                    "media-ad-trim", "Local Ad Segment Trim", False
                ),
                FeatureStatus("speech-to-text", "Speech to Text", False),
                FeatureStatus("automation", "Automation", False),
            )
        ),
    )
    panel = create_builtin_mod_panel(context)
    tree = panel.findChild(QTreeWidget, "builtinModTree")
    summary = next(
        label
        for label in panel.findChildren(QLabel)
        if label.objectName() == "dependencySummary"
    )
    assert tree.topLevelItemCount() == 13 + len(PLANNED_MODS)
    assert tree.accessibleName() == "依網站分組的內建 MOD 清單"
    toggles = [
        toggle
        for toggle in panel.findChildren(QCheckBox)
        if toggle.accessibleName().endswith("啟用狀態")
    ]
    assert len(toggles) == 19
    assert {toggle.text() for toggle in toggles} == {"啟用"}
    assert summary.text() == (
        "內建 MOD 31/31 已載入 · 10 個已啟用 · "
        f"8 個網站父 MOD · 規劃中 {len(PLANNED_MODS)} 個"
    )
    youtube = next(
        tree.topLevelItem(index)
        for index in range(tree.topLevelItemCount())
        if tree.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
        == "group:youtube"
    )
    bilibili = next(
        tree.topLevelItem(index)
        for index in range(tree.topLevelItemCount())
        if tree.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
        == "group:bilibili"
    )
    assert youtube.childCount() == 7
    assert bilibili.childCount() == 1
    assert youtube.child(0).data(0, Qt.ItemDataRole.UserRole) == "youtube"
    assert youtube.child(1).data(0, Qt.ItemDataRole.UserRole) == "youtube-search"
    planned_start = tree.topLevelItemCount() - len(PLANNED_MODS)
    assert [
        tree.topLevelItem(row).text(1)
        for row in range(planned_start, tree.topLevelItemCount())
    ] == [f"{planned.state} · {planned.priority}" for planned in PLANNED_MODS]
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_builtin_mod_panel_displays_failed_mod_reason(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QTreeWidget

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
        tree = panel.findChild(QTreeWidget, "builtinModTree")
        youtube = next(
            tree.topLevelItem(index)
            for index in range(tree.topLevelItemCount())
            if tree.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
            == "group:youtube"
        )
        assert youtube.child(0).text(1) == "初始化失敗"
        assert "integrity mismatch" in youtube.child(0).toolTip(1)
        youtube_toggle = next(
            toggle
            for toggle in panel.findChildren(QCheckBox)
            if toggle.objectName() == "builtinModToggle-youtube"
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
        QCheckBox,
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
            for toggle in dialog.findChildren(QCheckBox)
            if toggle.objectName() == "builtinModToggle-bilibili"
        )
        assert not context.download_providers.is_enabled("bilibili")
        assert bilibili.text() == "啟用"
        bilibili.click()
        app.processEvents()
        assert context.download_providers.is_enabled("bilibili")
        assert dialog.findChild(QCheckBox, "builtinModToggle-bilibili-search")

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
