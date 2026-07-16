from __future__ import annotations

import importlib.util
from io import StringIO
import os
from pathlib import Path
from types import SimpleNamespace

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


def test_folder_is_recognized_and_downloaded_as_verified_tree(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    url = "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop"
    assert provider.analyze({"url": url})["resource_kind"] == "public-folder"
    executable = tmp_path / "mega-get.exe"
    executable.write_bytes(b"test executable placeholder")
    output = tmp_path / "downloads"

    class Process:
        def __init__(self, arguments, **_kwargs):
            destination = Path(arguments[2])
            folder = destination / "shared-folder"
            folder.mkdir(parents=True)
            (folder / "episode.mp4").write_bytes(b"media")
            self.stdout = StringIO("100%\n")

        def wait(self):
            return 0

    monkeypatch.setattr(provider.subprocess, "Popen", Process)
    result = provider.download(
        {
            "url": url,
            "output_dir": str(output),
            "external_tools": {"mega-get": str(executable)},
        }
    )

    assert Path(result).is_dir()
    assert (Path(result) / "episode.mp4").read_bytes() == b"media"


def test_folder_rejects_file_rename(tmp_path: Path) -> None:
    provider = load_provider()
    executable = tmp_path / "mega-get.exe"
    executable.write_bytes(b"test executable placeholder")
    with pytest.raises(ValueError, match="do not accept"):
        provider.download(
            {
                "url": "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop",
                "output_dir": str(tmp_path / "downloads"),
                "output_filename": "renamed.zip",
                "external_tools": {"mega-get": str(executable)},
            }
        )


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


def test_download_applies_opt_in_official_transfer_settings(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    mega_get = tmp_path / "mega-get.exe"
    mega_speedlimit = tmp_path / "mega-speedlimit.exe"
    mega_get.write_bytes(b"test executable placeholder")
    mega_speedlimit.write_bytes(b"test executable placeholder")
    output = tmp_path / "downloads"
    settings_commands: list[list[str]] = []

    def run(arguments, **kwargs):
        settings_commands.append(arguments)
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 30
        return SimpleNamespace(returncode=0)

    class Process:
        def __init__(self, arguments, **_kwargs):
            destination = Path(arguments[2])
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "backup.zip").write_bytes(b"public data")
            self.stdout = StringIO("100%\n")

        def wait(self):
            return 0

    monkeypatch.setattr(provider.subprocess, "run", run)
    monkeypatch.setattr(provider.subprocess, "Popen", Process)
    provider.download(
        {
            "url": "https://mega.nz/file/AbCdEf12#abcdefghijklmnop",
            "output_dir": str(output),
            "external_tools": {
                "mega-get": str(mega_get),
                "mega-speedlimit": str(mega_speedlimit),
            },
            "provider_options": {
                "download_connections": "4",
                "download_speed_limit_bps": "10485760",
            },
        }
    )

    executable = str(mega_speedlimit.resolve())
    assert settings_commands == [
        [executable, "--download-connections", "4"],
        [executable, "-d", "10485760"],
    ]


def test_custom_transfer_settings_fail_closed_without_speedlimit(
    tmp_path: Path,
) -> None:
    provider = load_provider()
    mega_get = tmp_path / "mega-get.exe"
    mega_get.write_bytes(b"test executable placeholder")
    with pytest.raises(RuntimeError, match="mega-speedlimit"):
        provider.download(
            {
                "url": "https://mega.nz/file/AbCdEf12#abcdefghijklmnop",
                "output_dir": str(tmp_path / "downloads"),
                "external_tools": {"mega-get": str(mega_get)},
                "provider_options": {"download_connections": "4"},
            }
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows MEGAcmd uses batch clients")
def test_windows_official_batch_client_uses_bounded_environment_arguments(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    batch = tmp_path / "mega-get.bat"
    system_root = tmp_path / "Windows"
    command_processor = system_root / "System32" / "cmd.exe"
    batch.write_text("@echo off\n", encoding="utf-8")
    command_processor.parent.mkdir(parents=True)
    command_processor.write_bytes(b"test executable placeholder")
    monkeypatch.setenv("SystemRoot", str(system_root))

    command, environment = provider._official_tool_command(
        batch.resolve(),
        [
            "https://mega.nz/file/AbCdEf12#abcdefghijklmnop",
            str(tmp_path / "folder with spaces"),
        ],
    )

    assert command[:4] == [
        str(command_processor.resolve()),
        "/d",
        "/s",
        "/c",
    ]
    assert command[4] == (
        'call "%MM_MEGA_TOOL%" "%MM_MEGA_ARG_0%" "%MM_MEGA_ARG_1%"'
    )
    assert environment is not None
    assert environment["MM_MEGA_TOOL"] == str(batch.resolve())
    assert environment["MM_MEGA_ARG_1"].endswith("folder with spaces")


@pytest.mark.parametrize(
    "options",
    (
        {"download_connections": "0"},
        {"download_connections": "7"},
        {"download_speed_limit_bps": "not-a-number"},
        {"unexpected": "value"},
    ),
)
def test_transfer_settings_are_bounded(options: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="MEGA"):
        load_provider()._transfer_options({"provider_options": options})


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
