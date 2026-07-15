from __future__ import annotations

from pathlib import Path

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.models import DownloadRequest, DownloadState, DownloadTask
from core.storage.paths import AppPaths
from trusted_ui.download_panel import (
    ACTIVE_REFRESH_INTERVAL_MS,
    HIDDEN_REFRESH_INTERVAL_MS,
    IDLE_REFRESH_INTERVAL_MS,
    create_download_panel,
    download_refresh_interval,
    download_render_signature,
    safe_task_output_path,
    task_detail_summary,
)


def completed_task(output_dir: Path, output_path: Path) -> DownloadTask:
    return DownloadTask(
        "completed",
        DownloadRequest(
            "https://www.youtube.com/watch?v=example",
            output_dir,
            source_title="Example",
        ),
        state=DownloadState.COMPLETED,
        title="Example",
        progress=100.0,
        output_path=str(output_path),
    )


def test_download_render_signature_changes_only_for_visible_task_state(
    tmp_path: Path,
) -> None:
    task = DownloadTask(
        "queued",
        DownloadRequest("https://youtu.be/example", tmp_path),
        state=DownloadState.QUEUED,
        title="Example",
    )
    first = download_render_signature((task,))
    assert download_render_signature((task,)) == first
    task.progress = 25.0
    assert download_render_signature((task,)) != first
    second = download_render_signature((task,))
    task.cancel_event.set()
    assert download_render_signature((task,)) != second


def test_download_task_detail_reports_pending_pause_and_stop(tmp_path: Path) -> None:
    task = DownloadTask(
        "running",
        DownloadRequest("https://youtu.be/example", tmp_path),
        state=DownloadState.RUNNING,
        title="Example",
    )
    task.pause_requested.set()
    task.cancel_event.set()
    assert "正在暫停" in task_detail_summary(task)

    task.pause_requested.clear()
    assert "正在停止" in task_detail_summary(task)


def test_download_refresh_interval_adapts_to_visibility_and_queue_state(
    tmp_path: Path,
) -> None:
    task = DownloadTask(
        "queued",
        DownloadRequest("https://youtu.be/example", tmp_path),
        state=DownloadState.QUEUED,
    )
    assert (
        download_refresh_interval((task,), visible=True)
        == ACTIVE_REFRESH_INTERVAL_MS
    )
    task.state = DownloadState.COMPLETED
    assert (
        download_refresh_interval((task,), visible=True)
        == IDLE_REFRESH_INTERVAL_MS
    )
    assert (
        download_refresh_interval((task,), visible=False)
        == HIDDEN_REFRESH_INTERVAL_MS
    )


def test_download_panel_reuses_progress_widget_for_incremental_updates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    task = DownloadTask(
        "running",
        DownloadRequest("https://youtu.be/example", tmp_path),
        state=DownloadState.RUNNING,
        title="Example",
        progress=10.0,
    )
    monkeypatch.setattr(context.download_queue, "snapshots", lambda: (task,))
    panel = create_download_panel(context)
    panel.timer.stop()
    try:
        panel.render_signature = None
        panel.refresh()
        progress = panel.table.cellWidget(0, 2)
        task.progress = 42.5
        task.speed = "1.2 MiB/s"
        panel.refresh()

        assert panel.table.cellWidget(0, 2) is progress
        assert progress.value() == 425
        assert panel.table.item(0, 3).text() == "1.2 MiB/s"
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()


def test_safe_task_output_requires_confined_completed_regular_file(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    output = output_dir / "example.mp4"
    output.write_bytes(b"video")

    task = completed_task(output_dir, output)
    assert safe_task_output_path(task) == output.resolve()
    assert "輸出：" in task_detail_summary(task)

    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"outside")
    assert safe_task_output_path(completed_task(output_dir, outside)) is None

    output.unlink()
    assert safe_task_output_path(task) is None
    assert "已移動或目前不存在" in task_detail_summary(task)


def test_download_task_detail_exposes_failure_and_completed_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize()
    panel = create_download_panel(context)
    panel.timer.stop()
    failure = DownloadTask(
        "failed",
        DownloadRequest("https://www.youtube.com/watch?v=failed", tmp_path),
        state=DownloadState.FAILED,
        title="Failed video",
        error="network unavailable",
    )
    tasks = [failure]
    monkeypatch.setattr(
        context.download_queue,
        "snapshots",
        lambda: tuple(tasks),
    )
    try:
        panel.render_signature = None
        panel.refresh()
        panel.table.selectRow(0)
        app.processEvents()

        assert not panel.task_detail_card.isHidden()
        assert "失敗原因：network unavailable" in panel.task_detail_text.text()
        assert not panel.copy_error_button.isHidden()
        assert not panel.open_result_button.isEnabled()
        panel.copy_selected_error()
        assert QApplication.clipboard().text() == "network unavailable"

        output = tmp_path / "completed.mp4"
        output.write_bytes(b"video")
        tasks[:] = [completed_task(tmp_path, output)]
        panel.render_signature = None
        panel.refresh()
        panel.table.selectRow(0)
        app.processEvents()

        assert "輸出：" in panel.task_detail_text.text()
        assert panel.copy_error_button.isHidden()
        assert panel.open_result_button.isEnabled()
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        context.lifecycle.shutdown()
