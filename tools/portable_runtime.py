"""Pinned, verified portable runtime acquisition for Windows releases."""

from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from core.runtime_policy import (
    DENO_EXECUTABLE_SHA256,
    DENO_VERSION,
    FFMPEG_PORTABLE_SHA256,
    FFMPEG_VERSION,
)


@dataclass(frozen=True, slots=True)
class PortableRuntimeRelease:
    name: str
    version: str
    url: str
    archive_sha256: str
    executable_sha256: str


DENO_RELEASE = PortableRuntimeRelease(
    name="deno",
    version=DENO_VERSION,
    url=(
        "https://github.com/denoland/deno/releases/download/v2.9.2/"
        "deno-x86_64-pc-windows-msvc.zip"
    ),
    archive_sha256="5fe194d26ac5ef77fcc5288c2c438c7a0465f3b6180440ebf04092714bf2dcdf",
    executable_sha256=DENO_EXECUTABLE_SHA256,
)
FFMPEG_ARCHIVE_URL = (
    "https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/"
    "ffmpeg-8.1.2-essentials_build.zip"
)
FFMPEG_ARCHIVE_SHA256 = (
    "db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec"
)
MAX_ARCHIVE_BYTES = 150 * 1024 * 1024
MAX_EXECUTABLE_BYTES = 250 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_cache_directory(
    root: Path, release: PortableRuntimeRelease = DENO_RELEASE
) -> Path:
    return root.resolve() / ".tool-cache" / release.name / release.version


def cached_runtime_path(
    root: Path, release: PortableRuntimeRelease = DENO_RELEASE
) -> Path | None:
    executable = runtime_cache_directory(root, release) / f"{release.name}.exe"
    if (
        not executable.is_file()
        or executable.is_symlink()
        or hashlib.sha256(executable.read_bytes()).hexdigest()
        != release.executable_sha256
    ):
        return None
    return executable


def ffmpeg_cache_directory(root: Path) -> Path:
    return root.resolve() / ".tool-cache" / "ffmpeg" / FFMPEG_VERSION


def cached_ffmpeg_paths(root: Path) -> dict[str, Path] | None:
    cache = ffmpeg_cache_directory(root)
    paths = {name: cache / name for name in FFMPEG_PORTABLE_SHA256}
    for name, path in paths.items():
        if (
            not path.is_file()
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest()
            != FFMPEG_PORTABLE_SHA256[name]
        ):
            return None
    return paths


def extract_verified_archive(
    archive: bytes,
    target: Path,
    release: PortableRuntimeRelease = DENO_RELEASE,
) -> Path:
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("portable runtime archive is too large")
    if _sha256(archive) != release.archive_sha256:
        raise ValueError("portable runtime archive checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        files = [item for item in package.infolist() if not item.is_dir()]
        expected_name = f"{release.name}.exe"
        if len(files) != 1 or files[0].filename != expected_name:
            raise ValueError("portable runtime archive layout is invalid")
        if files[0].file_size > MAX_EXECUTABLE_BYTES:
            raise ValueError("portable runtime executable is too large")
        executable_data = package.read(files[0])
    if _sha256(executable_data) != release.executable_sha256:
        raise ValueError("portable runtime executable checksum mismatch")

    cache = runtime_cache_directory(target, release)
    temporary = cache.with_name(f".{cache.name}.staging")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    executable = temporary / expected_name
    executable.write_bytes(executable_data)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        shutil.rmtree(cache)
    temporary.replace(cache)
    return cache / expected_name


def extract_verified_ffmpeg_archive(archive: bytes, target: Path) -> dict[str, Path]:
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("FFmpeg archive is too large")
    if _sha256(archive) != FFMPEG_ARCHIVE_SHA256:
        raise ValueError("FFmpeg archive checksum mismatch")
    wanted_suffixes = {
        "ffmpeg.exe": "/bin/ffmpeg.exe",
        "ffprobe.exe": "/bin/ffprobe.exe",
        "FFMPEG-LICENSE.txt": "/LICENSE",
        "FFMPEG-README.txt": "/README.txt",
    }
    selected: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        for output_name, suffix in wanted_suffixes.items():
            matches = [
                item
                for item in package.infolist()
                if not item.is_dir() and f"/{item.filename}".endswith(suffix)
            ]
            if len(matches) != 1 or matches[0].file_size > MAX_EXECUTABLE_BYTES:
                raise ValueError(f"FFmpeg archive layout is invalid: {output_name}")
            selected[output_name] = package.read(matches[0])
    for name, data in selected.items():
        if _sha256(data) != FFMPEG_PORTABLE_SHA256[name]:
            raise ValueError(f"FFmpeg file checksum mismatch: {name}")

    cache = ffmpeg_cache_directory(target)
    temporary = cache.with_name(f".{cache.name}.staging")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    for name, data in selected.items():
        (temporary / name).write_bytes(data)
    if cache.exists():
        shutil.rmtree(cache)
    temporary.replace(cache)
    return {name: cache / name for name in selected}


def fetch_deno(root: Path) -> Path:
    cached = cached_runtime_path(root)
    if cached is not None:
        return cached
    with urllib.request.urlopen(DENO_RELEASE.url, timeout=60) as response:
        archive = response.read(MAX_ARCHIVE_BYTES + 1)
    executable = extract_verified_archive(archive, root)
    result = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
    )
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    if first_line != f"deno {DENO_RELEASE.version} (stable, release, x86_64-pc-windows-msvc)":
        executable.unlink(missing_ok=True)
        raise RuntimeError(f"unexpected Deno identity: {first_line}")
    return executable


def fetch_ffmpeg(root: Path) -> dict[str, Path]:
    cached = cached_ffmpeg_paths(root)
    if cached is not None:
        return cached
    archive_path = ffmpeg_cache_directory(root) / (
        f"ffmpeg-{FFMPEG_VERSION}-essentials_build.zip"
    )
    if archive_path.is_file():
        archive = archive_path.read_bytes()
    else:
        with urllib.request.urlopen(FFMPEG_ARCHIVE_URL, timeout=120) as response:
            archive = response.read(MAX_ARCHIVE_BYTES + 1)
    paths = extract_verified_ffmpeg_archive(archive, root)
    for executable_name in ("ffmpeg.exe", "ffprobe.exe"):
        result = subprocess.run(
            [str(paths[executable_name]), "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=True,
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        if f"version {FFMPEG_VERSION}-essentials_build-www.gyan.dev" not in first_line:
            raise RuntimeError(f"unexpected FFmpeg identity: {first_line}")
    return paths


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download pinned portable runtimes after SHA-256 verification."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(fetch_deno(args.root))
    for path in fetch_ffmpeg(args.root).values():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
