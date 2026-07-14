"""Safe filename planning for user-confirmed YouTube split drafts."""

from __future__ import annotations

import json
import math
import re
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SPACE = re.compile(r"\s+")
_EXTENSION = re.compile(r"[A-Za-z0-9]{1,8}")
_TIMESTAMP = re.compile(r"(?<!\d)(?:(\d{1,2}):)?([0-5]?\d):([0-5]\d)(?!\d)")
_TITLE_TRIM = " \t-–—|:：.[]()【】"
_SILENCE_START = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
_SILENCE_END = re.compile(
    r"silence_end:\s*([0-9]+(?:\.[0-9]+)?).*?silence_duration:\s*"
    r"([0-9]+(?:\.[0-9]+)?)"
)
_MAX_ANALYSIS_SECONDS = 7200.0
_MIN_SEGMENT_SECONDS = 15.0


def emit(message: dict[str, Any]) -> None:
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def safe_text(value: Any, fallback: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _SPACE.sub(" ", _UNSAFE.sub("_", text)).strip(" ._")
    return text or fallback


def timestamp(value: float) -> str:
    seconds = int(round(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}h{minutes:02d}m{seconds:02d}s"
    return f"{minutes:02d}m{seconds:02d}s"


def format_filename(request: dict[str, Any]) -> str:
    index = request.get("index")
    start = request.get("start")
    duration = request.get("duration")
    extension = str(request.get("extension") or "").lower()
    if not isinstance(index, int) or isinstance(index, bool) or not 1 <= index <= 999:
        raise ValueError("split index invalid")
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
        for value in (start, duration)
    ) or duration <= 0:
        raise ValueError("split time invalid")
    if not _EXTENSION.fullmatch(extension):
        raise ValueError("split extension invalid")
    source = safe_text(request.get("source_title"), "video")
    track = safe_text(request.get("track_title"), "unnamed")
    suffix = f"-{index:02d}-{track}-{timestamp(start)}-{timestamp(duration)}.{extension}"
    limit = 180
    available = max(1, limit - len(suffix))
    source = source[:available].rstrip(" ._") or "video"
    return f"{source}{suffix}"


def _finite_number(value: Any) -> float | None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        return None
    return float(value)


def _timestamp_seconds(match: re.Match[str]) -> float:
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    return float(hours * 3600 + minutes * 60 + seconds)


def _deduplicate_boundaries(
    values: list[tuple[float, str]], duration: float
) -> list[tuple[float, str]]:
    result: list[tuple[float, str]] = []
    for start, title in sorted(values, key=lambda item: item[0]):
        if not 0 <= start < duration:
            continue
        if result and start - result[-1][0] < 1:
            continue
        result.append((start, safe_text(title, f"Track {len(result) + 1}")[:200]))
        if len(result) >= 200:
            break
    return result


def _chapter_boundaries(
    chapters: Any, duration: float
) -> list[tuple[float, str]]:
    if not isinstance(chapters, list):
        return []
    values: list[tuple[float, str]] = []
    for chapter in chapters[:200]:
        if not isinstance(chapter, dict):
            continue
        start = _finite_number(chapter.get("start_time"))
        if start is None:
            continue
        values.append((start, str(chapter.get("title") or "")))
    return _deduplicate_boundaries(values, duration)


def _description_boundaries(
    description: Any, duration: float
) -> list[tuple[float, str]]:
    if not isinstance(description, str):
        return []
    values: list[tuple[float, str]] = []
    for line in description[:20_000].splitlines()[:1000]:
        match = _TIMESTAMP.search(line)
        if match is None:
            continue
        title = (line[: match.start()] + " " + line[match.end() :]).strip(
            _TITLE_TRIM
        )
        values.append((_timestamp_seconds(match), title))
    return _deduplicate_boundaries(values, duration)


def _segments(
    boundaries: list[tuple[float, str]],
    duration: float,
    *,
    source: str,
    confidence: float,
) -> list[dict[str, Any]]:
    if len(boundaries) < 2:
        return []
    values = list(boundaries)
    if values[0][0] > 0:
        values.insert(0, (0.0, "Intro"))
    result: list[dict[str, Any]] = []
    for index, (start, title) in enumerate(values, 1):
        end = values[index][0] if index < len(values) else duration
        if end - start < 1:
            continue
        result.append(
            {
                "index": len(result) + 1,
                "start": start,
                "end": end,
                "title": title,
                "evidence": [
                    {
                        "source": source,
                        "confidence": confidence,
                        "detail": (
                            "source chapter"
                            if source == "chapters"
                            else "description timestamp"
                        ),
                    }
                ],
            }
        )
    return result if len(result) >= 2 else []


def split_plan(request: dict[str, Any]) -> dict[str, Any]:
    source_url = request.get("source_url")
    source_title = request.get("source_title")
    duration = _finite_number(request.get("duration"))
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ValueError("split source URL invalid")
    if not isinstance(source_title, str) or not 1 <= len(source_title) <= 300:
        raise ValueError("split source title invalid")
    if duration is None or not 0 < duration <= 86400:
        raise ValueError("split source duration invalid")

    warnings: list[str] = []
    boundaries = _chapter_boundaries(request.get("chapters"), duration)
    source = "chapters"
    confidence = 0.98
    if len(boundaries) < 2:
        boundaries = _description_boundaries(request.get("description"), duration)
        source = "description"
        confidence = 0.82
        if len(boundaries) >= 2:
            warnings.append(
                "Description timestamps are unverified and require user confirmation."
            )
    segments = _segments(
        boundaries,
        duration,
        source=source,
        confidence=confidence,
    )
    if not segments:
        warnings.append("No reliable chapter or description split evidence was found.")
    return {
        "source_url": source_url,
        "source_title": source_title,
        "duration": duration,
        "composite_likely": len(segments) >= 2,
        "segments": segments,
        "warnings": warnings,
    }


def _silence_boundaries(stderr: str, duration: float) -> list[tuple[float, float]]:
    current_start: float | None = None
    values: list[tuple[float, float]] = []
    for line in stderr.splitlines():
        start_match = _SILENCE_START.search(line)
        if start_match is not None:
            current_start = float(start_match.group(1))
        end_match = _SILENCE_END.search(line)
        if end_match is None or current_start is None:
            continue
        end = float(end_match.group(1))
        silence_duration = float(end_match.group(2))
        boundary = (current_start + end) / 2
        if (
            silence_duration >= 0.5
            and boundary >= _MIN_SEGMENT_SECONDS
            and duration - boundary >= _MIN_SEGMENT_SECONDS
        ):
            values.append((boundary, silence_duration))
        current_start = None
    result: list[tuple[float, float]] = []
    for boundary, silence_duration in values:
        if result and boundary - result[-1][0] < _MIN_SEGMENT_SECONDS:
            if silence_duration > result[-1][1]:
                result[-1] = (boundary, silence_duration)
            continue
        result.append((boundary, silence_duration))
        if len(result) >= 199:
            break
    return result


def audio_split_plan(request: dict[str, Any]) -> dict[str, Any]:
    base = split_plan(
        {
            "source_url": request.get("source_url"),
            "source_title": request.get("source_title"),
            "duration": request.get("duration"),
            "chapters": [],
            "description": "",
        }
    )
    duration = float(base["duration"])
    input_path = Path(str(request.get("input_path") or "")).resolve()
    ffmpeg_path = Path(str(request.get("ffmpeg_location") or "")).resolve()
    if not input_path.is_file() or input_path.is_symlink():
        raise ValueError("audio analysis input is invalid")
    if not ffmpeg_path.is_file():
        raise ValueError("FFmpeg executable is missing")
    threshold_db = _finite_number(request.get("threshold_db"))
    min_silence = _finite_number(request.get("min_silence"))
    if threshold_db is None or not -80 <= threshold_db <= -10:
        raise ValueError("silence threshold is invalid")
    if min_silence is None or not 0.5 <= min_silence <= 10:
        raise ValueError("minimum silence duration is invalid")
    analysis_seconds = min(duration, _MAX_ANALYSIS_SECONDS)
    command = [
        str(ffmpeg_path),
        "-nostdin",
        "-hide_banner",
        "-v",
        "info",
        "-threads",
        "1",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        "8000",
        "-t",
        f"{analysis_seconds:.3f}",
        "-af",
        f"silencedetect=noise={threshold_db:.1f}dB:d={min_silence:.3f}",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"FFmpeg audio analysis failed: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip()[-500:]
        raise RuntimeError(f"FFmpeg audio analysis failed: {detail}")
    candidates = _silence_boundaries(completed.stderr, analysis_seconds)
    boundaries = [(0.0, "Track 01")]
    boundaries.extend(
        (boundary, f"Track {index:02d}")
        for index, (boundary, _silence_duration) in enumerate(candidates, 2)
    )
    segments = _segments(
        boundaries if candidates else [],
        analysis_seconds,
        source="silence",
        confidence=0.65,
    )
    warnings = [
        "Audio silence detection is heuristic and requires user confirmation."
    ]
    if duration > analysis_seconds:
        warnings.append("Audio analysis was limited to the first two hours.")
    if not segments:
        warnings.append("No usable sustained-silence boundary was found.")
    return {
        "source_url": base["source_url"],
        "source_title": base["source_title"],
        "duration": duration,
        "composite_likely": False,
        "segments": segments,
        "warnings": warnings,
    }


def main() -> int:
    try:
        raw = json.loads(sys.stdin.buffer.readline().decode("utf-8"))
        operation = raw.get("operation")
        if operation == "split_filename":
            value = format_filename(raw)
        elif operation == "split_plan":
            value = split_plan(raw)
        elif operation == "split_audio_plan":
            value = audio_split_plan(raw)
        else:
            raise ValueError("unsupported split operation")
        emit({"type": "result", "value": value})
        return 0
    except Exception as error:
        emit({"type": "error", "error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
