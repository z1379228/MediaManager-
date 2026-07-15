from __future__ import annotations

import pytest

from trusted_ui.site_mod_catalog import (
    ANI_GAMER_HOME,
    FACEBOOK_EXPORT_HELP,
    FACEBOOK_HOME,
    INSTAGRAM_EXPORT_HELP,
    INSTAGRAM_HOME,
    MEGA_HOME,
    OFFICIAL_BRIDGES,
    SITE_MOD_CANDIDATES,
    THREADS_EXPORT_HELP,
    THREADS_HOME,
    official_meta_bridge_id_for_url,
    validated_ani_gamer_url,
    validated_facebook_url,
    validated_instagram_url,
    validated_mega_url,
    validated_threads_url,
)


def test_site_mod_catalog_registers_requested_candidates() -> None:
    assert tuple(item.provider_id for item in SITE_MOD_CANDIDATES) == (
        "ani-gamer",
        "instagram",
        "threads",
    )
    assert all(
        "不擷取" in item.safety_boundary
        or "私人" in item.safety_boundary
        or "工作階段" in item.safety_boundary
        or "不啟用" in item.safety_boundary
        or "不宣稱" in item.safety_boundary
        for item in SITE_MOD_CANDIDATES
    )
    assert tuple(item.bridge_id for item in OFFICIAL_BRIDGES) == (
        "ani-gamer",
        "facebook",
        "instagram",
        "threads",
        "mega",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("https://www.facebook.com/watch/?v=123", "facebook"),
        ("https://instagram.com/reel/Cexample456?utm_source=share", "instagram"),
        ("https://www.threads.net/@openai/post/Cexample789", "threads"),
        ("https://www.facebook.com.evil.example/watch/?v=123", ""),
        ("https://user:secret@www.instagram.com/reel/Cexample456", ""),
        ("http://www.threads.com/@openai/post/Cexample789", ""),
    ),
)
def test_meta_official_bridge_detection_never_claims_download_support(
    value: str,
    expected: str,
) -> None:
    assert official_meta_bridge_id_for_url(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", ANI_GAMER_HOME),
        (ANI_GAMER_HOME, ANI_GAMER_HOME),
        (
            "https://ani.gamer.com.tw/animeVideo.php?sn=44866",
            "https://ani.gamer.com.tw/animeVideo.php?sn=44866",
        ),
    ),
)
def test_ani_gamer_official_url_accepts_only_canonical_pages(
    value: str,
    expected: str,
) -> None:
    assert validated_ani_gamer_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://ani.gamer.com.tw/",
        "https://ani.gamer.com.tw.evil.example/animeVideo.php?sn=1",
        "https://user:secret@ani.gamer.com.tw/animeVideo.php?sn=1",
        "https://ani.gamer.com.tw:443/animeVideo.php?sn=1",
        "https://ani.gamer.com.tw/animeVideo.php?sn=1&download=1",
        "https://ani.gamer.com.tw/animeVideo.php?sn=1#stream",
        "https://ani.gamer.com.tw/ajax/videoStart.php?sn=1",
    ),
)
def test_ani_gamer_official_url_rejects_noncanonical_or_endpoint_urls(
    value: str,
) -> None:
    assert validated_ani_gamer_url(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", FACEBOOK_HOME),
        ("https://facebook.com/", FACEBOOK_HOME),
        (
            "https://m.facebook.com/watch/?v=123456",
            "https://www.facebook.com/watch/?v=123456",
        ),
        (
            "https://www.facebook.com/video.php?v=123456",
            "https://www.facebook.com/video.php?v=123456",
        ),
        (
            "https://www.facebook.com/reel/123456",
            "https://www.facebook.com/reel/123456/",
        ),
        (
            "https://www.facebook.com/Page.Name/videos/987654321/",
            "https://www.facebook.com/Page.Name/videos/987654321/",
        ),
    ),
)
def test_facebook_official_url_accepts_bounded_video_pages(
    value: str,
    expected: str,
) -> None:
    assert validated_facebook_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://www.facebook.com/watch/?v=1",
        "https://www.facebook.com.evil.example/watch/?v=1",
        "https://user:secret@www.facebook.com/watch/?v=1",
        "https://www.facebook.com:443/watch/?v=1",
        "https://www.facebook.com/l.php?u=https://example.com/",
        "https://www.facebook.com/watch/?v=1&tracking=1",
        "https://www.facebook.com/example/",
        "https://www.facebook.com/reel/not-a-number/",
        "https://www.facebook.com/watch/?v=1#comments",
    ),
)
def test_facebook_official_url_rejects_redirect_or_nonmedia_pages(
    value: str,
) -> None:
    assert validated_facebook_url(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", INSTAGRAM_HOME),
        ("https://instagram.com/", INSTAGRAM_HOME),
        (
            "https://instagram.com/p/Cexample123",
            "https://www.instagram.com/p/Cexample123/",
        ),
        (
            "https://www.instagram.com/reel/Cexample456/",
            "https://www.instagram.com/reel/Cexample456/",
        ),
        (
            "https://www.instagram.com/tv/Cexample789",
            "https://www.instagram.com/tv/Cexample789/",
        ),
    ),
)
def test_instagram_official_url_accepts_bounded_media_pages(
    value: str,
    expected: str,
) -> None:
    assert validated_instagram_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://www.instagram.com/p/Cexample123/",
        "https://www.instagram.com.evil.example/p/Cexample123/",
        "https://user:secret@www.instagram.com/p/Cexample123/",
        "https://www.instagram.com:443/p/Cexample123/",
        "https://www.instagram.com/p/Cexample123/?utm_source=share",
        "https://www.instagram.com/example/",
        "https://www.instagram.com/accounts/login/",
        "https://www.instagram.com/p/a/",
        "https://www.instagram.com/reel/Cexample123/#comments",
    ),
)
def test_instagram_official_url_rejects_nonmedia_or_tracking_pages(
    value: str,
) -> None:
    assert validated_instagram_url(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", THREADS_HOME),
        ("https://threads.com/", THREADS_HOME),
        (
            "https://www.threads.net/@openai/post/Cexample123",
            "https://www.threads.com/@openai/post/Cexample123/",
        ),
        (
            "https://www.threads.com/@user.name/post/Cexample456/",
            "https://www.threads.com/@user.name/post/Cexample456/",
        ),
    ),
)
def test_threads_official_url_accepts_current_and_migrated_post_pages(
    value: str,
    expected: str,
) -> None:
    assert validated_threads_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://www.threads.com/@openai/post/Cexample123/",
        "https://www.threads.com.evil.example/@openai/post/Cexample123/",
        "https://user:secret@www.threads.com/@openai/post/Cexample123/",
        "https://www.threads.com:443/@openai/post/Cexample123/",
        "https://www.threads.com/@openai/",
        "https://www.threads.com/t/Cexample123/",
        "https://www.threads.com/@openai/post/Cexample123/?share=1",
        "https://www.threads.com/@bad%2Fname/post/Cexample123/",
        "https://www.threads.com/@openai/post/a/",
        "https://www.threads.com/@openai/post/Cexample123/#reply",
    ),
)
def test_threads_official_url_rejects_nonpost_or_tracking_pages(
    value: str,
) -> None:
    assert validated_threads_url(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", MEGA_HOME),
        ("https://mega.io/", MEGA_HOME),
        ("https://mega.nz/", MEGA_HOME),
        (
            "https://www.mega.nz/file/AbCdEf12#abcdefghijklmnopQRSTUVWX",
            "https://mega.nz/file/AbCdEf12#abcdefghijklmnopQRSTUVWX",
        ),
        (
            "https://mega.nz/folder/ZyXwVu98#1234567890abcdefghijklmnop",
            "https://mega.nz/folder/ZyXwVu98#1234567890abcdefghijklmnop",
        ),
    ),
)
def test_mega_official_url_accepts_home_or_bounded_public_share(
    value: str,
    expected: str,
) -> None:
    assert validated_mega_url(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "http://mega.nz/file/AbCdEf12#abcdefghijklmnop",
        "https://mega.nz.evil.example/file/AbCdEf12#abcdefghijklmnop",
        "https://user:secret@mega.nz/file/AbCdEf12#abcdefghijklmnop",
        "https://mega.nz:443/file/AbCdEf12#abcdefghijklmnop",
        "https://mega.nz/file/AbCdEf12?download=1#abcdefghijklmnop",
        "https://mega.nz/file/AbCdEf12",
        "https://mega.nz/file/a#abcdefghijklmnop",
        "https://mega.nz/file/AbCdEf12#short",
        "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop/folder/nested",
        "https://mega.io/file/AbCdEf12#abcdefghijklmnop",
        "https://mega.nz/#!legacy!link",
    ),
)
def test_mega_official_url_rejects_unsafe_or_unsupported_forms(value: str) -> None:
    assert validated_mega_url(value) is None


