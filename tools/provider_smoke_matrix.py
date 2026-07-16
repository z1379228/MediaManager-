"""Opt-in public-content analyze matrix for built-in download providers."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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
        "https://www.tiktok.com/@barudakhb_/video/6984138651336838402",
    ),
    SmokeCase(
        "generic-twitch-public-clip",
        "generic-ytdlp",
        "https://clips.twitch.tv/FaintLightGullWholeWheat",
    ),
    SmokeCase(
        "bilibili-public-video",
        "bilibili",
        "https://www.bilibili.com/video/BV13x41117TL",
    ),
)

_TEMPORARY_ERROR_MARKERS = (
    "http error 408",
    "http error 425",
    "http error 429",
    "http error 500",
    "http error 502",
    "http error 503",
    "http error 504",
    "bad gateway",
    "connection reset",
    "connection timed out",
    "network is unreachable",
    "remote end closed",
    "service unavailable",
    "temporarily unavailable",
    "timed out",
)
_ACCESS_ERROR_MARKERS = (
    "age restricted",
    "authentication required",
    "confirm your age",
    "geo restricted",
    "login required",
    "members-only",
    "private video",
    "sign in",
    "this video is unavailable in your country",
)


def classify_smoke_failure(error: BaseException) -> str:
    """Classify live-state failures without converting them into a pass."""

    message = " ".join(f"{type(error).__name__}: {error}".casefold().split())
    if any(marker in message for marker in _TEMPORARY_ERROR_MARKERS):
        return "temporary-upstream"
    if any(marker in message for marker in _ACCESS_ERROR_MARKERS):
        return "access-restriction"
    if isinstance(error, (FileNotFoundError, RuntimeError, ValueError)):
        return "local-or-contract"
    return "unknown"


def analyze_case(case: SmokeCase, release_root: Path) -> dict[str, object]:
    tools = release_root.resolve() / "tools"
    deno = tools / "deno.exe"
    ffmpeg = tools / "ffmpeg.exe"
    if not deno.is_file() or not ffmpeg.is_file():
        raise FileNotFoundError("bundled Deno or FFmpeg is missing")
    if case.provider_id not in {"youtube", "generic-ytdlp", "bilibili"}:
        raise ValueError(f"unsupported smoke provider: {case.provider_id}")
    runtime_parent = ROOT / ".work" / "provider-smoke-runtime"
    runtime_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"{case.provider_id}-",
        dir=runtime_parent,
    ) as raw_runtime:
        provider = SubprocessDownloadProvider(
            release_root.resolve() / "mod" / "builtin" / case.provider_id,
            application_root=release_root.resolve(),
            ffmpeg_location=str(ffmpeg),
            js_runtime=("deno", str(deno)),
            analyze_timeout=90.0,
            expected_hashes=BUILTIN_PROVIDER_HASHES[case.provider_id],
            runtime_home=Path(raw_runtime),
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
    max_attempts: int = 2,
) -> dict[str, object]:
    if not cases or len(cases) > 20:
        raise ValueError("smoke matrix case count is invalid")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("smoke matrix case IDs must be unique")
    if not 1 <= max_attempts <= 3:
        raise ValueError("smoke matrix attempt count is invalid")
    results: list[dict[str, Any]] = []
    for case in cases:
        started = time.monotonic()
        row: dict[str, Any] = {
            **asdict(case),
            "status": "FAIL",
            "attempt_count": 0,
        }
        attempts: list[dict[str, object]] = []
        for attempt in range(1, max_attempts + 1):
            attempt_started = time.monotonic()
            row["attempt_count"] = attempt
            try:
                row["observed"] = analyzer(case, release_root)
                row["status"] = "PASS"
                attempts.append(
                    {
                        "attempt": attempt,
                        "status": "PASS",
                        "elapsed_ms": round(
                            (time.monotonic() - attempt_started) * 1000
                        ),
                    }
                )
                break
            except Exception as error:
                failure_class = classify_smoke_failure(error)
                error_text = f"{type(error).__name__}: {error}"[:1000]
                row["failure_class"] = failure_class
                row["error"] = error_text
                attempts.append(
                    {
                        "attempt": attempt,
                        "status": "FAIL",
                        "failure_class": failure_class,
                        "error": error_text,
                        "elapsed_ms": round(
                            (time.monotonic() - attempt_started) * 1000
                        ),
                    }
                )
                if failure_class != "temporary-upstream":
                    break
        row["attempts"] = attempts
        row["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        results.append(row)
    passed = sum(row["status"] == "PASS" for row in results)
    temporary = sum(
        row.get("failure_class") == "temporary-upstream"
        for row in results
        if row["status"] == "FAIL"
    )
    report: dict[str, object] = {
        "schema_version": 2,
        "mode": "live-public-content",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": (
            "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL"
        ),
        "summary": {
            "passed": passed,
            "failed": len(results) - passed,
            "temporary_upstream": temporary,
        },
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
    parser.add_argument("--attempts", type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args()
    report = run_matrix(
        release_root=args.release_root,
        report_path=args.report,
        max_attempts=args.attempts,
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
