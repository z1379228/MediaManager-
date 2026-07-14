"""Opt-in public-content analyze matrix for built-in download providers."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES  # noqa: E402
from core.downloads.subprocess_provider import (  # noqa: E402
    SubprocessDownloadProvider,
)


@dataclass(frozen=True, slots=True)
class SmokeCase:
    case_id: str
    provider_id: str
    url: str


DEFAULT_CASES = (
    SmokeCase(
        "youtube-public-video",
        "youtube",
        "https://www.youtube.com/watch?v=YE7VzlLtp-4",
    ),
    SmokeCase(
        "generic-vimeo-public-video",
        "generic-ytdlp",
        "https://player.vimeo.com/video/54469442",
    ),
    SmokeCase(
        "generic-dailymotion-public-video",
        "generic-ytdlp",
        "https://www.dailymotion.com/video/x5kesuj",
    ),
    SmokeCase(
        "generic-soundcloud-public-track",
        "generic-ytdlp",
        "https://soundcloud.com/ethmusic/lostin-powers-she-so-heavy",
    ),
    SmokeCase(
        "generic-tiktok-public-video",
        "generic-ytdlp",
        "https://www.tiktok.com/@patroxofficial/video/6742501081818877190",
    ),
    SmokeCase(
        "generic-twitch-public-clip",
        "generic-ytdlp",
        "https://clips.twitch.tv/FaintLightGullWholeWheat",
    ),
    SmokeCase(
        "generic-twitter-public-video",
        "generic-ytdlp",
        "https://twitter.com/BrooklynNets/status/1349794411333394432",
    ),
    SmokeCase(
        "bilibili-public-video",
        "bilibili",
        "https://www.bilibili.com/video/BV13x41117TL",
    ),
)


def analyze_case(case: SmokeCase, release_root: Path) -> dict[str, object]:
    tools = release_root.resolve() / "tools"
    deno = tools / "deno.exe"
    ffmpeg = tools / "ffmpeg.exe"
    if not deno.is_file() or not ffmpeg.is_file():
        raise FileNotFoundError("bundled Deno or FFmpeg is missing")
    if case.provider_id not in {"youtube", "generic-ytdlp", "bilibili"}:
        raise ValueError(f"unsupported smoke provider: {case.provider_id}")
    provider = SubprocessDownloadProvider(
        ROOT / "mod" / "builtin" / case.provider_id,
        application_root=ROOT,
        ffmpeg_location=str(ffmpeg),
        js_runtime=("deno", str(deno)),
        analyze_timeout=90.0,
        expected_hashes=BUILTIN_PROVIDER_HASHES[case.provider_id],
    )
    try:
        info = provider.analyze(case.url)
    finally:
        provider.close()
    media_id = str(info.get("id") or "")
    title = " ".join(str(info.get("title") or "").split())
    if not media_id or not title:
        raise RuntimeError("provider analyze result has no ID or title")
    return {
        "media_id": media_id[:100],
        "title": title[:300],
        "duration": info.get("duration"),
    }


def run_matrix(
    *,
    release_root: Path,
    report_path: Path,
    cases: tuple[SmokeCase, ...] = DEFAULT_CASES,
    analyzer: Callable[[SmokeCase, Path], dict[str, object]] = analyze_case,
) -> dict[str, object]:
    if not cases or len(cases) > 20:
        raise ValueError("smoke matrix case count is invalid")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("smoke matrix case IDs must be unique")
    results: list[dict[str, Any]] = []
    for case in cases:
        started = time.monotonic()
        row: dict[str, Any] = {**asdict(case), "status": "PASS"}
        try:
            row["observed"] = analyzer(case, release_root)
        except Exception as error:
            row["status"] = "FAIL"
            row["error"] = f"{type(error).__name__}: {error}"[:1000]
        row["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        results.append(row)
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": (
            "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL"
        ),
        "cases": results,
    }
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(report_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-root", type=Path, default=ROOT / "Version" / "1.9"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / ".work" / "smoke-reports" / "provider-matrix.json",
    )
    args = parser.parse_args()
    report = run_matrix(release_root=args.release_root, report_path=args.report)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
