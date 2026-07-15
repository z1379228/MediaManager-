from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path

import pytest


def load_provider():
    path = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "mega"
        / "provider.py"
    )
    spec = importlib.util.spec_from_file_location("mega_provider_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_identifies_file_and_redacts_share_key(tmp_path: Path) -> None:
    provider = load_provider()
    result = provider.analyze(
        {
            "url": "https://www.mega.nz/file/AbCdEf12#abcdefghijklmnop",
            "external_tools": {},
        }
    )

    assert result["resource_kind"] == "public-file"
    assert result["thumbnail_kind"] == "mega-file"
    assert result["dependency_available"] is False
    assert result["content_kind"] == "unknown"
    assert result["webpage_url"] == "https://mega.nz/file/AbCdEf12"
    assert "abcdefghijklmnop" not in str(result)


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("movie.mkv", "video"),
        ("backup.tar.gz", "archive"),
        ("manual.pdf", "document"),
        ("song.flac", "audio"),
        ("cover.webp", "image"),
        ("payload.bin", "unknown"),
    ),
)
def test_filename_classification_covers_non_video_files(
    filename: str, expected: str
) -> None:
    assert load_provider().classify_mega_filename(filename) == expected


def test_folder_is_recognized_but_download_fails_closed(tmp_path: Path) -> None:
    provider = load_provider()
    url = "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop"
    assert provider.analyze({"url": url})["resource_kind"] == "public-folder"
    with pytest.raises(ValueError, match="downloads files only"):
        provider.download({"url": url, "output_dir": str(tmp_path)})


def test_public_file_requires_explicit_official_mega_get(tmp_path: Path) -> None:
    provider = load_provider()
    with pytest.raises(RuntimeError, match="official MEGAcmd"):
        provider.download(
            {
                "url": "https://mega.nz/file/AbCdEf12#abcdefghijklmnop",
                "output_dir": str(tmp_path),
                "external_tools": {},
            }
        )


def test_download_routes_public_file_to_injected_mega_get(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    executable = tmp_path / "mega-get.exe"
    executable.write_bytes(b"test executable placeholder")
    output = tmp_path / "downloads"
    captured: list[list[str]] = []

    class Process:
        def __init__(self, arguments, **kwargs):
            captured.append(arguments)
            assert kwargs["shell"] is False
            destination = Path(arguments[2])
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "public.bin").write_bytes(b"public data")
            self.stdout = StringIO("10%\n100%\n")

        def wait(self):
            return 0

    monkeypatch.setattr(provider.subprocess, "Popen", Process)
    url = "https://mega.nz/file/AbCdEf12#abcdefghijklmnop"
    result = provider.download(
        {
            "url": url,
            "output_dir": str(output),
            "output_filename": "",
            "external_tools": {"mega-get": str(executable)},
        }
    )

    assert captured == [[str(executable.resolve()), url, str(output.resolve())]]
    assert Path(result).read_bytes() == b"public data"


@pytest.mark.parametrize(
    "value",
    (
        "https://mega.nz/file/AbCdEf12",
        "https://mega.nz/file/AbCdEf12?x=1#abcdefghijklmnop",
        "https://mega.nz.evil.test/file/AbCdEf12#abcdefghijklmnop",
        "https://user@mega.nz/file/AbCdEf12#abcdefghijklmnop",
    ),
)
def test_share_parser_rejects_unsafe_forms(value: str) -> None:
    assert load_provider().parse_share(value) is None
