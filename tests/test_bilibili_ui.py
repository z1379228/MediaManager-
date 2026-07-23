from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.storage.paths import AppPaths
from trusted_ui.download_panel import create_download_panel


ROOT = Path(__file__).resolve().parents[1]
BUILTIN_ROOT = ROOT / "mod" / "builtin"


def _use_current_builtin_hashes(monkeypatch) -> None:
    for provider_id, files in tuple(BUILTIN_PROVIDER_HASHES.items()):
        monkeypatch.setitem(
            BUILTIN_PROVIDER_HASHES,
            provider_id,
            {
                name: hashlib.sha256(
                    (BUILTIN_ROOT / provider_id / name).read_bytes()
                ).hexdigest()
                for name in files
            },
        )


def test_bilibili_ui_builds_segmented_ass_mkv_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    # The central integrity table is updated once after parallel MOD changes.
    # Keep this focused UI contract test runnable before that consolidation.
    _use_current_builtin_hashes(monkeypatch)

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication([])
    unexpected_message = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", unexpected_message)
    monkeypatch.setattr(QMessageBox, "information", unexpected_message)
    monkeypatch.setattr(QMessageBox, "warning", unexpected_message)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    context = Bootstrap(portable=True).initialize(start_background=False)
    panel = None
    captured = []
    try:
        panel = create_download_panel(context, site_family="bilibili")
        panel.timer.stop()
        assert panel.bilibili_workspace is not None
        assert panel.enabled.isChecked()
        assert panel.bilibili_workspace.enabled.isEnabled()
        panel.enabled.setChecked(False)
        app.processEvents()
        assert not panel.bilibili_workspace.enabled.isEnabled()
        assert "先啟用" in panel.bilibili_workspace.enabled.text()
        panel.enabled.setChecked(True)
        app.processEvents()
        assert panel.bilibili_workspace.enabled.isEnabled()
        panel.bilibili_workspace.enabled.setChecked(True)
        panel.bilibili_workspace.danmaku_enabled.setChecked(True)
        app.processEvents()
        assert context.discovery.is_enabled("bilibili-search")
        assert context.features.is_enabled("bilibili-danmaku")
        panel.urls.setPlainText(
            "https://www.bilibili.com/video/BVexample"
        )
        app.processEvents()
        assert "Bilibili 影片" in panel.url_classification.text()
        assert panel.add_download.isEnabled()
        assert panel.read_info.isEnabled()
        assert panel.expand_playlist.isEnabled()

        panel.urls.setPlainText("https://space.bilibili.com/12345/video")
        app.processEvents()
        assert "UP 主影片清單" in panel.url_classification.text()
        assert not panel.add_download.isEnabled()
        assert not panel.read_info.isEnabled()
        assert panel.expand_playlist.isEnabled()

        panel.urls.setPlainText(
            "https://www.bilibili.com/video/BVexample"
        )
        app.processEvents()
        panel.start_time.setText("10")
        panel.end_time.setText("20")
        panel.danmaku_xml.setChecked(True)
        panel.danmaku_ass.setChecked(True)
        panel.danmaku_mkv.setChecked(True)
        monkeypatch.setattr(
            context.download_queue,
            "add_batch",
            lambda requests: captured.extend(requests) or ("task",),
        )

        panel.add_batch()

        assert not unexpected_message.called, unexpected_message.call_args
        assert len(captured) == 1
        request = captured[0]
        assert request.start_time == 10.0
        assert request.end_time == 20.0
        assert request.timed_comment_mode == "ass"
        assert request.container_preset == "mkv"
        assert context.download_providers.matching_provider_id(request.url) == "bilibili"
    finally:
        if panel is not None:
            panel.close()
            panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
