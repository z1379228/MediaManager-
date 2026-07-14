from __future__ import annotations

from pathlib import Path

import pytest

from contracts.media_options_v1 import MediaOptionsContractError
from core.downloads.archive import DownloadArchive
from core.downloads.models import DownloadRequest


def test_media_presets_and_selected_subtitle_languages_are_valid(
    tmp_path: Path,
) -> None:
    request = DownloadRequest(
        "https://youtu.be/abc12345",
        tmp_path,
        format_preset="video-720",
        subtitle_mode="selected",
        subtitle_languages=("zh-TW", "en"),
    )
    assert request.format_preset == "video-720"


@pytest.mark.parametrize(
    ("preset", "mode", "languages"),
    [
        ("video-8k", "none", ()),
        ("best", "selected", ()),
        ("best", "all", ("en",)),
        ("best", "selected", ("bad language",)),
    ],
)
def test_invalid_media_options_are_rejected(
    tmp_path: Path,
    preset: str,
    mode: str,
    languages: tuple[str, ...],
) -> None:
    with pytest.raises(MediaOptionsContractError):
        DownloadRequest(
            "https://youtu.be/abc12345",
            tmp_path,
            format_preset=preset,
            subtitle_mode=mode,
            subtitle_languages=languages,
        )


def test_default_archive_identity_stays_backward_compatible(
    tmp_path: Path,
) -> None:
    default = DownloadRequest("https://youtu.be/abc12345", tmp_path)
    explicit = DownloadRequest(
        "https://youtu.be/abc12345",
        tmp_path,
        format_preset="video-720",
    )
    assert DownloadArchive.request_key(default) != DownloadArchive.request_key(
        explicit
    )


def test_timed_comment_and_container_options_are_explicit_and_distinct(
    tmp_path: Path,
) -> None:
    source = DownloadRequest(
        "https://www.bilibili.com/video/BVexample",
        tmp_path,
        timed_comment_mode="source",
    )
    embedded = DownloadRequest(
        "https://www.bilibili.com/video/BVexample",
        tmp_path,
        timed_comment_mode="ass",
        container_preset="mkv",
    )

    assert source.timed_comment_mode == "source"
    assert embedded.container_preset == "mkv"
    assert DownloadArchive.request_key(source) != DownloadArchive.request_key(
        embedded
    )


@pytest.mark.parametrize(
    ("comment_mode", "container", "format_preset"),
    (
        ("invalid", "auto", "best"),
        ("none", "mkv", "best"),
        ("source", "invalid", "best"),
        ("ass", "auto", "audio-m4a"),
    ),
)
def test_invalid_timed_comment_options_are_rejected(
    tmp_path: Path,
    comment_mode: str,
    container: str,
    format_preset: str,
) -> None:
    with pytest.raises(MediaOptionsContractError):
        DownloadRequest(
            "https://www.bilibili.com/video/BVexample",
            tmp_path,
            format_preset=format_preset,
            timed_comment_mode=comment_mode,
            container_preset=container,
        )
