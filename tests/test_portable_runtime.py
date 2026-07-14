from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from tools import portable_runtime
from tools.portable_runtime import (
    PortableRuntimeRelease,
    cached_runtime_path,
    extract_verified_archive,
)


def _archive(name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        package.writestr(name, content)
    return output.getvalue()


def _release(archive: bytes, executable: bytes) -> PortableRuntimeRelease:
    return PortableRuntimeRelease(
        name="deno",
        version="test",
        url="https://example.invalid/deno.zip",
        archive_sha256=hashlib.sha256(archive).hexdigest(),
        executable_sha256=hashlib.sha256(executable).hexdigest(),
    )


def test_extract_verified_runtime_and_reuse_cache(tmp_path: Path) -> None:
    executable = b"verified-runtime"
    archive = _archive("deno.exe", executable)
    release = _release(archive, executable)

    result = extract_verified_archive(archive, tmp_path, release)

    assert result.read_bytes() == executable
    assert cached_runtime_path(tmp_path, release) == result


def test_extract_rejects_archive_checksum_mismatch(tmp_path: Path) -> None:
    executable = b"runtime"
    archive = _archive("deno.exe", executable)
    release = _release(archive, executable)

    with pytest.raises(ValueError, match="archive checksum"):
        extract_verified_archive(archive + b"tampered", tmp_path, release)


def test_extract_rejects_unexpected_archive_layout(tmp_path: Path) -> None:
    executable = b"runtime"
    archive = _archive("nested/deno.exe", executable)
    release = _release(archive, executable)

    with pytest.raises(ValueError, match="layout"):
        extract_verified_archive(archive, tmp_path, release)


def test_extract_verified_ffmpeg_files(tmp_path: Path, monkeypatch) -> None:
    files = {
        "root/bin/ffmpeg.exe": b"ffmpeg",
        "root/bin/ffprobe.exe": b"ffprobe",
        "root/LICENSE": b"license",
        "root/README.txt": b"readme",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        for name, content in files.items():
            package.writestr(name, content)
    archive = output.getvalue()
    expected = {
        "ffmpeg.exe": hashlib.sha256(files["root/bin/ffmpeg.exe"]).hexdigest(),
        "ffprobe.exe": hashlib.sha256(files["root/bin/ffprobe.exe"]).hexdigest(),
        "FFMPEG-LICENSE.txt": hashlib.sha256(files["root/LICENSE"]).hexdigest(),
        "FFMPEG-README.txt": hashlib.sha256(files["root/README.txt"]).hexdigest(),
    }
    monkeypatch.setattr(portable_runtime, "FFMPEG_ARCHIVE_SHA256", hashlib.sha256(archive).hexdigest())
    monkeypatch.setattr(portable_runtime, "FFMPEG_PORTABLE_SHA256", expected)

    paths = portable_runtime.extract_verified_ffmpeg_archive(archive, tmp_path)

    assert set(paths) == set(expected)
    assert paths["ffmpeg.exe"].read_bytes() == b"ffmpeg"
    assert portable_runtime.cached_ffmpeg_paths(tmp_path) == paths


def test_extract_ffmpeg_rejects_archive_checksum(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="archive checksum"):
        portable_runtime.extract_verified_ffmpeg_archive(b"invalid", tmp_path)
