from __future__ import annotations

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.bootstrap.bootstrap import Bootstrap
from core.discovery.adapters import FederatedSearchResult
from core.storage.paths import AppPaths
from trusted_ui.ani_gamer_workspace import (
    ANI_GAMER_FILTER_TAGS,
    ANI_GAMER_FILTER_TARGETS,
    ANI_GAMER_FILTER_TYPES,
    ani_gamer_catalog_url,
    is_official_ani_gamer_url,
)
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled


def test_ani_gamer_catalog_urls_use_only_verified_official_filters() -> None:
    assert ani_gamer_catalog_url("冒險", "電影", "闔家觀賞", 2) == (
        "https://ani.gamer.com.tw/animeList.php?"
        "tags=%E5%86%92%E9%9A%AA&category=%E9%9B%BB%E5%BD%B1&"
        "target=%E9%97%94%E5%AE%B6%E8%A7%80%E8%B3%9E&sort=2"
    )
    assert is_official_ani_gamer_url(
        "https://ani.gamer.com.tw/animeRef.php?sn=114096"
    )
    assert is_official_ani_gamer_url(
        "https://ani.gamer.com.tw/animeVideo.php?sn=49944"
    )
    assert not is_official_ani_gamer_url(
        "https://ani.gamer.com.tw.evil.example/animeRef.php?sn=114096"
    )
    with pytest.raises(ValueError, match="filter"):
        ani_gamer_catalog_url("未驗證分類")


def test_ani_gamer_workspace_follows_parent_child_state_and_opens_filter(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from trusted_ui.ani_gamer_workspace import create_ani_gamer_workspace

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    set_builtin_mod_enabled(context, "ani-gamer", True)
    opened: list[str] = []
    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: opened.append(bytes(url.toEncoded()).decode("ascii")) or True,
    )
    panel = create_ani_gamer_workspace(context)
    try:
        assert panel.tag_filter.count() == len(ANI_GAMER_FILTER_TAGS)
        assert panel.type_filter.count() == len(ANI_GAMER_FILTER_TYPES)
        assert panel.target_filter.count() == len(ANI_GAMER_FILTER_TARGETS)
        assert panel.search_enabled.isEnabled()
        assert not panel.search_enabled.isChecked()
        assert panel.episodes_enabled.isEnabled()
        assert not panel.episodes_enabled.isChecked()

        panel.search_enabled.setChecked(True)
        panel.episodes_enabled.setChecked(True)
        app.processEvents()
        assert context.discovery.is_enabled("ani-gamer-search")
        assert context.discovery.is_enabled("ani-gamer-episodes")

        panel.tag_filter.setCurrentText("冒險")
        panel.type_filter.setCurrentText("電影")
        panel.target_filter.setCurrentText("闔家觀賞")
        panel.sort_filter.setCurrentIndex(panel.sort_filter.findData(2))
        catalog_queries: list[str] = []

        def fake_catalog_search(query: str, **_options: object):
            catalog_queries.append(query)
            return FederatedSearchResult((), (), ())

        def wait_for_catalog_query_count(expected: int) -> None:
            for _ in range(200):
                app.processEvents()
                if len(catalog_queries) >= expected and not panel.busy:
                    return
                QTest.qWait(10)
            pytest.fail(
                f"catalog search did not finish: expected={expected}, "
                f"actual={len(catalog_queries)}, busy={panel.busy}"
            )

        monkeypatch.setattr(
            context.discovery, "federated_search", fake_catalog_search
        )
        panel.open_filter.click()
        wait_for_catalog_query_count(1)
        assert catalog_queries == [
            ani_gamer_catalog_url("冒險", "電影", "闔家觀賞", 2)
        ]
        assert panel.quick_buttons["recent"].isEnabled()
        panel.quick_buttons["recent"].click()
        wait_for_catalog_query_count(2)
        assert catalog_queries[-1].endswith("#recent")

        series = DiscoveryItemV1(
            "ani-114115",
            "https://ani.gamer.com.tw/animeRef.php?sn=114115",
            "幼女戰記 2",
            "動畫瘋官方目錄",
            None,
            "",
            "video",
            "",
        )
        episode = DiscoveryItemV1(
            "ani-episode-49944",
            "https://ani.gamer.com.tw/animeVideo.php?sn=49944",
            "幼女戰記 2 [2]",
            "動畫瘋官方集數",
            None,
            "",
            "video",
            "",
        )
        panel.results = (series,)
        panel.populate_results()
        panel.table.selectRow(0)
        app.processEvents()
        assert panel.load_episodes_button.isEnabled()
        panel.episode_query = series.url
        panel.show_episode_results(
            FederatedSearchResult(
                (episode,), (), ("ani-gamer-episodes",), ()
            ),
            "",
        )
        panel.episode_table.selectRow(0)
        panel.open_selected_episode()
        assert opened == [episode.url]

        panel.apply_language("en")
        assert panel.title.text() == "AniGamer Official Catalog"
        assert panel.load_episodes_button.text() == "Show Selected Title Episodes"

        set_builtin_mod_enabled(context, "ani-gamer", False)
        app.processEvents()
        assert not context.features.is_enabled("ani-gamer")
        assert not context.discovery.is_enabled("ani-gamer-search")
        assert not context.discovery.is_enabled("ani-gamer-episodes")
        assert not panel.search_enabled.isEnabled()
        assert not panel.episodes_enabled.isEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
