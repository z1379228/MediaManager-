from __future__ import annotations

from pathlib import Path

from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryPreferencesV1
from core.downloads.subprocess_provider import SubprocessDownloadProvider


def chinese_item() -> DiscoveryItemV1:
    return DiscoveryItemV1.from_dict(
        {
            "video_id": "zh-test",
            "url": "https://www.youtube.com/watch?v=zh-test",
            "title": "範例歌曲",
            "artist": "範例歌手",
            "duration": 180,
            "language": "zh-TW",
            "category": "music",
            "thumbnail_url": "",
        }
    )


def test_builtin_mod_ipc_round_trips_utf8_on_windows_codepages(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    history = SubprocessDownloadProvider(
        root / "mod" / "builtin" / "youtube-history",
        application_root=root,
        history_state_path=tmp_path / "history.json",
    )
    history.record_history("search", "中文歌曲")
    assert history.recent_history()[0].query == "中文歌曲"

    recovery = SubprocessDownloadProvider(
        root / "mod" / "builtin" / "youtube-recovery",
        application_root=root,
    )
    assert recovery.recovery_plan(chinese_item()).primary_query == "範例歌曲"

    similar = SubprocessDownloadProvider(
        root / "mod" / "builtin" / "youtube-similar",
        application_root=root,
    )
    plan = similar.similar_plan(
        chinese_item(),
        HistoryPreferencesV1(0, 0, {}, {}, {}, {}),
    )
    assert plan.queries[0] == "範例歌手 music"

    history.close()
    recovery.close()
    similar.close()
