"""Reusable trusted audio and video preview controls for YouTube items."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading


@dataclass(frozen=True, slots=True)
class PreviewSource:
    url: str
    duration: float | None = None
    title: str = ""


def create_media_preview_controls(
    parent: object,
    *,
    source: Callable[[], PreviewSource | None],
    audio_provider: Callable[[str], object],
    video_provider: Callable[[], object],
    audio_available: Callable[[], bool],
    video_available: Callable[[], bool],
    object_prefix: str,
) -> object:
    """Create one bounded preview controller without exposing MOD-owned UI."""

    from PySide6.QtCore import QObject, QUrl, Signal
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    class PreviewBridge(QObject):
        finished = Signal(str, int, object, str, str)

    class MediaPreviewControls(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.generation = 0
            self.busy_kind = ""
            self.selection_url = ""
            self.closing = False
            self.audio_owner: object | None = None
            self.audio_path = ""
            self.video_owner: object | None = None
            self.video_path = ""
            self.video_dialog: object | None = None
            self.video_player: object | None = None
            self.bridge = PreviewBridge(self)
            self.bridge.finished.connect(self.show_prepared_preview)
            self.audio_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.audio_output.setVolume(0.7)
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.mediaStatusChanged.connect(
                self.handle_audio_status
            )
            self.audio_player.errorOccurred.connect(self.handle_audio_error)

            row = QHBoxLayout(self)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            self.audio_button = QPushButton("試聽 30 秒")
            self.audio_button.setObjectName(f"{object_prefix}AudioPreview")
            self.audio_button.clicked.connect(self.prepare_audio)
            self.stop_audio_button = QPushButton("停止試聽")
            self.stop_audio_button.setObjectName(
                f"{object_prefix}StopAudioPreview"
            )
            self.stop_audio_button.clicked.connect(self.stop_audio)
            self.video_button = QPushButton("影片預覽 60 秒")
            self.video_button.setObjectName(f"{object_prefix}VideoPreview")
            self.video_button.clicked.connect(self.prepare_video)
            self.stop_video_button = QPushButton("停止影片預覽")
            self.stop_video_button.setObjectName(
                f"{object_prefix}StopVideoPreview"
            )
            self.stop_video_button.clicked.connect(self.stop_video)
            self.status = QLabel("選取單一影片後可試聽或預覽。")
            self.status.setObjectName(f"{object_prefix}PreviewStatus")
            self.status.setWordWrap(True)
            row.addWidget(self.audio_button)
            row.addWidget(self.stop_audio_button)
            row.addWidget(self.video_button)
            row.addWidget(self.stop_video_button)
            row.addWidget(self.status, 1)
            self.refresh()

        @staticmethod
        def available(check: Callable[[], bool]) -> bool:
            try:
                return bool(check())
            except (AttributeError, KeyError, LookupError, RuntimeError, ValueError):
                return False

        def current_source(self) -> PreviewSource | None:
            try:
                value = source()
            except (AttributeError, IndexError, RuntimeError, ValueError):
                return None
            return value if isinstance(value, PreviewSource) else None

        def refresh(self) -> None:
            selected = self.current_source()
            selected_url = selected.url if selected is not None else ""
            if selected_url != self.selection_url:
                self.selection_url = selected_url
                if self.busy_kind or self.audio_path or self.video_path:
                    self.stop_all()
            audio_ready = selected is not None and self.available(audio_available)
            video_ready = selected is not None and self.available(video_available)
            if self.busy_kind == "audio" and not audio_ready:
                self.stop_audio()
            if self.busy_kind == "video" and not video_ready:
                self.stop_video()
            self.audio_button.setEnabled(audio_ready and not self.busy_kind)
            self.video_button.setEnabled(video_ready and not self.busy_kind)
            self.stop_audio_button.setEnabled(
                self.busy_kind == "audio" or bool(self.audio_path)
            )
            self.stop_video_button.setEnabled(
                self.busy_kind == "video" or bool(self.video_path)
            )
            if not self.busy_kind and not self.audio_path and not self.video_path:
                if selected is None:
                    self.status.setText("目前網址／選取結果不是單一影片。")
                elif not audio_ready:
                    self.status.setText("請先啟用 YouTube 主 MOD。")
                elif not video_ready:
                    self.status.setText(
                        "可試聽；啟用 YouTube Player 子 MOD 後可預覽影片。"
                    )
                else:
                    self.status.setText("可試聽 30 秒或預覽影片 60 秒。")

        def cleanup_audio(self) -> None:
            owner, path = self.audio_owner, self.audio_path
            self.audio_owner = None
            self.audio_path = ""
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            if owner is not None and path:
                try:
                    owner.cleanup_audio_preview(path)
                except OSError:
                    pass

        def cleanup_video(self) -> None:
            child = self.video_dialog
            player = self.video_player
            owner, path = self.video_owner, self.video_path
            self.video_dialog = None
            self.video_player = None
            self.video_owner = None
            self.video_path = ""
            if player is not None:
                player.stop()
                player.setSource(QUrl())
            if child is not None and child.isVisible():
                child.close()
            if owner is not None and path:
                try:
                    owner.cleanup_video_preview(path)
                except OSError:
                    pass

        def stop_all(self) -> None:
            self.generation += 1
            self.busy_kind = ""
            self.cleanup_audio()
            self.cleanup_video()

        def stop_audio(self) -> None:
            was_active = self.busy_kind == "audio" or bool(self.audio_path)
            self.generation += 1
            if self.busy_kind == "audio":
                self.busy_kind = ""
            self.cleanup_audio()
            self.refresh()
            if was_active and not self.closing:
                self.status.setText("試聽已停止，暫存音訊已清除。")

        def stop_video(self) -> None:
            was_active = self.busy_kind == "video" or bool(self.video_path)
            self.generation += 1
            if self.busy_kind == "video":
                self.busy_kind = ""
            self.cleanup_video()
            self.refresh()
            if was_active and not self.closing:
                self.status.setText("影片預覽已停止，暫存影片已清除。")

        def prepare_audio(self) -> None:
            selected = self.current_source()
            if selected is None or not self.available(audio_available):
                self.refresh()
                return
            self.stop_all()
            self.generation += 1
            generation = self.generation
            self.busy_kind = "audio"
            self.status.setText("正在準備 30 秒音訊…")
            self.refresh()

            def worker() -> None:
                try:
                    owner = audio_provider(selected.url)
                    path = owner.prepare_audio_preview(
                        selected.url,
                        duration=float(selected.duration or 30),
                        preview_length=30,
                    )
                    if self.closing or generation != self.generation:
                        owner.cleanup_audio_preview(path)
                        return
                    self.bridge.finished.emit(
                        "audio", generation, owner, str(path), ""
                    )
                except Exception as error:
                    if not self.closing and generation == self.generation:
                        self.bridge.finished.emit(
                            "audio", generation, None, "", str(error)
                        )

            threading.Thread(
                target=worker,
                name=f"{object_prefix}-audio-preview",
                daemon=True,
            ).start()

        def prepare_video(self) -> None:
            selected = self.current_source()
            if selected is None or not self.available(video_available):
                self.refresh()
                return
            self.stop_all()
            self.generation += 1
            generation = self.generation
            self.busy_kind = "video"
            self.status.setText("正在準備 60 秒影片…")
            self.refresh()

            def worker() -> None:
                try:
                    owner = video_provider()
                    path = owner.prepare_video_preview(
                        selected.url,
                        duration=float(selected.duration or 60),
                        preview_length=60,
                    )
                    if self.closing or generation != self.generation:
                        owner.cleanup_video_preview(path)
                        return
                    self.bridge.finished.emit(
                        "video", generation, owner, str(path), ""
                    )
                except Exception as error:
                    if not self.closing and generation == self.generation:
                        self.bridge.finished.emit(
                            "video", generation, None, "", str(error)
                        )

            threading.Thread(
                target=worker,
                name=f"{object_prefix}-video-preview",
                daemon=True,
            ).start()

        def show_prepared_preview(
            self,
            kind: str,
            generation: int,
            owner: object | None,
            path: str,
            error: str,
        ) -> None:
            if self.closing or generation != self.generation:
                if owner is not None and path:
                    cleanup = getattr(owner, f"cleanup_{kind}_preview", None)
                    if callable(cleanup):
                        cleanup(path)
                return
            self.busy_kind = ""
            if error or owner is None or not path:
                self.refresh()
                self.status.setText(
                    f"{'試聽' if kind == 'audio' else '影片預覽'}失敗："
                    f"{error or '沒有可播放內容'}"
                )
                return
            if kind == "audio":
                self.audio_owner = owner
                self.audio_path = path
                self.audio_player.setSource(QUrl.fromLocalFile(path))
                self.audio_player.play()
                self.status.setText("正在試聽 30 秒；可按停止。")
            else:
                self.video_owner = owner
                self.video_path = path
                child = QDialog(self)
                child.setWindowTitle("YouTube 影片預覽（最多 60 秒）")
                child.resize(720, 480)
                layout = QVBoxLayout(child)
                video = QVideoWidget(child)
                layout.addWidget(video, 1)
                close_button = QPushButton("停止並關閉", child)
                close_button.clicked.connect(child.close)
                layout.addWidget(close_button)
                player = QMediaPlayer(child)
                audio = QAudioOutput(child)
                audio.setVolume(0.7)
                player.setAudioOutput(audio)
                player.setVideoOutput(video)
                player.setSource(QUrl.fromLocalFile(path))
                child._player = player
                child._audio = audio
                child.finished.connect(lambda _result: self.stop_video())
                self.video_dialog = child
                self.video_player = player
                child.show()
                player.play()
                self.status.setText("正在預覽影片；最多 60 秒。")
            self.refresh()

        def handle_audio_status(self, status: object) -> None:
            if (
                status == QMediaPlayer.MediaStatus.EndOfMedia
                and self.audio_path
            ):
                self.cleanup_audio()
                self.refresh()
                self.status.setText("30 秒試聽已結束。")

        def handle_audio_error(self, *_error: object) -> None:
            if not self.audio_path:
                return
            message = self.audio_player.errorString() or "無法播放音訊"
            self.cleanup_audio()
            self.refresh()
            self.status.setText(f"音訊播放失敗：{message}")

        def shutdown(self) -> None:
            if self.closing:
                return
            self.closing = True
            self.stop_all()

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return MediaPreviewControls()
