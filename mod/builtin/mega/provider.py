"""MEGA public file/folder adapter backed only by the official mega-get client."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


PROVIDER_ID = "mega"
DISPLAY_NAME = "MEGA"
_SHARE = re.compile(r"/(file|folder)/([A-Za-z0-9_-]{6,64})/?")
_KEY = re.compile(r"[A-Za-z0-9_-]{16,128}")
_PROGRESS = re.compile(r"(?<!\d)(\d{1,3})(?:\.\d+)?%")
_MAX_TOOL_OUTPUT_CHARS = 4_000
_FILE_TYPES = {
    "video": frozenset({".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}),
    "archive": frozenset(
        {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".tgz"}
    ),
    "document": frozenset(
        {
            ".pdf",
            ".doc",
            ".docx",
            ".odt",
            ".txt",
            ".rtf",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".epub",
        }
    ),
    "audio": frozenset({".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus"}),
    "image": frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}),
}


def classify_mega_filename(value: object) -> str:
    """Classify only a disclosed filename; a MEGA share ID contains no type."""

    filename = Path(str(value or "")).name
    suffixes = [suffix.casefold() for suffix in Path(filename).suffixes]
    compound = "".join(suffixes[-2:])
    if compound in {".tar.gz", ".tar.bz2", ".tar.xz"}:
        return "archive"
    suffix = suffixes[-1] if suffixes else ""
    for category, extensions in _FILE_TYPES.items():
        if suffix in extensions:
            return category
    return "unknown"


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def parse_share(value: object) -> tuple[str, str] | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    host = (parsed.hostname or "").casefold()
    share = _SHARE.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or host not in {"mega.nz", "www.mega.nz"}
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or share is None
        or _KEY.fullmatch(parsed.fragment) is None
    ):
        return None
    return share.group(1), share.group(2)


def _official_tool_path(
    request: dict[str, Any], tool_name: str
) -> Path | None:
    tools = request.get("external_tools")
    raw_path = tools.get(tool_name) if isinstance(tools, dict) else None
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).resolve()
    allowed_names = {tool_name, f"{tool_name}.exe"}
    if os.name == "nt":
        allowed_names.add(f"{tool_name}.bat")
    if not path.is_file() or path.name.casefold() not in allowed_names:
        return None
    return path


def _mega_get_path(request: dict[str, Any]) -> Path | None:
    return _official_tool_path(request, "mega-get")


def _transfer_options(request: dict[str, Any]) -> tuple[int | None, int | None]:
    raw_options = request.get("provider_options")
    if raw_options is None:
        return None, None
    if not isinstance(raw_options, dict) or len(raw_options) > 16:
        raise ValueError("MEGA provider options are invalid")
    allowed = {"download_connections", "download_speed_limit_bps"}
    if any(not isinstance(key, str) or key not in allowed for key in raw_options):
        raise ValueError("MEGA provider options contain unsupported keys")

    def bounded_integer(key: str, minimum: int, maximum: int) -> int | None:
        raw_value = raw_options.get(key)
        if raw_value in {None, ""}:
            return None
        if not isinstance(raw_value, str) or not raw_value.isascii():
            raise ValueError(f"MEGA {key} is invalid")
        try:
            value = int(raw_value)
        except ValueError as error:
            raise ValueError(f"MEGA {key} is invalid") from error
        if not minimum <= value <= maximum:
            raise ValueError(f"MEGA {key} is outside the allowed range")
        return value

    return (
        bounded_integer("download_connections", 1, 6),
        bounded_integer("download_speed_limit_bps", 65_536, 1_073_741_824),
    )


def _hidden_process_options() -> tuple[object, int]:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW
    return startupinfo, creationflags


def _official_tool_command(
    executable: Path, arguments: list[str]
) -> tuple[list[str], dict[str, str] | None]:
    """Invoke official Windows batch clients without interpolating user data."""

    if executable.suffix.casefold() != ".bat":
        return [str(executable), *arguments], None
    if os.name != "nt":
        raise RuntimeError("MEGAcmd batch clients are supported only on Windows")
    system_root = Path(os.environ.get("SystemRoot", "")).resolve()
    command_processor = (system_root / "System32" / "cmd.exe").resolve()
    if (
        not system_root.is_dir()
        or not command_processor.is_file()
        or command_processor.name.casefold() != "cmd.exe"
        or not command_processor.is_relative_to(system_root)
    ):
        raise RuntimeError("trusted Windows command processor is unavailable")
    environment = os.environ.copy()
    environment["MM_MEGA_TOOL"] = str(executable)
    variables = []
    for index, argument in enumerate(arguments):
        if "\x00" in argument or "\r" in argument or "\n" in argument:
            raise ValueError("MEGAcmd argument is invalid")
        variable = f"MM_MEGA_ARG_{index}"
        environment[variable] = argument
        variables.append(f'"%{variable}%"')
    command_text = 'call "%MM_MEGA_TOOL%"'
    if variables:
        command_text += " " + " ".join(variables)
    return (
        [str(command_processor), "/d", "/s", "/c", command_text],
        environment,
    )


def _apply_transfer_options(request: dict[str, Any]) -> None:
    connections, speed_limit = _transfer_options(request)
    if connections is None and speed_limit is None:
        return
    speedlimit = _official_tool_path(request, "mega-speedlimit")
    if speedlimit is None:
        raise RuntimeError(
            "official MEGAcmd mega-speedlimit is required for custom transfer settings"
        )
    startupinfo, creationflags = _hidden_process_options()
    commands: list[list[str]] = []
    if connections is not None:
        commands.append(
            [str(speedlimit), "--download-connections", str(connections)]
        )
    if speed_limit is not None:
        commands.append([str(speedlimit), "-d", str(speed_limit)])
    for command in commands:
        command, environment = _official_tool_command(
            speedlimit, command[1:]
        )
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
            timeout=30,
            check=False,
            env=environment,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "official MEGAcmd rejected the requested transfer settings"
            )


def analyze(request: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_share(request.get("url"))
    if parsed is None:
        raise ValueError("unsupported MEGA public share URL")
    resource_kind, share_id = parsed
    is_file = resource_kind == "file"
    content_kind = (
        classify_mega_filename(request.get("output_filename"))
        if is_file
        else "folder"
    )
    return {
        "id": share_id,
        "title": f"MEGA 公開{'檔案' if is_file else '資料夾'} ({share_id[:8]})",
        "duration": None,
        "uploader": "MEGA",
        "webpage_url": "https://mega.nz/" + resource_kind + "/" + share_id,
        "thumbnail": "",
        "thumbnail_kind": (
            f"mega-{content_kind}"
            if is_file and content_kind != "unknown"
            else "mega-file" if is_file else "mega-folder"
        ),
        "resource_kind": "public-file" if is_file else "public-folder",
        "content_kind": content_kind,
        "dependency_available": _mega_get_path(request) is not None,
        "chapters": [],
        "description": "MEGA 公開分享；解密片段只在本機下載程序中使用。",
        "formats": [],
        "audio_languages": [],
        "subtitle_languages": [],
    }


def _safe_output_filename(value: object) -> str:
    filename = str(value or "")
    if filename and (
        Path(filename).name != filename
        or len(filename) > 180
        or filename[-1] in " ."
        or any(ord(character) < 32 for character in filename)
    ):
        raise ValueError("output filename is invalid")
    return filename


def _entry_snapshot(output: Path) -> dict[str, tuple[str, int, int]]:
    values: dict[str, tuple[str, int, int]] = {}
    try:
        entries = tuple(output.iterdir())
    except OSError:
        return values
    if len(entries) > 10_000:
        raise ValueError("output directory contains too many items")
    for item in entries:
        try:
            if not item.is_symlink() and (item.is_file() or item.is_dir()):
                stat = item.stat()
                kind = "file" if item.is_file() else "folder"
                values[item.name] = (kind, stat.st_size, stat.st_mtime_ns)
        except OSError:
            continue
    return values


def _verify_folder_tree(folder: Path) -> None:
    pending = [folder]
    visited = 0
    while pending:
        current = pending.pop()
        entries = tuple(current.iterdir())
        visited += len(entries)
        if visited > 10_000:
            raise ValueError("MEGA folder output exceeds the 10,000-entry limit")
        for entry in entries:
            if entry.is_symlink():
                raise ValueError("MEGA folder output contains a symbolic link")
            if entry.is_dir():
                pending.append(entry)
            elif not entry.is_file():
                raise ValueError("MEGA folder output contains an unsupported entry")


def _completed_entry(
    output: Path,
    before: dict[str, tuple[str, int, int]],
) -> Path:
    candidates: list[Path] = []
    for item in output.iterdir():
        try:
            if item.is_symlink() or not (item.is_file() or item.is_dir()):
                continue
            stat = item.stat()
            kind = "file" if item.is_file() else "folder"
            if item.is_file() and stat.st_size <= 0:
                continue
            if before.get(item.name) != (kind, stat.st_size, stat.st_mtime_ns):
                resolved = item.resolve()
                if resolved.is_relative_to(output):
                    if resolved.is_dir():
                        _verify_folder_tree(resolved)
                    candidates.append(resolved)
        except OSError:
            continue
    if len(candidates) != 1:
        raise RuntimeError("MEGAcmd did not create exactly one verifiable output entry")
    return candidates[0]


def download(request: dict[str, Any]) -> str:
    parsed = parse_share(request.get("url"))
    if parsed is None:
        raise ValueError("unsupported MEGA public share URL")
    resource_kind, _share_id = parsed
    executable = _mega_get_path(request)
    if executable is None:
        raise RuntimeError("official MEGAcmd mega-get is not installed or not detected")
    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("output directory is unsafe")
    output_filename = _safe_output_filename(request.get("output_filename"))
    if resource_kind == "folder" and output_filename:
        raise ValueError("MEGA folder downloads do not accept an output filename")
    before = _entry_snapshot(output)
    _apply_transfer_options(request)
    emit({"type": "progress", "title": "Preparing official MEGA download"})
    startupinfo, creationflags = _hidden_process_options()
    command, environment = _official_tool_command(
        executable, [str(request["url"]), str(output)]
    )
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        startupinfo=startupinfo,
        creationflags=creationflags,
        env=environment,
    )
    assert process.stdout is not None
    output_lines: list[str] = []
    output_size = 0
    for line in process.stdout:
        if output_size < _MAX_TOOL_OUTPUT_CHARS:
            retained = line.strip()[: _MAX_TOOL_OUTPUT_CHARS - output_size]
            if retained:
                output_lines.append(retained)
                output_size += len(retained)
        match = _PROGRESS.search(line[:1000])
        if match:
            percent = min(100, int(match.group(1)))
            emit(
                {
                    "type": "progress",
                    "title": "Downloading from MEGA",
                    "downloaded_bytes": percent,
                    "total_bytes": 100,
                    "speed": "",
                    "eta": "",
                }
            )
    returncode = process.wait()
    if returncode != 0:
        details = " ".join(output_lines)
        suffix = f": {details}" if details else ""
        raise RuntimeError(
            f"official MEGAcmd failed with exit code {returncode}{suffix}"
        )
    completed = _completed_entry(output, before)
    if output_filename:
        target = (output / output_filename).resolve()
        if not target.is_relative_to(output) or target.exists():
            raise ValueError("requested output filename is already in use")
        completed.replace(target)
        completed = target
    category = (
        "folder" if completed.is_dir() else classify_mega_filename(completed.name)
    )
    emit(
        {
            "type": "progress",
            "title": f"MEGA download completed ({category}): {completed.name}",
        }
    )
    return str(completed)


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "analyze":
            emit({"type": "result", "value": analyze(raw)})
        elif operation == "download":
            emit({"type": "result", "value": download(raw)})
        elif operation == "playlist":
            raise ValueError("MEGA MOD does not support playlists")
        else:
            raise ValueError("unsupported provider operation")
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
