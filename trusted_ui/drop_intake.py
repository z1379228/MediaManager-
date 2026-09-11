"""Trusted Qt bridge for bounded drag-and-drop intake."""

from __future__ import annotations

from collections.abc import Callable

from core.drop_intake import DropIntake, prepare_drop_intake


def intake_from_mime_data(mime_data: object) -> DropIntake:
    """Convert one QMimeData payload without executing or moving its content."""

    has_urls = getattr(mime_data, "hasUrls", None)
    urls_reader = getattr(mime_data, "urls", None)
    local_paths: list[str] = []
    remote_urls: list[str] = []
    if callable(has_urls) and has_urls() and callable(urls_reader):
        for value in tuple(urls_reader())[:501]:
            is_local_file = getattr(value, "isLocalFile", None)
            if callable(is_local_file) and is_local_file():
                local_file = getattr(value, "toLocalFile", None)
                local_paths.append(str(local_file() if callable(local_file) else ""))
            else:
                text_reader = getattr(value, "toString", None)
                remote_urls.append(str(text_reader() if callable(text_reader) else ""))

    text = "\n".join(remote_urls)
    if not local_paths and not remote_urls:
        has_text = getattr(mime_data, "hasText", None)
        text_reader = getattr(mime_data, "text", None)
        if callable(has_text) and has_text() and callable(text_reader):
            text = str(text_reader())
    return prepare_drop_intake(text=text, local_paths=local_paths)


def install_drop_intake(
    widget: object,
    on_drop: Callable[[DropIntake], None],
    *,
    on_error: Callable[[str], None] | None = None,
) -> object:
    """Intercept drops on one explicit field; ordinary clipboard input is unchanged."""

    from PySide6.QtCore import QEvent, QObject, Qt

    class DropIntakeFilter(QObject):
        def eventFilter(self, watched: object, event: object) -> bool:
            event_type = event.type()
            if event_type == QEvent.Type.DragEnter:
                mime_data = event.mimeData()
                if mime_data.hasUrls() or mime_data.hasText():
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.accept()
                else:
                    event.ignore()
                return True
            if event_type != QEvent.Type.Drop:
                return False
            try:
                intake = intake_from_mime_data(event.mimeData())
            except (OSError, TypeError, ValueError) as error:
                if on_error is not None:
                    on_error(str(error))
                event.ignore()
                return True
            try:
                on_drop(intake)
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                if on_error is not None:
                    on_error(str(error))
                event.ignore()
                return True
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return True

    target = widget.viewport() if hasattr(widget, "viewport") else widget
    target.setAcceptDrops(True)
    drop_filter = DropIntakeFilter(target)
    target.installEventFilter(drop_filter)
    # Keep the Python wrapper alive for as long as the Qt target exists.
    target._media_manager_drop_intake_filter = drop_filter
    return drop_filter


def issue_summary(intake: DropIntake, *, limit: int = 3) -> str:
    """Return a bounded, non-executing summary for a trusted status label."""

    issues = intake.issues[: max(0, limit)]
    text = "；".join(issue.reason for issue in issues)
    remaining = len(intake.issues) - len(issues)
    if remaining > 0:
        text = f"{text}；另有 {remaining} 項" if text else f"另有 {remaining} 項"
    return text
