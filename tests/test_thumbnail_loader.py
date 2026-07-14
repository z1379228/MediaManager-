from trusted_ui.thumbnail_loader import (
    create_thumbnail_loader,
    decode_thumbnail,
    thumbnail_resource_limits,
    valid_thumbnail_response,
    valid_thumbnail_url,
)


def test_thumbnail_memory_and_network_limits_are_explicit() -> None:
    limits = thumbnail_resource_limits()
    assert limits == {
        "response_bytes": 1024 * 1024,
        "image_pixels": 16_000_000,
        "cache_items": 40,
        "pending_items": 32,
        "timeout_ms": 8_000,
        "decode_width": 384,
        "decode_height": 216,
    }


def test_thumbnail_url_accepts_only_bounded_youtube_https_hosts() -> None:
    assert valid_thumbnail_url("https://i.ytimg.com/vi/example/mqdefault.jpg")
    assert valid_thumbnail_url("https://img.youtube.com/vi/example/0.jpg")
    assert not valid_thumbnail_url("http://i.ytimg.com/vi/example/0.jpg")
    assert not valid_thumbnail_url("https://example.com/thumbnail.jpg")
    assert not valid_thumbnail_url("https://user@i.ytimg.com/thumbnail.jpg")


def test_thumbnail_response_rejects_failed_or_non_image_replies() -> None:
    assert valid_thumbnail_response(
        network_ok=True,
        status_code=200,
        content_type="image/jpeg; charset=binary",
    )
    assert not valid_thumbnail_response(
        network_ok=False,
        status_code=200,
        content_type="image/jpeg",
    )
    assert not valid_thumbnail_response(
        network_ok=True,
        status_code=404,
        content_type="image/jpeg",
    )
    assert not valid_thumbnail_response(
        network_ok=True,
        status_code=200,
        content_type="text/html",
    )


def test_thumbnail_decoder_returns_bounded_pixmap(monkeypatch) -> None:
    import pytest

    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    image = QImage(640, 360, QImage.Format.Format_RGB32)
    image.fill(QColor("#345678"))
    buffer = QBuffer()
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")

    pixmap = decode_thumbnail(bytes(buffer.data()))
    assert pixmap is not None
    assert pixmap.width() <= 96
    assert pixmap.height() <= 54
    assert decode_thumbnail(b"not an image") is None
    app.processEvents()


def test_thumbnail_loader_cancels_pending_replies(monkeypatch) -> None:
    import pytest

    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    class Reply:
        aborted = False

        def isRunning(self) -> bool:
            return True

        def abort(self) -> None:
            self.aborted = True

    app = QApplication.instance() or QApplication([])
    loader = create_thumbnail_loader()
    reply = Reply()
    loader.pending["https://i.ytimg.com/example.jpg"] = [lambda _: None]
    loader.replies["https://i.ytimg.com/example.jpg"] = reply

    loader.cancel_pending()

    assert loader.pending == {}
    assert loader.replies == {}
    assert reply.aborted
    loader.deleteLater()
    app.processEvents()
