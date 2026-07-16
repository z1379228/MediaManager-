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


def test_batch_import_dialog_renders_offscreen(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog, QPushButton, QTableWidget

    from trusted_ui.batch_import_dialog import show_batch_import_dialog

    app = QApplication.instance() or QApplication([])
    def inspect_dialog(dialog):
        table = dialog.findChild(QTableWidget)
        select_all = dialog.findChild(QPushButton, "batchImportSelectAll")
        clear_all = dialog.findChild(QPushButton, "batchImportClearAll")
        assert table is not None
        assert select_all is not None and select_all.text() == "全選有效項目"
        assert clear_all is not None and clear_all.text() == "全部取消"
        assert table.item(0, 0).checkState() == Qt.CheckState.Checked
        clear_all.click()
        assert table.item(0, 0).checkState() == Qt.CheckState.Unchecked
        select_all.click()
        assert table.item(0, 0).checkState() == Qt.CheckState.Checked
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", inspect_dialog)
    result = BatchImportResult(
        (
            BatchImportEntry(1, "https://example.com/video", "Title", "Artist"),
        ),
        (BatchImportIssue(2, "invalid", "URL is malformed"),),
    )
    assert show_batch_import_dialog(result) is None
    app.processEvents()
