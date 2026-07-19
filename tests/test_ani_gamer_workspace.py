from __future__ import annotations

import json

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from core.bootstrap.bootstrap import Bootstrap
from core.discovery.adapters import FederatedSearchResult, SearchAdapterFailure
from core.storage.paths import AppPaths
from trusted_ui.ani_gamer_offline import ALLOWED_LOCAL_MEDIA_SUFFIXES
from trusted_ui.ani_gamer_history import load_history
from trusted_ui.ani_gamer_workspace import (
    ANI_GAMER_FILTER_TAGS,
    ANI_GAMER_FILTER_TARGETS,
    ANI_GAMER_FILTER_TYPES,
    ANI_GAMER_MEDIA_CAPABILITY_PROBE,
    ANI_GAMER_MEDIA_PROBE_WORLD_ID,
    WebEngineMediaCapability,
    ani_gamer_catalog_url,
    classify_webengine_media_capability,
    configure_ani_gamer_web_view,
    detect_qt_local_media_runtime_support,
    is_ani_gamer_navigation_allowed,
    is_official_ani_gamer_url,
    manual_official_episode,
    open_ani_gamer_system_browser,
    wire_ani_gamer_web_view_diagnostics,
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


def test_ani_gamer_web_view_enables_normal_html5_playback_only() -> None:
    pytest.importorskip("PySide6.QtWebEngineCore")

    class Settings:
        def __init__(self) -> None:
            self.attributes = []

        def setAttribute(self, attribute, enabled) -> None:
            self.attributes.append((attribute, enabled))

    class View:
        def __init__(self) -> None:
            self.settings_object = Settings()

        def settings(self):
            return self.settings_object

    view = View()
    assert configure_ani_gamer_web_view(view)
    assert len(view.settings_object.attributes) == 4
    assert [enabled for _attribute, enabled in view.settings_object.attributes] == [
        True,
        True,
        True,
        False,
    ]


def test_ani_gamer_navigation_allows_subresources_but_restricts_top_level() -> None:
    class Url:
        def __init__(self, host: str, scheme: str = "https", port: int = -1) -> None:
            self._host = host
            self._scheme = scheme
            self._port = port

        def host(self) -> str:
            return self._host

        def scheme(self) -> str:
            return self._scheme

        def userName(self) -> str:
            return ""

        def password(self) -> str:
            return ""

        def port(self) -> int:
            return self._port

    assert is_ani_gamer_navigation_allowed(Url("cdn.example"), False)
    assert is_ani_gamer_navigation_allowed(Url("ani.gamer.com.tw"), True)
    assert not is_ani_gamer_navigation_allowed(Url("evil.example"), True)
    assert not is_ani_gamer_navigation_allowed(Url("ani.gamer.com.tw", "http"), True)


@pytest.mark.parametrize(
    ("probe", "expected"),
    (
        (
            {
                "html5Video": True,
                "mse": True,
                "h264": True,
                "aac": True,
                "hls": True,
                "mseH264Aac": True,
            },
            WebEngineMediaCapability.SUPPORTED,
        ),
        (
            {
                "html5Video": True,
                "mse": False,
                "h264": True,
                "aac": True,
                "hls": True,
                "mseH264Aac": False,
            },
            WebEngineMediaCapability.SUPPORTED,
        ),
        (
            {
                "html5Video": True,
                "mse": True,
                "h264": True,
                "aac": True,
                "hls": False,
                "mseH264Aac": True,
            },
            WebEngineMediaCapability.SUPPORTED,
        ),
        (
            {
                "html5Video": True,
                "mse": True,
                "h264": False,
                "aac": False,
                "hls": False,
                "mseH264Aac": False,
            },
            WebEngineMediaCapability.UNSUPPORTED,
        ),
        (
            json.dumps(
                {
                    "html5Video": True,
                    "mse": True,
                    "h264": True,
                    "aac": True,
                    "hls": False,
                    "mseH264Aac": True,
                }
            ),
            WebEngineMediaCapability.SUPPORTED,
        ),
        ({"html5Video": True}, WebEngineMediaCapability.UNKNOWN),
        (None, WebEngineMediaCapability.UNKNOWN),
        ("not a probe result", WebEngineMediaCapability.UNKNOWN),
        ("{" + ("x" * 1_024) + "}", WebEngineMediaCapability.UNKNOWN),
    ),
)
def test_ani_gamer_media_capability_classification_is_pure(
    probe: object,
    expected: WebEngineMediaCapability,
) -> None:
    assert classify_webengine_media_capability(probe) is expected


def test_ani_gamer_media_probe_checks_only_local_browser_capabilities() -> None:
    probe = ANI_GAMER_MEDIA_CAPABILITY_PROBE.casefold()
    for forbidden in (
        "cookie",
        "fetch(",
        "xmlhttprequest",
        "queryselector",
        "localstorage",
        "sessionstorage",
    ):
        assert forbidden not in probe
    assert "canplaytype" in probe
    assert "mediasource.istypesupported" in probe
    assert "json.stringify" in probe
    assert "h.264" not in probe
    assert "avc1" in probe
    assert "mp4a" in probe
    assert "mpegurl" in probe


def test_ani_gamer_web_view_diagnostics_separates_load_from_media_capability() -> None:
    class Signal:
        def __init__(self) -> None:
            self.callback = None

        def connect(self, callback) -> None:
            self.callback = callback

        def emit(self, *values: object) -> None:
            assert self.callback is not None
            self.callback(*values)

    class Page:
        def __init__(self) -> None:
            self.script = ""
            self.world_id = -1
            self.callback = None

        def runJavaScript(self, script: str, world_id: int, callback) -> None:
            self.script = script
            self.world_id = world_id
            self.callback = callback

    class View:
        def __init__(self) -> None:
            self.loadFinished = Signal()
            self.renderProcessTerminated = Signal()
            self.page_object = Page()

        def page(self) -> Page:
            return self.page_object

    events: list[object] = []
    view = View()
    wire_ani_gamer_web_view_diagnostics(
        view,
        on_page_loaded=lambda: events.append("page-loaded-not-playable"),
        on_load_failed=lambda: events.append("load-failed"),
        on_capability=lambda value: events.append(value),
        on_renderer_terminated=lambda: events.append("renderer-terminated"),
    )

    view.loadFinished.emit(True)
    assert events == ["page-loaded-not-playable"]
    assert view.page_object.script == ANI_GAMER_MEDIA_CAPABILITY_PROBE
    assert view.page_object.world_id == ANI_GAMER_MEDIA_PROBE_WORLD_ID
    assert view.page_object.callback is not None
    view.page_object.callback(
        json.dumps(
            {
                "html5Video": True,
                "mse": True,
                "h264": False,
                "aac": False,
                "hls": False,
                "mseH264Aac": False,
            }
        )
    )
    assert events[-1] is WebEngineMediaCapability.UNSUPPORTED
    view.renderProcessTerminated.emit("potentially sensitive detail", 123)
    assert events[-1] == "renderer-terminated"
    assert "potentially sensitive detail" not in events

    failed_view = View()
    failed_events: list[str] = []
    wire_ani_gamer_web_view_diagnostics(
        failed_view,
        on_page_loaded=lambda: failed_events.append("page-loaded"),
        on_load_failed=lambda: failed_events.append("load-failed"),
        on_capability=lambda _value: failed_events.append("capability"),
        on_renderer_terminated=lambda: failed_events.append("renderer-terminated"),
    )
    failed_view.loadFinished.emit(False)
    assert failed_events == ["load-failed"]
    assert failed_view.page_object.script == ""


def test_ani_gamer_system_browser_fallback_accepts_only_official_https() -> None:
    opened: list[str] = []

    def opener(url: str) -> bool:
        opened.append(url)
        return True

    official = "https://ani.gamer.com.tw/animeVideo.php?sn=49944"
    assert open_ani_gamer_system_browser(official, opener)
    assert opened == [official]
    assert not open_ani_gamer_system_browser(
        "https://ani.gamer.com.tw.evil.example/animeVideo.php?sn=49944",
        opener,
    )
    assert not open_ani_gamer_system_browser(
        "https://user:secret@ani.gamer.com.tw/animeVideo.php?sn=49944",
        opener,
    )
    assert opened == [official]

    attempted: list[str] = []

    def rejected_by_os(url: str) -> bool:
        attempted.append(url)
        return False

    assert not open_ani_gamer_system_browser(official, rejected_by_os)
    assert attempted == [official]


def test_qt_local_media_runtime_adapter_matches_direct_qt_query() -> None:
    multimedia = pytest.importorskip("PySide6.QtMultimedia")
    from trusted_ui.ani_gamer_offline import local_media_runtime_support

    media_format_class = multimedia.QMediaFormat
    decode = media_format_class.ConversionMode.Decode
    instance = media_format_class()
    expected = local_media_runtime_support(
        {value.name for value in instance.supportedFileFormats(decode)},
        {value.name for value in instance.supportedAudioCodecs(decode)},
    )

    assert detect_qt_local_media_runtime_support(media_format_class) == expected


def test_qt_local_media_runtime_adapter_fails_closed_to_unknown() -> None:
    class BrokenMediaFormat:
        class ConversionMode:
            Decode = object()

        def __init__(self) -> None:
            raise RuntimeError("backend discovery failed")

    support = detect_qt_local_media_runtime_support(BrokenMediaFormat)

    assert not support.supported
    assert not support.unsupported
    assert support.unknown == ALLOWED_LOCAL_MEDIA_SUFFIXES


def test_ani_gamer_episode_verification_failure_accepts_manual_official_url(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from trusted_ui.ani_gamer_workspace import create_ani_gamer_workspace

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    set_builtin_mod_enabled(context, "ani-gamer", True)
    set_builtin_mod_enabled(context, "ani-gamer-episodes", True)
    panel = create_ani_gamer_workspace(context)
    series = DiscoveryItemV1(
        video_id="ani-114115",
        url="https://ani.gamer.com.tw/animeRef.php?sn=114115",
        title="幼女戰記 2",
        artist="動畫瘋",
        duration=None,
        language="zh-TW",
        category="video",
        thumbnail_url="",
    )
    episode_url = "https://ani.gamer.com.tw/animeVideo.php?sn=49944"
    queries: list[str] = []

    def fake_episode_search(query: str, **_options: object):
        queries.append(query)
        return FederatedSearchResult(
            (),
            (
                SearchAdapterFailure(
                    "ani-gamer-episodes",
                    "ani-gamer-browser-verification-required",
                ),
            ),
            (),
            (),
        )

    monkeypatch.setattr(context.discovery, "federated_search", fake_episode_search)
    try:
        panel.resize(940, 620)
        panel.show()
        panel.results = (series,)
        panel.populate_results()
        panel.table.selectRow(0)
        panel.load_episodes_button.click()

        for _ in range(200):
            app.processEvents()
            if not panel.busy and panel.episode_fallback.isVisible():
                break
            QTest.qWait(10)

        assert queries == [series.url]
        assert panel.episode_table.rowCount() == 0
        assert panel.episodes == ()
        assert panel.episode_fallback.isVisible()
        assert panel.manual_episode_url.isEnabled()

        panel.manual_episode_url.setText(episode_url)
        app.processEvents()
        assert panel.manual_episode_add.isEnabled()
        panel.manual_episode_add.click()
        app.processEvents()

        assert panel.episode_table.rowCount() == 1
        assert len(panel.episodes) == 1
        assert panel.episodes[0].url == episode_url
        assert panel.episode_query == series.url
        assert panel.episode_context.isVisible()
        assert panel.episode_context.text() == series.title
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_ani_gamer_workspace_follows_parent_child_state_and_opens_filter(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
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
        assert panel.status.textFormat() == Qt.TextFormat.PlainText
        assert panel.status.textInteractionFlags() & (
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        assert panel.offline_status.textFormat() == Qt.TextFormat.PlainText
        assert panel.open_selected_button.objectName() == "primary"
        assert panel.open_selected_embedded_button.objectName() == "ghost"
        assert panel.fallback_open_series.objectName() == "primary"
        assert panel.fallback_open_embedded.objectName() == "ghost"
        assert panel.open_episode_button.objectName() == "primary"
        assert panel.open_episode_embedded_button.objectName() == "ghost"
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
        assert panel.player_enabled.isEnabled()
        assert not panel.player_enabled.isChecked()

        panel.search_enabled.setChecked(True)
        panel.offline_enabled.setChecked(True)
        panel.player_enabled.setChecked(True)
        app.processEvents()
        assert context.discovery.is_enabled("ani-gamer-search")
        assert not context.discovery.is_enabled("ani-gamer-episodes")
        assert context.features.is_enabled("ani-gamer-offline")
        assert context.features.is_enabled("ani-gamer-player")

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
        panel.show_episode_results(
            FederatedSearchResult(
                (),
                (
                    SearchAdapterFailure(
                        "ani-gamer-episodes",
                        "[PROVIDER_ERROR] RuntimeError: "
                        "ani-gamer-browser-verification-required",
                    ),
                ),
                (),
            ),
            "",
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
        assert "尚未確認影片播放" in panel.status.text()

        history = load_history(panel.history_file)
        assert len(history) == 1
        original_open_embedded_url = panel.open_embedded_url
        monkeypatch.setattr(
            panel,
            "open_embedded_url",
            lambda *_args: pytest.fail("history must use the system browser"),
        )
        panel.open_history_entry(history[0])
        assert opened == [episode.url, episode.url]
        monkeypatch.setattr(
            panel,
            "open_embedded_url",
            original_open_embedded_url,
        )

        panel.embedded_web_engine_available = False
        panel.open_embedded_url(episode.url, episode.title)
        assert opened == [episode.url, episode.url]
        assert "尚未啟動任何外部程式" in panel.status.text()

        monkeypatch.setattr(QDesktopServices, "openUrl", lambda _url: False)
        panel.open_selected_episode()
        assert opened == [episode.url, episode.url]
        assert episode.url in panel.status.text()
        assert "無法將官方頁面交給系統瀏覽器" in panel.status.text()

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
        assert panel.open_episode_embedded_button.text() == "Compatibility View"
        assert panel.history_button.text() == "Recent Opens"

        set_builtin_mod_enabled(context, "ani-gamer", False)
        app.processEvents()
        assert not context.features.is_enabled("ani-gamer")
        assert not context.discovery.is_enabled("ani-gamer-search")
        assert not context.discovery.is_enabled("ani-gamer-episodes")
        assert not context.features.is_enabled("ani-gamer-offline")
        assert not context.features.is_enabled("ani-gamer-player")
        assert not panel.search_enabled.isEnabled()
        assert not panel.episodes_enabled.isEnabled()
        assert not panel.offline_enabled.isEnabled()
        assert not panel.player_enabled.isEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
