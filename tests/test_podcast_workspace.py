from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from core.bootstrap.bootstrap import Bootstrap
from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES
from core.storage.paths import AppPaths
from trusted_ui.podcast_workspace import create_podcast_workspace


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


def test_podcast_workspace_previews_then_explicitly_hands_off(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    _use_current_builtin_hashes(monkeypatch)

    from PySide6.QtWidgets import QApplication

    feed_path = tmp_path / "show.rss"
    feed_path.write_text(
        """<rss version="2.0"><channel><title>範例節目</title>
        <item><title>可交接</title><enclosure
          url="https://cdn.example.org/audio/episode.mp3" type="audio/mpeg" />
        </item><item><title>僅預覽</title><enclosure
          url="https://cdn.example.org/play?id=2" type="audio/mpeg" />
        </item></channel></rss>""",
        encoding="utf-8",
    )
    app = QApplication.instance() or QApplication([])
    context = Bootstrap(portable=True).initialize(start_background=False)
    captured: list[tuple[tuple[str, ...], str]] = []
    panel = create_podcast_workspace(
        context,
        lambda urls, title: captured.append((urls, title)) or True,
    )
    try:
        assert context.features.is_enabled("podcast-import")
        assert context.download_queue.snapshots() == ()
        panel.source.setText(str(feed_path))
        panel.load_feed()
        app.processEvents()

        assert panel.table.rowCount() == 2
        assert "1 集可交給 Direct HTTP" in panel.summary.text()
        assert not captured

        panel.select_visible()
        assert panel.selected_urls() == (
            "https://cdn.example.org/audio/episode.mp3",
        )
        panel.handoff_selected()

        assert captured == [
            (("https://cdn.example.org/audio/episode.mp3",), "範例節目")
        ]
        assert context.download_queue.snapshots() == ()
        assert panel.selected_urls() == ()
    finally:
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        context.lifecycle.shutdown()
        app.processEvents()