def test_site_mod_catalog_panel_marks_candidates_as_not_installed(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QTableWidget,
    )

    from trusted_ui.site_mod_catalog import create_site_mod_catalog_panel

    app = QApplication.instance() or QApplication([])
    opened: list[str] = []
    from PySide6.QtGui import QDesktopServices

    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()) or True,
    )
    panel = create_site_mod_catalog_panel()
    table = panel.findChild(QTableWidget)
    summaries = [
        label.text()
        for label in panel.findChildren(QLabel)
        if label.objectName() == "dependencySummary"
    ]
    assert table.rowCount() == 3
    assert summaries == [
        "已登記 3 個候選網站 MOD · 目前均未啟用下載"
    ]
    assert {table.item(row, 1).text() for row in range(3)} == {
        "不可下載 · 官方播放",
        "不可下載 · 官方工具",
    }
    official_site = panel.findChild(QComboBox, "officialSiteBridgeSelect")
    official_url = panel.findChild(QLineEdit, "officialSiteBridgeUrl")
    open_official = panel.findChild(QPushButton, "officialSiteBridgeOpen")
    open_help = panel.findChild(QPushButton, "officialSiteBridgeHelp")
    assert official_site is not None
    assert official_url is not None
    assert open_official is not None
    assert open_help is not None
    assert table.accessibleName() == "候選網站 MOD 狀態"
    assert official_site.accessibleName() == "官方工具網站"
    assert official_url.accessibleName() == "官方媒體頁網址"
    assert open_official.accessibleName() == "開啟選取網站的官方頁面"
    assert open_help.accessibleName() == "開啟選取網站的官方資料匯出說明"
    assert official_site.currentData() == "ani-gamer"
    assert open_help.isHidden()
    official_url.setText("https://example.com/")
    open_official.click()
    assert opened == []
    assert any(
        label.text() == "網址不是允許的「動畫瘋」官方媒體頁。"
        for label in panel.findChildren(QLabel)
    )
    official_url.setText("https://ani.gamer.com.tw/animeVideo.php?sn=44866")
    open_official.click()
    assert opened == ["https://ani.gamer.com.tw/animeVideo.php?sn=44866"]
    assert any(
        label.text() == "已交由系統瀏覽器開啟「動畫瘋」官方頁面。"
        for label in panel.findChildren(QLabel)
    )
    official_site.setCurrentIndex(official_site.findData("facebook"))
    assert not open_help.isHidden()
    assert any(
        label.text().startswith("Facebook：下載由可停用的獨立網站 MOD 處理")
        for label in panel.findChildren(QLabel)
    )
    official_url.setText("https://m.facebook.com/watch/?v=123456")
    open_official.click()
    open_help.click()
    assert opened[-2:] == [
        "https://www.facebook.com/watch/?v=123456",
        FACEBOOK_EXPORT_HELP,
    ]
    official_site.setCurrentIndex(official_site.findData("instagram"))
    official_url.setText("https://instagram.com/reel/Cexample456")
    open_official.click()
    open_help.click()
    assert opened[-2:] == [
        "https://www.instagram.com/reel/Cexample456/",
        INSTAGRAM_EXPORT_HELP,
    ]
    official_site.setCurrentIndex(official_site.findData("threads"))
    official_url.setText("https://threads.net/@openai/post/Cexample789")
    open_official.click()
    open_help.click()
    assert opened[-2:] == [
        "https://www.threads.com/@openai/post/Cexample789/",
        THREADS_EXPORT_HELP,
    ]
    official_site.setCurrentIndex(official_site.findData("mega"))
    assert open_help.isHidden()
    official_url.setText(
        "https://www.mega.nz/file/AbCdEf12#abcdefghijklmnopQRSTUVWX"
    )
    open_official.click()
    assert opened[-1] == (
        "https://mega.nz/file/AbCdEf12#abcdefghijklmnopQRSTUVWX"
    )
    panel.close()
    panel.deleteLater()
    app.processEvents()
