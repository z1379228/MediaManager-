"""MEGA public file adapter backed only by the official mega-get client."""

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


def _mega_get_path(request: dict[str, Any]) -> Path | None:
    tools = request.get("external_tools")
    raw_path = tools.get("mega-get") if isinstance(tools, dict) else None
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).resolve()
    if (
        not path.is_file()
        or path.name.casefold() not in {"mega-get", "mega-get.exe"}
    ):
        return None
    return path


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


def _file_snapshot(output: Path) -> dict[str, tuple[int, int]]:
    values: dict[str, tuple[int, int]] = {}
    try:
        entries = tuple(output.iterdir())
    except OSError:
        return values
    if len(entries) > 10_000:
        raise ValueError("output directory contains too many items")
    for item in entries:
        try:
            if item.is_file() and not item.is_symlink():
                stat = item.stat()
                values[item.name] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            continue
    return values


def _completed_file(
    output: Path,
    before: dict[str, tuple[int, int]],
) -> Path:
    candidates: list[Path] = []
    for item in output.iterdir():
        try:
            if item.is_symlink() or not item.is_file() or item.stat().st_size <= 0:
                continue
            stat = item.stat()
            if before.get(item.name) != (stat.st_size, stat.st_mtime_ns):
                resolved = item.resolve()
                if resolved.is_relative_to(output):
                    candidates.append(resolved)
        except OSError:
            continue
    if len(candidates) != 1:
        raise RuntimeError("MEGAcmd did not create exactly one verifiable output file")
    return candidates[0]


def download(request: dict[str, Any]) -> str:
    parsed = parse_share(request.get("url"))
    if parsed is None:
        raise ValueError("unsupported MEGA public share URL")
    resource_kind, _share_id = parsed
    if resource_kind != "file":
        raise ValueError("Development 9.2 recognizes MEGA folders but downloads files only")
    executable = _mega_get_path(request)
    if executable is None:
        raise RuntimeError("official MEGAcmd mega-get is not installed or not detected")
    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("output directory is unsafe")
    output_filename = _safe_output_filename(request.get("output_filename"))
    before = _file_snapshot(output)
    emit({"type": "progress", "title": "Preparing official MEGA download"})
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen(
        [str(executable), str(request["url"]), str(output)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    assert process.stdout is not None
    for line in process.stdout:
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
        raise RuntimeError(f"official MEGAcmd failed with exit code {returncode}")
    completed = _completed_file(output, before)
    if output_filename:
        target = (output / output_filename).resolve()
        if not target.is_relative_to(output) or target.exists():
            raise ValueError("requested output filename is already in use")
        completed.replace(target)
        completed = target
    category = classify_mega_filename(completed.name)
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
