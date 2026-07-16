from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from contracts.discovery_v1 import DiscoveryItemV1
from trusted_ui.ani_gamer_history import (
    MAX_HISTORY_ENTRIES,
    clear_history,
    export_history,
    load_history,
    record_history,
)


def item(video_id: str, url: str, title: str) -> DiscoveryItemV1:
    return DiscoveryItemV1(
        video_id,
        url,
        title,
        "",
        None,
        "zh-TW",
        "anime",
        "",
    )


SERIES = item(
    "114096",
    "https://ani.gamer.com.tw/animeRef.php?sn=114096",
    "Series",
)
EPISODE = item(
    "ani-episode-49944",
    "https://ani.gamer.com.tw/animeVideo.php?sn=49944",
    "Series [Episode 1]",
)


def test_history_is_newest_first_deduplicated_and_bounded(tmp_path: Path) -> None:
    path = tmp_path / "data" / "ani-gamer-history.json"
    timestamp = datetime(2026, 7, 16, tzinfo=timezone.utc)

    first = record_history(path, SERIES, EPISODE, opened_at=timestamp)
    assert len(first) == 1
    assert first[0].episode_id == EPISODE.video_id
    assert load_history(path) == first

    second_episode = item(
        "ani-episode-49945",
        "https://ani.gamer.com.tw/animeVideo.php?sn=49945",
        "Series [Episode 2]",
    )
    updated = record_history(path, SERIES, second_episode, opened_at=timestamp)
    assert [entry.episode_id for entry in updated] == [
        second_episode.video_id,
        EPISODE.video_id,
    ]
    again = record_history(path, SERIES, EPISODE, opened_at=timestamp)
    assert [entry.episode_id for entry in again] == [
        EPISODE.video_id,
        second_episode.video_id,
    ]

    for serial in range(50000, 50000 + MAX_HISTORY_ENTRIES + 5):
        episode = item(
            f"ani-episode-{serial}",
            f"https://ani.gamer.com.tw/animeVideo.php?sn={serial}",
            f"Series [{serial}]",
        )
        record_history(path, SERIES, episode, opened_at=timestamp)
    entries = load_history(path)
    assert len(entries) == MAX_HISTORY_ENTRIES
    assert entries[0].episode_id.endswith("50104")


def test_history_ignores_invalid_records_and_rejects_cross_site_items(
    tmp_path: Path,
) -> None:
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "kind": "ani-gamer-local-history",
                "entries": [
                    {"episode_id": "bad", "url": "https://example.invalid"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert load_history(path) == ()

    wrong_series = item("x", "https://www.youtube.com/watch?v=x", "Wrong")
    with pytest.raises(ValueError, match="history item URL"):
        record_history(path, wrong_series, EPISODE)


def test_history_can_be_cleared_or_exported_without_media_side_effects(
    tmp_path: Path,
) -> None:
    path = tmp_path / "data" / "ani-gamer-history.json"
    exported = tmp_path / "exports" / "history.json"
    record_history(path, SERIES, EPISODE)

    export_history(path, exported)
    assert load_history(exported)[0].episode_id == EPISODE.video_id

    clear_history(path)
    assert load_history(path) == ()
    assert exported.is_file()
