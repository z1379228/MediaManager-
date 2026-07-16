from __future__ import annotations

import json

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
    manual_official_episode,
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

    manual = manual_official_episode(
        "https://ani.gamer.com.tw/animeVideo.php?sn=49944",
        "AniGamer official episode 49944",
    )
    assert manual is not None
    assert manual.url == "https://ani.gamer.com.tw/animeVideo.php?sn=49944"
    assert manual.video_id == "ani-episode-49944"
    assert (
        manual_official_episode(
            "https://ani.gamer.com.tw/animeRef.php?sn=114096",
            "invalid",
        )
        is None
    )


def test_ani_gamer_workspace_follows_parent_child_state_and_opens_filter(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox

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
        panel.resize(940, 360)
        panel.show()
        app.processEvents()
        assert panel.scroll_area.horizontalScrollBar().maximum() == 0
        assert panel.tag_filter.count() == len(ANI_GAMER_FILTER_TAGS)
        assert panel.type_filter.count() == len(ANI_GAMER_FILTER_TYPES)
        assert panel.target_filter.count() == len(ANI_GAMER_FILTER_TARGETS)
        assert panel.search_enabled.isEnabled()
        assert not panel.search_enabled.isChecked()
        assert panel.episodes_enabled.isEnabled()
        assert not panel.episodes_enabled.isChecked()
        assert panel.offline_enabled.isEnabled()
        assert not panel.offline_enabled.isChecked()

        panel.search_enabled.setChecked(True)
        panel.offline_enabled.setChecked(True)
        app.processEvents()
        assert context.discovery.is_enabled("ani-gamer-search")
        assert not context.discovery.is_enabled("ani-gamer-episodes")
        assert context.features.is_enabled("ani-gamer-offline")

        panel.show_search_results(
            None,
            "[PROVIDER_ERROR] RuntimeError: "
            "ani-gamer-browser-verification-required",
        )
        assert "Cloudflare" in panel.status.text()
        assert "[PROVIDER_ERROR]" not in panel.status.text()

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
        assert panel.retry_button.isEnabled()
        panel.retry_button.click()
        wait_for_catalog_query_count(3)
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
        assert panel.load_episodes_button.text() == "啟用集數導覽並載入"
        panel.show_episode_results(
            None,
            "[PROVIDER_ERROR] RuntimeError: "
            "ani-gamer-browser-verification-required",
        )
        assert "Cloudflare" in panel.status.text()
        assert "[PROVIDER_ERROR]" not in panel.status.text()
        assert panel.episode_fallback.isVisible()

        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
        )
        episode_queries: list[str] = []

        def fake_episode_search(query: str, **_options: object):
            episode_queries.append(query)
            return FederatedSearchResult(
                (episode,), (), ("ani-gamer-episodes",), ()
            )

        monkeypatch.setattr(
            context.discovery, "federated_search", fake_episode_search
        )
        panel.load_episodes_button.click()
        for _ in range(200):
            app.processEvents()
            if not panel.busy and panel.episode_table.rowCount() == 1:
                break
            QTest.qWait(10)
        app.processEvents()
        assert context.discovery.is_enabled("ani-gamer-episodes")
        assert episode_queries == [series.url]
        assert panel.episode_table.rowCount() == 1
        assert panel.episode_context.isVisible()
        assert panel.episode_context.text() == series.title
        assert panel.scroll_area.verticalScrollBar().value() > 0
        panel.episode_table.selectRow(0)
        panel.offline_output.setText(str(tmp_path / "offline-records"))
        assert panel.offline_save_button.isEnabled()
        assert panel.offline_import_button.isEnabled()
        assert panel.offline_verify_button.isEnabled()
        panel.offline_save_button.click()
        app.processEvents()
        assert panel.offline_archive_root is not None
        record = json.loads(
            (panel.offline_archive_root / "episode.json").read_text(encoding="utf-8")
        )
        assert record["episode"]["official_url"] == episode.url
        assert record["local_media"] is None
        panel.offline_verify_button.click()
        for _ in range(200):
            app.processEvents()
            if not panel.busy:
                break
            QTest.qWait(10)
        assert not panel.busy
        assert "尚未連結影片或字幕" in panel.offline_status.text()
        panel.open_selected_episode()
        assert opened == [episode.url]

        panel.manual_episode_url.setText(
            "https://ani.gamer.com.tw/animeVideo.php?sn=49945"
        )
        app.processEvents()
        assert panel.manual_episode_add.isEnabled()
        panel.manual_episode_add.click()
        app.processEvents()
        assert panel.episodes[0].url.endswith("sn=49945")
        assert "49945" in panel.episodes[0].title

        other_series = DiscoveryItemV1(
            "ani-114116",
            "https://ani.gamer.com.tw/animeRef.php?sn=114116",
            "另一部作品",
            "動畫瘋官方目錄",
            None,
            "",
            "video",
            "",
        )
        panel.results = (series, other_series)
        panel.populate_results()
        panel.table.selectRow(1)
        app.processEvents()
        assert panel.manual_episode_url.text() == ""
        assert panel.episodes == ()
        assert not panel.episode_fallback.isVisible()
        assert not panel.manual_episode_add.isEnabled()

        panel.apply_language("en")
        assert panel.title.text() == "AniGamer Official Catalog"
        assert panel.load_episodes_button.text() == "Load Selected Title Episodes"

        set_builtin_mod_enabled(context, "ani-gamer", False)
        app.processEvents()
        assert not context.features.is_enabled("ani-gamer")
        assert not context.discovery.is_enabled("ani-gamer-search")
        assert not context.discovery.is_enabled("ani-gamer-episodes")
        assert not context.features.is_enabled("ani-gamer-offline")
        assert not panel.search_enabled.isEnabled()
        assert not panel.episodes_enabled.isEnabled()
        assert not panel.offline_enabled.isEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
