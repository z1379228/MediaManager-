from __future__ import annotations

import pytest

from trusted_ui.feature_introduction import (
    FEATURE_INTRODUCTION_SECTIONS,
    create_feature_introduction_dialog,
    feature_introduction_search_text,
)


def test_feature_introduction_covers_current_features_and_required_boundaries() -> None:
    sections = {section.section_id: section for section in FEATURE_INTRODUCTION_SECTIONS}

    assert set(sections) == {
        "download-search",
        "download-inbox",
        "other-sources",
        "podcast-rss",
        "peertube-search",
        "library",
        "format-factory",
        "gopeed-p2p",
        "speech-to-text",
        "automation",
        "background-idle",
        "mods",
        "safety-release",
    }
    all_text = " ".join(
        feature_introduction_search_text(section)
        for section in FEATURE_INTRODUCTION_SECTIONS
    )
    for required in (
        "youtube",
        "bilibili",
        "direct http",
        "podcast / rss",
        "peertube",
        "格式工廠",
        "gopeed",
        "speech to text",
        "automation",
        "背景待機",
        "manifest schema v2",
        "sha-256",
        "不繞過 drm",
    ):
        assert required.casefold() in all_text


def test_feature_introduction_dialog_is_searchable_and_keyboard_accessible(
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QFrame, QLabel, QLineEdit

    app = QApplication.instance() or QApplication([])
    dialog = create_feature_introduction_dialog()
    try:
        assert dialog.objectName() == "featureIntroductionDialog"
        assert dialog.accessibleName() == "MediaManager 功能簡介"
        assert (dialog.minimumWidth(), dialog.minimumHeight()) == (720, 520)

        search = dialog.findChild(QLineEdit, "featureIntroductionSearch")
        cards = [
            card
            for card in dialog.findChildren(QFrame, "card")
            if card.property("featureIntroductionId")
        ]
        count = next(
            label
            for label in dialog.findChildren(QLabel, "muted")
            if label.accessibleName() == "功能簡介顯示數量"
        )
        assert search.accessibleName() == "搜尋功能簡介"
        assert len(cards) == len(FEATURE_INTRODUCTION_SECTIONS)
        assert count.text() == f"顯示 {len(cards)}／{len(cards)} 類"

        search.setText("whisper-cli")
        app.processEvents()
        visible_ids = {
            card.property("featureIntroductionId")
            for card in cards
            if not card.isHidden()
        }
        assert visible_ids == {"speech-to-text"}
        assert count.text() == f"顯示 1／{len(cards)} 類"

        search.setText("不存在的功能")
        app.processEvents()
        assert all(card.isHidden() for card in cards)
        no_results = dialog.findChild(QLabel, "emptyText")
        assert no_results.isVisibleTo(dialog)
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
