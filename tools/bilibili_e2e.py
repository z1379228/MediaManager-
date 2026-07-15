"""Opt-in live Bilibili search, metadata and short-download smoke test.

The diagnostic uses only public Bilibili routes. It never supplies cookies,
solves verification challenges, or bypasses login, region, payment or DRM.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES  # noqa: E402
from core.downloads.models import DownloadRequest  # noqa: E402
from core.downloads.subprocess_provider import (  # noqa: E402
    SubprocessDownloadProvider,
)


DEFAULT_QUERY = "Blender 動畫"


def _provider(
    provider_id: str,
    release_root: Path,
    work_root: Path,
) -> SubprocessDownloadProvider:
    tools = release_root / "tools"
    arguments: dict[str, object] = {
        "application_root": ROOT,
        "expected_hashes": BUILTIN_PROVIDER_HASHES[provider_id],
        "analyze_timeout": 90.0,
        "runtime_home": work_root / "runtime" / provider_id,
    }
    if provider_id == "bilibili":
        arguments.update(
            ffmpeg_location=str(tools / "ffmpeg.exe"),
            js_runtime=("deno", str(tools / "deno.exe")),
            download_timeout=300.0,
            idle_timeout=90.0,
        )
    return SubprocessDownloadProvider(
        ROOT / "mod" / "builtin" / provider_id,
        **arguments,
    )


def _official_thumbnail(url: str) -> bool:
    if not url:
        return True
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    host = (parsed.hostname or "").casefold()
    return (
        parsed.scheme == "https"
        and host.endswith(".hdslb.com")
        and parsed.username is None
        and parsed.password is None
        and port is None
    )


def _probe(
    path: Path,
    ffprobe: Path,
    *,
    maximum_duration: float = 8.0,
) -> dict[str, object]:
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
    if not 0 < duration <= maximum_duration:
        raise RuntimeError(f"unexpected segment duration: {duration:.3f}s")
    if not isinstance(streams, list) or not streams:
        raise RuntimeError("downloaded segment contains no media streams")
    return {"duration": round(duration, 3), "streams": streams}


def run(
    *,
    release_root: Path,
    work_root: Path,
    query: str,
    url: str,
    creator_url: str,
    expect_parts: bool,
    danmaku: bool,
    keep_output: bool,
) -> dict[str, object]:
    release_root = release_root.resolve()
    work_root = work_root.resolve()
    required = tuple(
        release_root / "tools" / name
        for name in ("deno.exe", "ffmpeg.exe", "ffprobe.exe")
    )
    missing = tuple(path.name for path in required if not path.is_file())
    if missing:
        raise FileNotFoundError(f"bundled tools are missing: {', '.join(missing)}")
    if work_root == ROOT or not work_root.is_relative_to(ROOT / ".work"):
        raise ValueError("work directory must be inside the project .work directory")
    if work_root.exists():
        shutil.rmtree(work_root)
    output_dir = work_root / "output"
    output_dir.mkdir(parents=True)

    search_provider = _provider("bilibili-search", release_root, work_root)
    download_provider = _provider("bilibili", release_root, work_root)
    progress_events: list[dict[str, object]] = []
    creator_report: dict[str, object] = {}
    try:
        if creator_url:
            creator_entries = download_provider.playlist(creator_url, limit=5)
            available_creator_entries = tuple(
                entry for entry in creator_entries if entry.available
            )
            if not available_creator_entries:
                raise RuntimeError("Bilibili creator page has no available entries")
            creator_report = {
                "creator_entries": len(creator_entries),
                "creator_first_title": available_creator_entries[0].title,
            }

        results = ()
        if url:
            print("[1/4] Using the supplied public Bilibili URL...", flush=True)
            selected = SimpleNamespace(
                url=url,
                video_id=url.rstrip("/").rsplit("/", 1)[-1],
                artist="",
            )
        else:
            print("[1/4] Searching Bilibili official catalogue...", flush=True)
            results = search_provider.search(query, limit=5, content_type="video")
            if not results:
                raise RuntimeError("Bilibili search returned no results")
            if any(not _official_thumbnail(item.thumbnail_url) for item in results):
                raise RuntimeError("Bilibili search returned a non-official thumbnail")
            selected = results[0]

        print("[2/4] Reading public video metadata...", flush=True)
        info = download_provider.analyze(selected.url)
        if not info.get("id") or not info.get("title"):
            raise RuntimeError("Bilibili analyze returned incomplete metadata")

        parts = ()
        download_url = selected.url
        if expect_parts or int(info.get("part_count") or 0) > 1:
            parts = download_provider.playlist(selected.url, limit=20)
            available_parts = tuple(part for part in parts if part.available)
            if not available_parts:
                raise RuntimeError("Bilibili multipart video has no available parts")
            if expect_parts and len(parts) < 2:
                raise RuntimeError("expected a multipart Bilibili list")
            if any(not part.title.strip() for part in parts):
                raise RuntimeError("Bilibili multipart list contains an empty title")
            download_url = available_parts[0].url

        print("[3/4] Downloading a 3-second public segment...", flush=True)
        returned_path = Path(
            download_provider.download(
                DownloadRequest(
                    url=download_url,
                    output_dir=output_dir,
                    start_time=10 if danmaku else 0,
                    end_time=18 if danmaku else 3,
                    format_preset="video-480",
                    timed_comment_mode="ass" if danmaku else "none",
                    container_preset="mkv" if danmaku else "auto",
                ),
                progress_events.append,
                threading.Event(),
            )
        ).resolve()
        files = tuple(path.resolve() for path in output_dir.iterdir() if path.is_file())
        output = returned_path
        if not output.is_relative_to(output_dir) or output.stat().st_size == 0:
            raise RuntimeError("download output is unsafe or empty")
        if danmaku:
            xml_files = tuple(path for path in files if path.suffix.casefold() == ".xml")
            ass_files = tuple(path for path in files if path.suffix.casefold() == ".ass")
            if output.suffix.casefold() != ".mkv" or not xml_files or not ass_files:
                raise RuntimeError("Bilibili danmaku XML/ASS/MKV output is incomplete")

        print("[4/4] Validating media with bundled ffprobe...", flush=True)
        media = _probe(
            output,
            release_root / "tools" / "ffprobe.exe",
            maximum_duration=8.5 if danmaku else 8.0,
        )
        if danmaku and not any(
            stream.get("codec_type") == "subtitle" for stream in media["streams"]
        ):
            raise RuntimeError("Bilibili MKV contains no ASS subtitle stream")
        report: dict[str, object] = {
            "status": "PASS",
            "search_results": len(results),
            "search_thumbnails": sum(bool(item.thumbnail_url) for item in results),
            "selected_video_id": selected.video_id,
            "selected_uploader": selected.artist,
            "analyzed_title": info.get("title", ""),
            "content_kind": info.get("content_kind", ""),
            "part_count": info.get("part_count", 0),
            "expanded_parts": len(parts),
            "first_part_title": parts[0].title if parts else "",
            "provider_returned_path": str(returned_path),
            "output_name": output.name,
            "output_bytes": output.stat().st_size,
            "progress_events": len(progress_events),
            "danmaku_files": [path.name for path in files if path != output],
            **creator_report,
            **media,
        }
        print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)
        return report
    finally:
        search_provider.close()
        download_provider.close()
        if not keep_output and work_root.exists():
            shutil.rmtree(work_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-root",
        type=Path,
        default=ROOT / "Version" / "Development" / "10.3",
        help="Development version folder containing bundled tools",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=ROOT / ".work" / "bilibili-e2e",
        help="Temporary directory under .work",
    )
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument(
        "--url",
        default="",
        help="Skip search and validate one public Bilibili video URL",
    )
    parser.add_argument(
        "--expect-parts",
        action="store_true",
        help="Require the supplied URL to expand into at least two named parts",
    )
    parser.add_argument(
        "--creator-url",
        default="",
        help="Also expand the first five entries from one public UP creator page",
    )
    parser.add_argument(
        "--danmaku",
        action="store_true",
        help="Require XML, converted ASS and an MKV subtitle stream",
    )
    parser.add_argument("--keep-output", action="store_true")
    args = parser.parse_args()
    try:
        run(
            release_root=args.release_root,
            work_root=args.work_root,
            query=args.query,
            url=args.url,
            creator_url=args.creator_url,
            expect_parts=args.expect_parts,
            danmaku=args.danmaku,
            keep_output=args.keep_output,
        )
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
