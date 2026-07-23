"""Bounded in-memory thumbnail loading for trusted search results."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from urllib.parse import urlsplit

_ALLOWED_HOSTS = {"i.ytimg.com", "img.youtube.com"}
_ALLOWED_HOST_SUFFIXES = (".hdslb.com", ".bahamut.com.tw", ".fbcdn.net")
_MAX_BYTES = 1024 * 1024
_MAX_IMAGE_PIXELS = 16_000_000
_MAX_CACHE_ITEMS = 40
_MAX_PENDING_ITEMS = 32
_TRANSFER_TIMEOUT_MS = 8_000
_DECODE_WIDTH = 384
_DECODE_HEIGHT = 216
_DISPLAY_WIDTH = 96
_DISPLAY_HEIGHT = 54
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def thumbnail_resource_limits() -> dict[str, int]:
    """Expose stable memory/network bounds for diagnostics and regression tests."""

    return {
        "response_bytes": _MAX_BYTES,
        "image_pixels": _MAX_IMAGE_PIXELS,
        "cache_items": _MAX_CACHE_ITEMS,
        "pending_items": _MAX_PENDING_ITEMS,
        "timeout_ms": _TRANSFER_TIMEOUT_MS,
        "decode_width": _DECODE_WIDTH,
        "decode_height": _DECODE_HEIGHT,
    }


def valid_thumbnail_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold()
        return (
            parsed.scheme == "https"
            and (
                host in _ALLOWED_HOSTS
                or any(host.endswith(suffix) for suffix in _ALLOWED_HOST_SUFFIXES)
            )
            and not parsed.username
            and not parsed.password
            and parsed.port is None
            and not parsed.fragment
            and len(url) <= 1000
        )
    except ValueError:
        return False


def valid_thumbnail_response(
    *, network_ok: bool, status_code: object, content_type: object
) -> bool:
    if not network_ok or isinstance(status_code, bool):
        return False
    if not isinstance(status_code, int) or not 200 <= status_code < 300:
        return False
    media_type = str(content_type or "").partition(";")[0].strip().casefold()
    return not media_type or media_type in _ALLOWED_CONTENT_TYPES


def decode_thumbnail(data: bytes) -> object | None:
    from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
    from PySide6.QtGui import QImageReader, QPixmap

    if not data or len(data) > _MAX_BYTES:
        return None
    buffer = QBuffer()
    buffer.setData(data)
    if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
        return None
    reader = QImageReader(buffer)
    reader.setAutoTransform(True)
    reader.setDecideFormatFromContent(True)
    dimensions = reader.size()
    if (
        not dimensions.isValid()
        or dimensions.width() <= 0
        or dimensions.height() <= 0
        or dimensions.width() * dimensions.height() > _MAX_IMAGE_PIXELS
    ):
        return None
    reader.setScaledSize(
        dimensions.scaled(
            QSize(_DECODE_WIDTH, _DECODE_HEIGHT),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
    )
    image = reader.read()
    if (
        image.isNull()
        or reader.error() != QImageReader.ImageReaderError.UnknownError
        or image.width() * image.height() > _MAX_IMAGE_PIXELS
    ):
        return None
    pixmap = QPixmap.fromImage(image)
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        QSize(_DISPLAY_WIDTH, _DISPLAY_HEIGHT),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def create_thumbnail_loader(parent: object = None) -> object:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QPixmap
    from PySide6.QtNetwork import (
        QNetworkAccessManager,
        QNetworkReply,
        QNetworkRequest,
    )

    class ThumbnailLoader(QNetworkAccessManager):
        def __init__(self) -> None:
            super().__init__(parent)
            self.cache: OrderedDict[str, QPixmap] = OrderedDict()
            self.pending: dict[str, list[Callable[[object | None], None]]] = {}
            self.replies: dict[str, QNetworkReply] = {}

        def _complete(self, url: str, pixmap: object | None) -> None:
            callbacks = self.pending.pop(url, ())
            for callback in callbacks:
                try:
                    callback(pixmap)
                except RuntimeError:
                    # The owning widget may have closed while the reply completed.
                    continue

        def cancel_pending(self) -> None:
            self.pending.clear()
            replies = tuple(self.replies.values())
            self.replies.clear()
            for reply in replies:
                if reply.isRunning():
                    reply.abort()

        def shutdown(self) -> None:
            """Cancel network work and release cached pixmaps before widget teardown."""

            self.cancel_pending()
            self.cache.clear()

        def load(self, url: str, callback: Callable[[object | None], None]) -> None:
            if not valid_thumbnail_url(url):
                callback(None)
                return
            cached = self.cache.get(url)
            if cached is not None:
                self.cache.move_to_end(url)
                callback(cached)
                return
            waiting = self.pending.get(url)
            if waiting is not None:
                waiting.append(callback)
                return
            if len(self.pending) >= _MAX_PENDING_ITEMS:
                callback(None)
                return
            self.pending[url] = [callback]
            request = QNetworkRequest(QUrl(url))
            request.setAttribute(
                QNetworkRequest.Attribute.RedirectPolicyAttribute,
                QNetworkRequest.RedirectPolicy.SameOriginRedirectPolicy,
            )
            request.setRawHeader(b"Accept", b"image/webp,image/png,image/jpeg")
            request.setTransferTimeout(_TRANSFER_TIMEOUT_MS)
            reply = self.get(request)
            self.replies[url] = reply
            oversized = [False]

            def check_size(received: int, total: int) -> None:
                if received > _MAX_BYTES or total > _MAX_BYTES:
                    oversized[0] = True
                    reply.abort()

            def finished() -> None:
                self.replies.pop(url, None)
                data = bytes(reply.readAll())
                network_ok = reply.error() == QNetworkReply.NetworkError.NoError
                status_code = reply.attribute(
                    QNetworkRequest.Attribute.HttpStatusCodeAttribute
                )
                content_type = reply.header(
                    QNetworkRequest.KnownHeaders.ContentTypeHeader
                )
                reply.deleteLater()
                if oversized[0] or not valid_thumbnail_response(
                    network_ok=network_ok,
                    status_code=status_code,
                    content_type=content_type,
                ):
                    self._complete(url, None)
                    return
                pixmap = decode_thumbnail(data)
                if pixmap is None:
                    self._complete(url, None)
                    return
                self.cache[url] = pixmap
                self.cache.move_to_end(url)
                while len(self.cache) > _MAX_CACHE_ITEMS:
                    self.cache.popitem(last=False)
                self._complete(url, pixmap)

            reply.downloadProgress.connect(check_size)
            reply.finished.connect(finished)

    return ThumbnailLoader()
