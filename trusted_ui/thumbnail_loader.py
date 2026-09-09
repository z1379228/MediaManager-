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


def visible_thumbnail_rows(
    table: object,
    total: int,
    *,
    overscan: int = 2,
) -> range:
    """Return a bounded visible-row window without walking every result."""

    if total <= 0:
        return range(0)
    viewport = table.viewport()
    height = max(1, int(viewport.height()))
    top = int(table.rowAt(0))
    if top < 0:
        top = 0
    bottom = int(table.rowAt(height - 1))
    if bottom < top:
        row_height = max(1, int(table.rowHeight(top)))
        bottom = min(total - 1, top + max(1, height // row_height))
    margin = max(0, overscan)
    return range(
        max(0, top - margin),
        min(total, bottom + margin + 1),
    )


def cancel_thumbnail_clients(root: object) -> int:
    """Cancel thumbnail callbacks owned by one workspace before it becomes hidden."""

    from PySide6.QtCore import QObject

    cancelled = 0
    for client in root.findChildren(QObject, "trustedThumbnailClient"):
        cancel = getattr(client, "cancel_pending", None)
        if callable(cancel):
            cancel()
            cancelled += 1
    return cancelled


def resume_thumbnail_clients(root: object) -> int:
    """Ask one visible workspace to refill its bounded thumbnail window."""

    from PySide6.QtCore import QObject

    resumed = 0
    for client in root.findChildren(QObject, "trustedThumbnailClient"):
        resume = getattr(client, "resume", None)
        if callable(resume):
            resume()
            resumed += 1
    return resumed


def create_thumbnail_loader(parent: object = None) -> object:
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtGui import QPixmap
    from PySide6.QtNetwork import (
        QNetworkAccessManager,
        QNetworkReply,
        QNetworkRequest,
    )

    class ThumbnailService(QNetworkAccessManager):
        def __init__(self, owner: object = None) -> None:
            super().__init__(owner)
            self.setObjectName("trustedThumbnailService")
            self.cache: OrderedDict[str, QPixmap] = OrderedDict()
            self.pending: dict[
                str,
                dict[object, list[Callable[[object | None], None]]],
            ] = {}
            self.replies: dict[str, QNetworkReply] = {}

        def _complete(self, url: str, pixmap: object | None) -> None:
            waiting = self.pending.pop(url, {})
            for callbacks in waiting.values():
                for callback in callbacks:
                    try:
                        callback(pixmap)
                    except RuntimeError:
                        # The owning widget may have closed while the reply completed.
                        continue

        def cancel_client(self, client: object) -> None:
            for url, waiting in tuple(self.pending.items()):
                waiting.pop(client, None)
                if waiting:
                    continue
                self.pending.pop(url, None)
                reply = self.replies.pop(url, None)
                if reply is not None and reply.isRunning():
                    reply.abort()

        def cancel_all_pending(self) -> None:
            self.pending.clear()
            replies = tuple(self.replies.values())
            self.replies.clear()
            for reply in replies:
                if reply.isRunning():
                    reply.abort()

        def clear_cache(self) -> None:
            self.cache.clear()

        def shutdown_service(self) -> None:
            self.cancel_all_pending()
            self.clear_cache()

        def load_for(
            self,
            client: object,
            url: str,
            callback: Callable[[object | None], None],
        ) -> None:
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
                waiting.setdefault(client, []).append(callback)
                return
            if len(self.pending) >= _MAX_PENDING_ITEMS:
                callback(None)
                return
            self.pending[url] = {client: [callback]}
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

    class ThumbnailLoaderClient(QObject):
        def __init__(
            self,
            service: object,
            owner: object = None,
            *,
            owns_service: bool = False,
        ) -> None:
            super().__init__(owner)
            self.setObjectName("trustedThumbnailClient")
            self.service = service
            self.token = object()
            self.owns_service = owns_service
            self.closed = False
            self.cancel_handlers: list[Callable[[], None]] = []
            self.resume_handlers: list[Callable[[], None]] = []

        def load(
            self,
            url: str,
            callback: Callable[[object | None], None],
        ) -> None:
            if self.closed:
                callback(None)
                return
            self.service.load_for(self.token, url, callback)

        def cancel_pending(self) -> None:
            self.service.cancel_client(self.token)
            for handler in tuple(self.cancel_handlers):
                try:
                    handler()
                except RuntimeError:
                    continue

        def on_cancel(self, handler: Callable[[], None]) -> None:
            self.cancel_handlers.append(handler)

        def on_resume(self, handler: Callable[[], None]) -> None:
            self.resume_handlers.append(handler)

        def resume(self) -> None:
            if self.closed:
                return
            for handler in tuple(self.resume_handlers):
                try:
                    handler()
                except RuntimeError:
                    continue

        def shutdown(self) -> None:
            if self.closed:
                return
            self.closed = True
            self.cancel_pending()
            self.cancel_handlers.clear()
            self.resume_handlers.clear()
            if self.owns_service:
                self.service.shutdown_service()
                self.service.deleteLater()

    root = parent
    if root is not None:
        parent_of = getattr(root, "parent", None)
        while callable(parent_of):
            candidate = parent_of()
            if candidate is None:
                break
            root = candidate
            parent_of = getattr(root, "parent", None)
    attribute = "_media_manager_thumbnail_service"
    service = getattr(root, attribute, None) if root is not None else None
    owns_service = service is None and root is None
    if service is None:
        service = ThumbnailService(root)
        if root is not None:
            setattr(root, attribute, service)
    return ThumbnailLoaderClient(
        service,
        parent,
        owns_service=owns_service,
    )
