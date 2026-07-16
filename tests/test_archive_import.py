from __future__ import annotations

import json
from pathlib import Path
import stat
from zipfile import ZipFile, ZipInfo

import pytest

from core.archive_import import extract_media_archive, preview_media_archive


MEDIA_SUFFIXES = frozenset({".jpg", ".png", ".mp4"})


def test_official_export_preview_and_extract_only_media(tmp_path: Path) -> None:
    archive = tmp_path / "official-export.zip"
    with ZipFile(archive, "w") as target:
        target.writestr("media/photo.jpg", b"photo")
        target.writestr("media/video.mp4", b"video")
        target.writestr("account/profile.json", b'{"name":"local"}')

    preview = preview_media_archive(
        archive, allowed_media_suffixes=MEDIA_SUFFIXES
    )
    destination = tmp_path / "library"
    extracted = extract_media_archive(
        archive, destination, allowed_media_suffixes=MEDIA_SUFFIXES
    )

    assert [entry.name for entry in preview.media_entries] == [
        "media/photo.jpg",
        "media/video.mp4",
    ]
    assert preview.metadata_count == 1
    assert [path.relative_to(destination).as_posix() for path in extracted] == [
        "media/photo.jpg",
        "media/video.mp4",
    ]
    assert not (destination / "account" / "profile.json").exists()
    index = json.loads(
        (destination / "media-index.json").read_text(encoding="utf-8")
    )
    assert index["schema"] == 1
    assert [item["path"] for item in index["media"]] == [
        "media/photo.jpg",
        "media/video.mp4",
    ]


@pytest.mark.parametrize("name", ("../outside.jpg", "/absolute.jpg"))
def test_official_export_rejects_unsafe_member_paths(
    tmp_path: Path, name: str
) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as target:
        target.writestr(name, b"data")

    with pytest.raises(ValueError, match="path"):
        preview_media_archive(archive, allowed_media_suffixes=MEDIA_SUFFIXES)


def test_official_export_rejects_symbolic_links(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.zip"
    link = ZipInfo("media/link.jpg")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive, "w") as target:
        target.writestr(link, "target.jpg")

    with pytest.raises(ValueError, match="symbolic"):
        preview_media_archive(archive, allowed_media_suffixes=MEDIA_SUFFIXES)


def test_official_export_rolls_back_created_media_on_collision(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "collision.zip"
    with ZipFile(archive, "w") as target:
        target.writestr("a.jpg", b"new-a")
        target.writestr("z.jpg", b"new-z")
    destination = tmp_path / "library"
    destination.mkdir()
    (destination / "z.jpg").write_bytes(b"existing")

    with pytest.raises(ValueError, match="already in use"):
        extract_media_archive(
            archive, destination, allowed_media_suffixes=MEDIA_SUFFIXES
        )

    assert not (destination / "a.jpg").exists()
    assert (destination / "z.jpg").read_bytes() == b"existing"
    assert not (destination / "media-index.json").exists()
