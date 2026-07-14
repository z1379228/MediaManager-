from pathlib import Path

from core.media_library import classify, scan_media


def test_scan_media_classifies_supported_files(tmp_path: Path) -> None:
    (tmp_path / "photo.JPG").write_bytes(b"image")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
    album = tmp_path / "album"
    album.mkdir()
    (album / "song.flac").write_bytes(b"audio")
    assert [(x.name, x.media_type) for x in scan_media(tmp_path)] == [
        ("photo.JPG", "\u5716\u7247"),
        ("song.flac", "\u97f3\u8a0a"),
    ]
    assert classify(Path("clip.MP4")) == "\u5f71\u7247"