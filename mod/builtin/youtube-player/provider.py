"""Bounded local video-preview MOD for YouTube search results."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class StderrLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def runtime_options(request: dict[str, Any]) -> dict[str, Any]:
    raw = request.get("js_runtime")
    if raw is None:
        return {}
    if (
        not isinstance(raw, dict)
        or set(raw) != {"name", "path"}
        or raw["name"] not in {"deno", "node", "quickjs"}
    ):
        raise ValueError("JavaScript runtime configuration is invalid")
    path = Path(str(raw["path"])).resolve()
    if not path.is_file():
        raise ValueError("JavaScript runtime executable is missing")
    return {"js_runtimes": {raw["name"]: {"path": str(path)}}}


def prepare_video_preview(request: dict[str, Any]) -> str:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    duration = float(request["duration"])
    preview_length = float(request.get("preview_length", 60))
    if not 0 < duration <= 86400 or not 0 < preview_length <= 120:
        raise ValueError("video preview duration is invalid")

    options: dict[str, Any] = {
        "format": (
            "bv*[height<=480][ext=mp4]+ba[ext=m4a]/"
            "b[height<=480][ext=mp4]/b[height<=480]"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(output / "preview.%(ext)s"),
        "noplaylist": True,
        "max_filesize": 80 * 1024 * 1024,
        "download_ranges": download_range_func(
            None, [(0, min(duration, preview_length))]
        ),
        "force_keyframes_at_cuts": True,
        "quiet": True,
        "noprogress": True,
        "logger": StderrLogger(),
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
    }
    options.update(runtime_options(request))
    if request.get("ffmpeg_location"):
        options["ffmpeg_location"] = request["ffmpeg_location"]
    emit({"type": "progress", "title": "Preparing video preview"})
    with YoutubeDL(options) as ydl:
        ydl.extract_info(request["url"], download=True)
    preview = output / "preview.mp4"
    if not preview.is_file() or preview.stat().st_size == 0:
        raise RuntimeError("video preview was not created")
    return str(preview)


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        if raw.get("operation") != "prepare_video_preview":
            raise ValueError("unsupported provider operation")
        emit({"type": "result", "value": prepare_video_preview(raw)})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
