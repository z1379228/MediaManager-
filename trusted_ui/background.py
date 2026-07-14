"""Persistent, resource-bounded background image support for the trusted UI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

_ALLOWED_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
_MAX_IMAGE_BYTES = 50 * 1024 * 1024
_MAX_IMAGE_PIXELS = 32_000_000
_MAX_DECODE_EDGE = 4096
_MANAGED_BACKGROUND_STEM = "appearance-background"


def appearance_settings_path(settings_root: Path) -> Path:
    return settings_root / "appearance.json"


def valid_background_path(path: Path) -> Path | None:
    try:
        candidate = path.expanduser().resolve()
        if (
            candidate.suffix.casefold() not in _ALLOWED_SUFFIXES
            or not candidate.is_file()
            or candidate.stat().st_size > _MAX_IMAGE_BYTES
        ):
            return None
        return candidate
    except OSError:
        return None


def load_background_path(settings_root: Path) -> Path | None:
    try:
        data = json.loads(appearance_settings_path(settings_root).read_text("utf-8"))
        value = data.get("background_image")
        if not isinstance(value, str) or not value:
            return None
        return valid_background_path(Path(value))
    except OSError, ValueError, TypeError, AttributeError:
        return None


def save_background_path(settings_root: Path, path: Path | None) -> None:
    settings_root.mkdir(parents=True, exist_ok=True)
    target = appearance_settings_path(settings_root)
    validated = valid_background_path(path) if path is not None else None
    if path is not None and validated is None:
        raise ValueError(
            "background image is missing, unsupported, or larger than 50 MB"
        )
    payload = json.dumps(
        {"schema_version": 1, "background_image": str(validated) if validated else ""},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)


def store_background_copy(settings_root: Path, path: Path) -> Path:
    source = valid_background_path(path)
    if source is None:
        raise ValueError(
            "background image is missing, unsupported, or larger than 50 MB"
        )
    settings_root = settings_root.expanduser().resolve()
    settings_root.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.casefold()
    target = settings_root / f"{_MANAGED_BACKGROUND_STEM}{suffix}"
    temporary = settings_root / f".{_MANAGED_BACKGROUND_STEM}.tmp{suffix}"
    if source != target:
        shutil.copy2(source, temporary)
        temporary.replace(target)
    for candidate_suffix in _ALLOWED_SUFFIXES:
        stale = settings_root / f"{_MANAGED_BACKGROUND_STEM}{candidate_suffix}"
        if stale != target and (stale.exists() or stale.is_symlink()):
            stale.unlink()
    save_background_path(settings_root, target)
    return target


def clear_background_copy(settings_root: Path) -> None:
    settings_root = settings_root.expanduser().resolve()
    save_background_path(settings_root, None)
    for suffix in _ALLOWED_SUFFIXES:
        target = settings_root / f"{_MANAGED_BACKGROUND_STEM}{suffix}"
        if target.exists() or target.is_symlink():
            target.unlink()


def create_background_widget(path: Path | None, parent: object = None) -> object:
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import (
        QColor,
        QImageReader,
        QLinearGradient,
        QPainter,
        QPixmap,
        QRadialGradient,
    )
    from PySide6.QtWidgets import QWidget

    class BackgroundWidget(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self._pixmap = QPixmap()
            self._scaled_pixmap = QPixmap()
            self._scaled_size = QSize()
            self.set_background(path)

        def _clear_scaled_cache(self) -> None:
            self._scaled_pixmap = QPixmap()
            self._scaled_size = QSize()

        def set_background(self, selected: Path | None) -> bool:
            if selected is None:
                self._pixmap = QPixmap()
                self._clear_scaled_cache()
                self.update()
                return True
            validated = valid_background_path(selected)
            if validated is None:
                return False
            reader = QImageReader(str(validated))
            reader.setAutoTransform(True)
            reader.setDecideFormatFromContent(True)
            dimensions = reader.size()
            if (
                not dimensions.isValid()
                or dimensions.width() <= 0
                or dimensions.height() <= 0
                or dimensions.width() * dimensions.height() > _MAX_IMAGE_PIXELS
            ):
                return False
            bounded = dimensions.scaled(
                QSize(_MAX_DECODE_EDGE, _MAX_DECODE_EDGE),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            if bounded != dimensions:
                reader.setScaledSize(bounded)
            image = reader.read()
            if (
                image.isNull()
                or reader.error() != QImageReader.ImageReaderError.UnknownError
                or image.width() * image.height() > _MAX_IMAGE_PIXELS
            ):
                return False
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                return False
            self._pixmap = pixmap
            self._clear_scaled_cache()
            self.update()
            return True

        def paintEvent(self, event: object) -> None:
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(
                QPainter.RenderHint.SmoothPixmapTransform,
                True,
            )
            if self._pixmap.isNull():
                base = QLinearGradient(0, 0, self.width(), self.height())
                base.setColorAt(0.0, QColor("#071426"))
                base.setColorAt(0.48, QColor("#0a1020"))
                base.setColorAt(1.0, QColor("#17132a"))
                painter.fillRect(self.rect(), base)

                radius = max(320.0, max(self.width(), self.height()) * 0.72)
                blue = QRadialGradient(
                    self.width() * 0.84,
                    self.height() * 0.08,
                    radius,
                )
                blue.setColorAt(0.0, QColor(59, 130, 246, 92))
                blue.setColorAt(0.42, QColor(37, 99, 235, 34))
                blue.setColorAt(1.0, QColor(37, 99, 235, 0))
                painter.fillRect(self.rect(), blue)

                violet = QRadialGradient(
                    self.width() * 0.08,
                    self.height() * 0.9,
                    radius * 0.85,
                )
                violet.setColorAt(0.0, QColor(139, 92, 246, 62))
                violet.setColorAt(0.5, QColor(99, 72, 190, 20))
                violet.setColorAt(1.0, QColor(99, 72, 190, 0))
                painter.fillRect(self.rect(), violet)

                horizon = QLinearGradient(0, 0, 0, self.height())
                horizon.setColorAt(0.0, QColor(255, 255, 255, 8))
                horizon.setColorAt(0.45, QColor(255, 255, 255, 0))
                horizon.setColorAt(1.0, QColor(2, 6, 15, 72))
                painter.fillRect(self.rect(), horizon)
                return
            if self._scaled_pixmap.isNull() or self._scaled_size != self.size():
                self._scaled_pixmap = self._pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._scaled_size = self.size()
            x = (self.width() - self._scaled_pixmap.width()) // 2
            y = (self.height() - self._scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._scaled_pixmap)
            overlay = QLinearGradient(0, 0, 0, self.height())
            overlay.setColorAt(0.0, QColor(4, 10, 22, 184))
            overlay.setColorAt(0.48, QColor(5, 11, 22, 132))
            overlay.setColorAt(1.0, QColor(5, 9, 19, 196))
            painter.fillRect(self.rect(), overlay)

            vignette = QRadialGradient(
                self.width() * 0.5,
                self.height() * 0.45,
                max(280.0, max(self.width(), self.height()) * 0.78),
            )
            vignette.setColorAt(0.0, QColor(3, 7, 16, 0))
            vignette.setColorAt(0.64, QColor(3, 7, 16, 18))
            vignette.setColorAt(1.0, QColor(3, 7, 16, 132))
            painter.fillRect(self.rect(), vignette)

    return BackgroundWidget()
