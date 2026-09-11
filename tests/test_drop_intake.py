from __future__ import annotations

from pathlib import Path

import pytest

from core.drop_intake import MAX_DROP_ITEMS, prepare_drop_intake
from trusted_ui.conversion_panel import accepted_conversion_drop_sources


def test_drop_intake_separates_urls_batch_lists_and_local_media(
    tmp_path: Path,
) -> None:
    batch = tmp_path / "downloads.txt"
    batch.write_text("https://example.com/video\n", encoding="utf-8")
    media = tmp_path / "clip.MKV"
    media.write_bytes(b"media")

    result = prepare_drop_intake(
        text="https://example.com/one\nhttps://example.com/two\n",
        local_paths=(batch, media),
    )

    assert result.urls == (
        "https://example.com/one",
        "https://example.com/two",
    )
    assert result.batch_files == (batch.resolve(),)
    assert result.media_files == (media.resolve(),)
    assert result.issues == ()


def test_drop_intake_rejects_unsupported_missing_and_duplicate_local_files(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "unsafe.exe"
    executable.write_bytes(b"MZ")
    media = tmp_path / "song.mp3"
    media.write_bytes(b"audio")

    result = prepare_drop_intake(
        local_paths=(executable, tmp_path / "missing.mp4", media, media)
    )

    assert result.media_files == (media.resolve(),)
    assert len(result.issues) == 3
    assert {issue.reason for issue in result.issues} == {
        "unsupported local file type",
        "local file is missing or is not a regular file",
        "duplicate local file",
    }


def test_drop_intake_preserves_bounded_url_validation_issues() -> None:
    result = prepare_drop_intake(
        text="https://example.com/valid\nfile:///C:/Windows/win.ini\n"
    )

    assert result.urls == ("https://example.com/valid",)
    assert len(result.issues) == 1
    assert result.issues[0].reason == "URL must use HTTP or HTTPS and include a host"


def test_drop_intake_rejects_too_many_local_items(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="item limit"):
        prepare_drop_intake(
            local_paths=tuple(
                tmp_path / f"{index}.mp4" for index in range(MAX_DROP_ITEMS + 1)
            )
        )


def test_drop_intake_rejects_symlinked_media(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    link = tmp_path / "source-link.mp4"
    try:
        link.symlink_to(source)
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")

    result = prepare_drop_intake(local_paths=(link,))

    assert result.media_files == ()
    assert result.issues[0].reason == "symbolic links and junctions are not accepted"


def test_conversion_drop_accepts_media_only_and_never_starts_work(
    tmp_path: Path,
) -> None:
    media = tmp_path / "source.mkv"
    media.write_bytes(b"media")
    intake = prepare_drop_intake(local_paths=(media,))

    assert accepted_conversion_drop_sources(intake) == (media.resolve(),)

    with pytest.raises(ValueError, match="只接受本機媒體"):
        accepted_conversion_drop_sources(
            prepare_drop_intake(text="https://example.com/video")
        )
