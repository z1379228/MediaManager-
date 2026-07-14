from pathlib import Path

import pytest

from core.storage.atomic import commit_file_without_overwrite


def test_commit_file_refuses_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "source.part"
    target = tmp_path / "target.bin"
    source.write_bytes(b"new")
    target.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        commit_file_without_overwrite(source, target)
    assert source.read_bytes() == b"new"
    assert target.read_bytes() == b"old"


def test_commit_file_exposes_complete_source(tmp_path: Path) -> None:
    source = tmp_path / "source.part"
    target = tmp_path / "target.bin"
    source.write_bytes(b"complete")
    commit_file_without_overwrite(source, target)
    assert not source.exists()
    assert target.read_bytes() == b"complete"
