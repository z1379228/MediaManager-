from __future__ import annotations

from core.dependency_health import DependencyReport, DependencyStatus
from trusted_ui.dependency_dialog import (
    dependency_table_row,
    dependency_presentation,
    startup_dependency_prompt_required,
)


def _report(available: tuple[bool, ...]) -> DependencyReport:
    dependency_ids = (
        "yt-dlp",
        "yt-dlp-ejs",
        "ffmpeg",
        "javascript-runtime",
    )
    return DependencyReport(
        tuple(
            DependencyStatus(dependency_id, dependency_id, ready, "", "", "")
            for dependency_id, ready in zip(dependency_ids, available, strict=True)
        )
    )


def test_dependency_badge_is_compact_and_explicit() -> None:
    assert dependency_presentation(_report((True, True, True, True))) == (
        "核心 4/4",
        "ready",
        "核心下載環境已就緒；MEGAcmd、whisper-cli 與語音模型依使用的 MOD 選裝。",
    )
    assert dependency_presentation(_report((True, False, True, False))) == (
        "核心 2/4",
        "warning",
        "缺少 2 項核心依賴，請開啟環境檢查。",
    )


def test_dependency_badge_separates_optional_mod_tools() -> None:
    statuses = _report((True, True, True, True)).statuses + (
        DependencyStatus("mega-get", "MEGAcmd", False, "", "", ""),
        DependencyStatus("whisper-cli", "whisper-cli", False, "", "", ""),
        DependencyStatus("speech-model", "Speech model", False, "", "", ""),
    )
    assert dependency_presentation(DependencyReport(statuses))[0] == (
        "核心 4/4｜選用 MOD 工具 0/3"
    )


def test_dependency_rows_distinguish_missing_optional_tools_from_core_faults() -> None:
    optional = DependencyStatus(
        "whisper-cli",
        "whisper-cli",
        False,
        "",
        "",
        "尚未偵測到 whisper-cli；Speech to Text 無法執行",
    )
    core = DependencyStatus(
        "ffmpeg",
        "FFmpeg",
        False,
        "",
        "",
        "尚未偵測到 FFmpeg",
    )

    assert dependency_table_row(optional, is_core=False) == (
        "選用 MOD",
        "whisper-cli",
        "未安裝（不影響核心）",
        "尚未偵測到",
        "Speech to Text MOD：尚未偵測到 whisper-cli；Speech to Text 無法執行",
    )
    assert dependency_table_row(core, is_core=True)[2] == "缺少（阻擋核心）"


def test_dependency_dialog_exposes_full_detected_path_and_copy_action(
    tmp_path,
    monkeypatch,
) -> None:
    import pytest

    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget

    from trusted_ui.dependency_dialog import create_dependency_dialog

    detected = str(tmp_path / "MEGAcmd" / "mega-get.bat")
    statuses = _report((True, True, True, True)).statuses + (
        DependencyStatus(
            "mega-get",
            "MEGAcmd mega-get",
            True,
            "",
            detected,
            "MEGA 公開檔案下載可用",
        ),
    )
    app = QApplication.instance() or QApplication([])
    dialog = create_dependency_dialog(
        tmp_path,
        report_factory=lambda _root: DependencyReport(statuses),
    )
    table = dialog.findChild(QTableWidget, "dependencyTable")
    copy = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == "複製所選工具路徑"
    )
    try:
        optional_row = table.rowCount() - 1
        assert table.item(optional_row, 0).text() == "選用 MOD"
        assert table.item(optional_row, 2).text() == "可用"
        assert table.item(optional_row, 3).toolTip() == detected
        table.selectRow(optional_row)
        app.processEvents()
        assert copy.isEnabled()
        copy.click()
        assert QApplication.clipboard().text() == detected
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_startup_dependency_prompt_only_appears_for_incomplete_support() -> None:
    assert not startup_dependency_prompt_required(_report((True, True, True, True)))
    assert startup_dependency_prompt_required(_report((True, False, True, True)))
