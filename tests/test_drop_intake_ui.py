from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl

from trusted_ui.drop_intake import intake_from_mime_data


def test_mime_intake_does_not_duplicate_url_list_text(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    mime = QMimeData()
    mime.setUrls(
        (
            QUrl.fromLocalFile(str(media)),
            QUrl("https://example.com/video"),
        )
    )

    result = intake_from_mime_data(mime)

    assert result.media_files == (media.resolve(),)
    assert result.urls == ("https://example.com/video",)
    assert result.issues == ()


def test_mime_intake_accepts_plain_multiline_url_text() -> None:
    mime = QMimeData()
    mime.setText("https://example.com/one\nhttps://example.com/two")

    result = intake_from_mime_data(mime)

    assert result.urls == (
        "https://example.com/one",
        "https://example.com/two",
    )
