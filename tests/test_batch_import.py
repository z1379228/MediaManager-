from __future__ import annotations

from pathlib import Path

import pytest

from core.downloads.batch_import import (
    MAX_BATCH_IMPORT_BYTES,
    BatchImportEntry,
    BatchImportIssue,
    BatchImportResult,
    build_import_requests,
    parse_batch_import,
    parse_download_intake_text,
    prepare_download_intake,
)


def test_txt_import_skips_comments_and_reports_invalid_or_duplicate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "downloads.txt"
    source.write_text(
        "# MediaManager list\n"
        "https://example.com/one\n"
        "not-a-url\n"
        "https://example.com/one\n"
        "https://user:secret@example.com/private\n",
        encoding="utf-8",
    )

    result = parse_batch_import(source)

    assert [entry.url for entry in result.entries] == ["https://example.com/one"]
    assert [issue.row_number for issue in result.issues] == [3, 4, 5]
    assert "duplicate" in result.issues[1].reason
    assert "credentials" in result.issues[2].reason


def test_csv_import_reads_named_metadata_columns(tmp_path: Path) -> None:
    source = tmp_path / "downloads.csv"
    source.write_text(
        "作者,網址,標題\n"
        'Example Artist,https://example.com/video,"Example, Song"\n',
        encoding="utf-8-sig",
    )

    result = parse_batch_import(source)

    assert result.issues == ()
    assert result.entries == (
        BatchImportEntry(
            row_number=2,
            url="https://example.com/video",
            title="Example, Song",
            artist="Example Artist",
        ),
    )


def test_csv_import_without_header_uses_first_three_columns(tmp_path: Path) -> None:
    source = tmp_path / "plain.csv"
    source.write_text(
        "https://example.com/a,Title A,Artist A\n"
        "https://example.com/b,Title B\n",
        encoding="utf-8",
    )

    result = parse_batch_import(source)

    assert [entry.title for entry in result.entries] == ["Title A", "Title B"]
    assert [entry.artist for entry in result.entries] == ["Artist A", ""]


def test_import_rejects_unsupported_or_oversized_files(tmp_path: Path) -> None:
    unsupported = tmp_path / "downloads.json"
    unsupported.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="TXT or CSV"):
        parse_batch_import(unsupported)

    oversized = tmp_path / "downloads.txt"
    oversized.write_bytes(b"x" * (MAX_BATCH_IMPORT_BYTES + 1))
    with pytest.raises(ValueError, match="2 MiB"):
        parse_batch_import(oversized)


def test_import_rejects_more_than_500_data_rows(tmp_path: Path) -> None:
    source = tmp_path / "downloads.txt"
    source.write_text(
        "\n".join(f"https://example.com/{index}" for index in range(501)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="500-row"):
        parse_batch_import(source)


def test_download_intake_text_uses_the_same_bounded_url_validation() -> None:
    result = parse_download_intake_text(
        "# pasted links\n"
        "https://example.com/one\n"
        "https://user:secret@example.com/private\n"
        "not-a-url\n"
        "https://example.com/one\n"
    )

    assert result.entries == (
        BatchImportEntry(2, "https://example.com/one"),
    )
    assert [issue.row_number for issue in result.issues] == [3, 4, 5]
    assert "credentials" in result.issues[0].reason
    assert "HTTP or HTTPS" in result.issues[1].reason
    assert "duplicate" in result.issues[2].reason


def test_download_intake_text_rejects_unbounded_payloads() -> None:
    with pytest.raises(ValueError, match="2 MiB"):
        parse_download_intake_text("x" * (MAX_BATCH_IMPORT_BYTES + 1))


def test_download_intake_filters_workspace_and_disabled_providers() -> None:
    parsed = BatchImportResult(
        (
            BatchImportEntry(1, "https://example.com/ready"),
            BatchImportEntry(2, "https://wrong.example/video"),
            BatchImportEntry(3, "https://example.com/disabled"),
        ),
        (BatchImportIssue(4, "invalid", "URL is malformed"),),
    )

    def provider_for(url: str) -> object:
        if url.endswith("/disabled"):
            raise RuntimeError("Example MOD 尚未啟用")
        return object()

    result = prepare_download_intake(
        parsed,
        accepts_url=lambda url: "wrong.example" not in url,
        provider_for=provider_for,
        site_label="Example",
    )

    assert result.entries == parsed.entries[:1]
    assert [issue.row_number for issue in result.issues] == [4, 2, 3]
    assert "Example 網址" in result.issues[1].reason
    assert result.issues[2].reason == "Example MOD 尚未啟用"


def test_build_import_requests_keeps_options_and_metadata(tmp_path: Path) -> None:
    requests = build_import_requests(
        (
            BatchImportEntry(
                row_number=2,
                url="https://example.com/video",
                title="Example Song",
                artist="Example Artist",
            ),
        ),
        output_dir=tmp_path,
        priority=5,
        start_time=10.0,
        end_time=20.0,
        format_preset="best",
        subtitle_mode="selected",
        subtitle_languages=("zh-TW", "en"),
        timed_comment_mode="ass",
        container_preset="mkv",
    )

    request = requests[0]
    assert request.source_title == "Example Song"
    assert request.source_artist == "Example Artist"
    assert request.source_category == "batch-import"
    assert request.start_time == 10.0
    assert request.subtitle_languages == ("zh-TW", "en")
    assert request.timed_comment_mode == "ass"
    assert request.container_preset == "mkv"


def test_batch_import_dialog_renders_as_download_inbox_offscreen(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QDialogButtonBox,
        QLabel,
        QPushButton,
        QTableWidget,
    )

    from trusted_ui.batch_import_dialog import show_batch_import_dialog

    app = QApplication.instance() or QApplication([])
    def inspect_dialog(dialog):
        table = dialog.findChild(QTableWidget)
        select_all = dialog.findChild(QPushButton, "batchImportSelectAll")
        clear_all = dialog.findChild(QPushButton, "batchImportClearAll")
        source = dialog.findChild(QLabel, "downloadInboxSource")
        summary = dialog.findChild(QLabel, "downloadInboxSummary")
        buttons = dialog.findChild(QDialogButtonBox)
        confirm = buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert table is not None
        assert dialog.windowTitle() == "下載收件匣"
        assert source is not None and source.text() == "手動輸入"
        assert summary is not None and "有效 1" in summary.text()
        assert "略過 1" in summary.text()
        assert confirm.text() == "確認並加入佇列"
        assert confirm.objectName() == "primary"
        assert select_all is not None and select_all.text() == "全選有效項目"
        assert clear_all is not None and clear_all.text() == "全部取消"
        assert table.item(0, 0).checkState() == Qt.CheckState.Checked
        clear_all.click()
        assert table.item(0, 0).checkState() == Qt.CheckState.Unchecked
        assert not confirm.isEnabled()
        select_all.click()
        assert table.item(0, 0).checkState() == Qt.CheckState.Checked
        assert confirm.isEnabled()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", inspect_dialog)
    result = BatchImportResult(
        (
            BatchImportEntry(1, "https://example.com/video", "Title", "Artist"),
        ),
        (BatchImportIssue(2, "invalid", "URL is malformed"),),
    )
    assert show_batch_import_dialog(result, source_label="手動輸入") is None
    app.processEvents()
