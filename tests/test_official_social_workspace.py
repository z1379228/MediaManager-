from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("site_family", "page_id", "export_id", "valid_url", "canonical_url"),
    (
        (
            "instagram",
            "instagram-page",
            "instagram-export",
            "https://instagram.com/reel/Cexample456",
            "https://www.instagram.com/reel/Cexample456/",
        ),
        (
            "threads",
            "threads-page",
            "threads-export",
            "https://threads.net/@openai/post/Cexample789",
            "https://www.threads.com/@openai/post/Cexample789/",
        ),
        (
            "twitter",
            "twitter-page",
            "twitter-export",
            "https://twitter.com/openai/status/123456",
            "https://x.com/openai/status/123456",
        ),
    ),
)
def test_official_social_workspace_gates_child_tools_and_opens_only_validated_urls(
    tmp_path,
    monkeypatch,
    site_family: str,
    page_id: str,
    export_id: str,
    valid_url: str,
    canonical_url: str,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QPushButton

    from core.bootstrap.bootstrap import Bootstrap
    from core.storage.paths import AppPaths
    from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
    from trusted_ui.official_social_workspace import create_official_social_workspace

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    opened: list[str] = []
    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()) or True,
    )
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    panel = None
    try:
        assert context.features.is_enabled(site_family)
        assert context.features.is_enabled(page_id)
        assert context.features.is_enabled(export_id)
        set_builtin_mod_enabled(context, page_id, False)
        set_builtin_mod_enabled(context, export_id, False)
        panel = create_official_social_workspace(
            context,
            site_family=site_family,
        )
        page_toggle = panel.findChild(
            QCheckBox,
            f"officialSocialToggle-{page_id}",
        )
        export_toggle = panel.findChild(
            QCheckBox,
            f"officialSocialToggle-{export_id}",
        )
        url = panel.findChild(QLineEdit, f"officialSocialUrl-{site_family}")
        open_page = panel.findChild(
            QPushButton,
            f"officialSocialOpenPage-{site_family}",
        )
        open_export = panel.findChild(
            QPushButton,
            f"officialSocialOpenExport-{site_family}",
        )
        choose_archive = panel.findChild(
            QPushButton,
            f"officialSocialChooseArchive-{site_family}",
        )
        import_archive = panel.findChild(
            QPushButton,
            f"officialSocialImportArchive-{site_family}",
        )
        assert page_toggle.isEnabled()
        assert export_toggle.isEnabled()
        assert not page_toggle.isChecked()
        assert not open_page.isEnabled()
        page_toggle.click()
        export_toggle.click()
        app.processEvents()
        assert context.features.is_enabled(page_id)
        assert context.features.is_enabled(export_id)
        assert open_page.isEnabled()
        assert open_export.isEnabled()
        assert choose_archive.isEnabled()
        assert not import_archive.isEnabled()

        url.setText("https://example.com/not-allowed")
        open_page.click()
        assert opened == []
        url.setText(valid_url)
        open_page.click()
        assert opened == [canonical_url]
        open_export.click()
        assert len(opened) == 2

        set_builtin_mod_enabled(context, site_family, False)
        app.processEvents()
        assert not context.features.is_enabled(page_id)
        assert not context.features.is_enabled(export_id)
        assert not page_toggle.isEnabled()
        assert not open_page.isEnabled()
        assert not choose_archive.isEnabled()
    finally:
        if panel is not None:
            panel.shutdown()
            panel.close()
            panel.deleteLater()
        context.lifecycle.shutdown()
        app.processEvents()


def test_official_social_workspace_rejects_unknown_site() -> None:
    from trusted_ui.official_social_workspace import create_official_social_workspace

    with pytest.raises(ValueError, match="unsupported"):
        create_official_social_workspace(object(), site_family="unknown")
