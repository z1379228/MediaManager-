from pathlib import Path
from types import SimpleNamespace

import pytest

from core.downloads.models import DownloadRequest
from core.downloads.preflight import preflight_download_batch


def test_download_preflight_reports_unique_outputs_and_free_space(tmp_path: Path) -> None:
    requests = [
        DownloadRequest("https://example.com/a", tmp_path / "new"),
        DownloadRequest("https://example.com/b", tmp_path / "new"),
    ]
    report = preflight_download_batch(requests, minimum_free_bytes=0)
    assert report.output_directories == ((tmp_path / "new").resolve(),)
    assert report.lowest_free_bytes >= 0


def test_download_preflight_rejects_insufficient_space(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "core.downloads.preflight.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=100, used=90, free=10),
    )
    request = DownloadRequest("https://example.com/a", tmp_path)
    with pytest.raises(RuntimeError, match="磁碟空間不足"):
        preflight_download_batch((request,), minimum_free_bytes=20)


def test_download_preflight_reserves_estimated_output_and_safety_space(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "core.downloads.preflight.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=1000, used=500, free=500),
    )
    request = DownloadRequest("https://example.com/a", tmp_path)

    report = preflight_download_batch(
        (request,), minimum_free_bytes=100, estimated_bytes=350
    )
    assert report.required_free_bytes == 450
    assert report.estimated_bytes == 350
    with pytest.raises(RuntimeError, match="磁碟空間不足"):
        preflight_download_batch(
            (request,), minimum_free_bytes=200, estimated_bytes=350
        )


def test_download_preflight_refuses_existing_named_output(tmp_path: Path) -> None:
    (tmp_path / "result.mp4").write_bytes(b"existing")
    request = DownloadRequest(
        "https://example.com/a", tmp_path, output_filename="result.mp4"
    )

    with pytest.raises(FileExistsError, match="不會覆蓋"):
        preflight_download_batch((request,), minimum_free_bytes=0)
