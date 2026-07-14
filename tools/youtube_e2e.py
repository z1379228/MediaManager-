"""Opt-in live YouTube MOD smoke test.

This diagnostic is intentionally excluded from pytest because it uses the public
internet. It searches for Blender Foundation's open movie, analyzes the first
result, downloads only a short segment, and validates it with bundled ffprobe.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES  # noqa: E402
from core.downloads.models import DownloadRequest  # noqa: E402
from core.downloads.subprocess_provider import (  # noqa: E402
    SubprocessDownloadProvider,
)


DEFAULT_QUERY = "Big Buck Bunny official Blender Foundation"


def _provider(provider_id: str, release_root: Path) -> SubprocessDownloadProvider:
    tools = release_root / "tools"
    arguments: dict[str, object] = {
        "application_root": ROOT,
        "expected_hashes": BUILTIN_PROVIDER_HASHES[provider_id],
        "analyze_timeout": 90.0,
    }
    if provider_id in {"youtube", "youtube-search", "youtube-player"}:
        arguments["js_runtime"] = ("deno", str(tools / "deno.exe"))
    if provider_id == "youtube":
        arguments.update(
            ffmpeg_location=str(tools / "ffmpeg.exe"),
            download_timeout=300.0,
            idle_timeout=90.0,
        )
    if provider_id == "youtube-player":
        arguments.update(
            ffmpeg_location=str(tools / "ffmpeg.exe"),
            download_timeout=300.0,
            idle_timeout=90.0,
            preview_root=ROOT / ".work" / "youtube-player-e2e",
        )
    return SubprocessDownloadProvider(
        ROOT / "mod" / "builtin" / provider_id,
        **arguments,
    )


def _validate_tools(release_root: Path) -> None:
    missing = [
        path
        for path in (
            release_root / "tools" / "deno.exe",
            release_root / "tools" / "ffmpeg.exe",
            release_root / "tools" / "ffprobe.exe",
        )
        if not path.is_file()
    ]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"bundled tools are missing: {names}")


def _probe(path: Path, ffprobe: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    result = json.loads(completed.stdout)
    duration = float(result.get("format", {}).get("duration", 0))
    streams = result.get("streams", [])
    if not 0 < duration <= 8:
        raise RuntimeError(f"unexpected segment duration: {duration:.3f}s")
    if not isinstance(streams, list) or not streams:
        raise RuntimeError("downloaded segment contains no media streams")
    return {"duration": round(duration, 3), "streams": streams}


def run(*, release_root: Path, work_root: Path, keep_output: bool) -> dict[str, object]:
    release_root = release_root.resolve()
    work_root = work_root.resolve()
    _validate_tools(release_root)
    if work_root == ROOT or not work_root.is_relative_to(ROOT / ".work"):
        raise ValueError("work directory must be inside the project .work directory")
    if work_root.exists():
        shutil.rmtree(work_root)
    output_dir = work_root / "output"
    output_dir.mkdir(parents=True)

    search_provider = _provider("youtube-search", release_root)
    download_provider = _provider("youtube", release_root)
    split_provider = _provider("youtube-auto-split", release_root)
    player_provider = _provider("youtube-player", release_root)
    progress_events: list[dict[str, object]] = []
    try:
        print("[1/6] Searching YouTube...", flush=True)
        search_results = search_provider.search(DEFAULT_QUERY, limit=3)
        if not search_results:
            raise RuntimeError("YouTube search returned no results")

        selected = search_results[0]
        print("[2/6] Analyzing the first search result...", flush=True)
        info = download_provider.analyze(selected.url)
        if info.get("id") != selected.video_id:
            raise RuntimeError("analyze returned an unexpected video id")

        print("[3/6] Planning metadata-based split candidates...", flush=True)
        chapters = info.get("chapters")
        split_plan = split_provider.split_plan(
            source_url=selected.url,
            source_title=str(info.get("title") or selected.title),
            duration=float(info.get("duration") or 0),
            chapters=chapters if isinstance(chapters, list) else [],
            description=str(info.get("description") or ""),
        )

        print("[4/6] Preparing a 3-second 480p video preview...", flush=True)
        preview_path = player_provider.prepare_video_preview(
            selected.url,
            duration=float(info.get("duration") or selected.duration or 3),
            preview_length=3,
        )
        preview_media = _probe(preview_path, release_root / "tools" / "ffprobe.exe")
        if not player_provider.cleanup_video_preview(preview_path):
            raise RuntimeError("video preview temporary session was not cleaned")

        print("[5/6] Downloading a 3-second segment...", flush=True)
        returned_path = Path(
            download_provider.download(
                DownloadRequest(
                    url=selected.url,
                    output_dir=output_dir,
                    start_time=0,
                    end_time=3,
                    format_preset="video-720",
                ),
                progress_events.append,
                threading.Event(),
            )
        ).resolve()
        files = tuple(path for path in output_dir.iterdir() if path.is_file())
        if len(files) != 1:
            raise RuntimeError(f"expected one output file, found {len(files)}")
        output_path = files[0].resolve()
        if not output_path.is_relative_to(output_dir) or output_path.stat().st_size == 0:
            raise RuntimeError("download output is unsafe or empty")

        print("[6/6] Validating media with bundled ffprobe...", flush=True)
        media = _probe(output_path, release_root / "tools" / "ffprobe.exe")
        report: dict[str, object] = {
            "status": "PASS",
            "search_results": len(search_results),
            "first_search_title": search_results[0].title,
            "selected_video_id": selected.video_id,
            "analyzed_title": info.get("title", ""),
            "split_composite_likely": split_plan.composite_likely,
            "split_segments": len(split_plan.segments),
            "split_warnings": list(split_plan.warnings),
            "provider_returned_path": str(returned_path),
            "output_name": output_path.name,
            "output_bytes": output_path.stat().st_size,
            "progress_events": len(progress_events),
            "video_preview": preview_media,
            **media,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return report
    finally:
        search_provider.close()
        download_provider.close()
        split_provider.close()
        player_provider.close()
        if not keep_output and work_root.exists():
            shutil.rmtree(work_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-root",
        type=Path,
        default=ROOT / "Version" / "1.2",
        help="Version folder containing bundled tools",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=ROOT / ".work" / "youtube-e2e",
        help="Temporary directory under .work",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep the downloaded test segment for manual inspection",
    )
    args = parser.parse_args()
    try:
        run(
            release_root=args.release_root,
            work_root=args.work_root,
            keep_output=args.keep_output,
        )
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
