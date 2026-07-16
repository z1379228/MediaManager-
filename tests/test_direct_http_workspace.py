from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.storage.paths import AppPaths
from trusted_ui.direct_http_workspace import create_direct_http_workspace


ROOT = Path(__file__).resolve().parents[1]


def _use_current_builtin_hashes(monkeypatch) -> None:
    for provider_id, files in tuple(BUILTIN_PROVIDER_HASHES.items()):
        monkeypatch.setitem(
            BUILTIN_PROVIDER_HASHES,
            provider_id,
            {
                name: hashlib.sha256(
                    (ROOT / "mod" / "builtin" / provider_id / name).read_bytes()
                ).hexdigest()
                for name in files
            },
        )


def test_direct_http_workspace_is_opt_in_and_builds_isolated_request(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    _use_current_builtin_hashes(monkeypatch)

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        QMessageBox,
        "question",
        Mock(return_value=QMessageBox.StandardButton.Yes),
    )
    context = Bootstrap(portable=True).initialize(start_background=False)
    panel = create_direct_http_workspace(context)
    panel.timer.stop()
    captured = []
    monkeypatch.setattr(
        context.download_queue,
        "add_batch",
        lambda requests: captured.extend(requests) or ("task",),
    )
    try:
        assert not context.download_providers.is_enabled("direct-http")
        assert not panel.add_download.isEnabled()
        panel.enabled.click()
        app.processEvents()
        assert context.download_providers.is_enabled("direct-http")

        panel.urls.setPlainText("https://downloads.example.org/release.zip")
        panel.output.setText(str(tmp_path / "downloads"))
        panel.expected_sha256.setText("a" * 64)
        app.processEvents()
        assert panel.add_download.isEnabled()
        panel.add_batch()

        assert len(captured) == 1
        request = captured[0]
        assert request.source_category == "direct-http"
        assert request.provider_options == (("expected_sha256", "a" * 64),)

        panel.urls.setPlainText("https://www.youtube.com/media/release.zip")
        app.processEvents()
        assert not panel.add_download.isEnabled()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        context.lifecycle.shutdown()
        app.processEvents()
