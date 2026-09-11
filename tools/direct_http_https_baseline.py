"""Run one bounded Direct HTTP download against the W3C HTML5 test asset.

The command is a dry run unless ``--execute`` is supplied. Execution is
restricted to the exact HTTPS media URL used by the W3C HTML5 media-events
test page. The real built-in provider keeps its production URL, redirect,
DNS, filename and output-path validation; this tool only tightens the maximum
payload to 8 MiB. The transient output is hashed, reported, and removed.

This is deliberately a one-request integration smoke, not a public-host load
test and not evidence of representative network throughput.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import hashlib
import math
from pathlib import Path
import platform
import time
from types import ModuleType
from typing import Any

from core.version import CORE_VERSION
from tools import g39_baseline
from tools.direct_http_io_baseline import _load_provider
from tools.source_fingerprint import source_fingerprint, source_revision
from tools.startup_baseline import write_report


_SCHEMA_VERSION = 1
_WORKLOAD_ID = "direct-http-w3c-html5-video-smoke-v1"
_SAMPLE_URL = "https://media.w3.org/2010/05/sintel/trailer.mp4"
_SOURCE_PAGE = "https://www.w3.org/2010/05/video/mediaevents"
_SOURCE_CONTEXT = (
    "W3C HTML5 media-events test asset; W3C credits the Blender Foundation"
)
_MAX_FILE_BYTES = 8 * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def _run_sample(
    provider: ModuleType,
    sample_root: Path,
) -> dict[str, int | float | str]:
    sample_root.mkdir()
    progress_events = 0

    def record_event(message: dict[str, Any]) -> None:
        nonlocal progress_events
        if message.get("type") == "progress":
            progress_events += 1

    # Tighten the provider for this fixed workload. The smoke never relaxes
    # production URL, redirect, DNS, filename or output-path validation.
    provider.MAX_FILE_BYTES = _MAX_FILE_BYTES
    provider._STREAM_CHUNK_BYTES = _CHUNK_BYTES
    provider.emit = record_event
    started_at = time.perf_counter_ns()
    cpu_started_at = time.process_time_ns()
    output = Path(
        provider.download(
            {
                "url": _SAMPLE_URL,
                "output_dir": str(sample_root),
                "provider_options": {},
            }
        )
    )
    elapsed_ns = time.perf_counter_ns() - started_at
    cpu_ns = time.process_time_ns() - cpu_started_at
    resolved_root = sample_root.resolve()
    if output.parent != resolved_root or output.name != "trailer.mp4":
        raise RuntimeError("HTTPS smoke output escaped its sample root")
    observed_bytes = output.stat().st_size
    if not 0 < observed_bytes <= _MAX_FILE_BYTES:
        raise RuntimeError("HTTPS smoke output size is outside its safety bound")
    expected_events = math.ceil(observed_bytes / _CHUNK_BYTES)
    if progress_events != expected_events:
        raise RuntimeError("HTTPS smoke progress event count is inconsistent")
    seconds = elapsed_ns / 1_000_000_000
    return {
        "elapsed_ms": elapsed_ns / 1_000_000,
        "cpu_ms": cpu_ns / 1_000_000,
        "throughput_mib_s": observed_bytes / (1024**2) / seconds,
        "progress_events": progress_events,
        "observed_bytes": observed_bytes,
        "sha256": _file_sha256(output),
    }


SampleRunner = Callable[
    [ModuleType, Path],
    dict[str, int | float | str],
]


def run_smoke(
    *,
    repository_root: Path,
    temp_root: Path | None = None,
    sample_runner: SampleRunner | None = None,
    include_source_identity: bool = True,
) -> dict[str, Any]:
    """Execute exactly one bounded real-HTTPS sample and return its report."""

    repository = repository_root.resolve()
    benchmark_root = g39_baseline.validate_temp_root(
        g39_baseline.default_temp_root() if temp_root is None else temp_root,
        repository,
    )
    provider = _load_provider(repository)
    runner = _run_sample if sample_runner is None else sample_runner
    attempt, token = g39_baseline._create_owned_attempt(benchmark_root)
    cleanup_succeeded = False
    try:
        sample_root = attempt / "sample-01"
        sample = runner(provider, sample_root)
        sha256 = sample.get("sha256")
        observed_bytes = sample.get("observed_bytes")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise RuntimeError("HTTPS smoke sample omitted a valid SHA-256")
        if (
            not isinstance(observed_bytes, int)
            or isinstance(observed_bytes, bool)
            or not 0 < observed_bytes <= _MAX_FILE_BYTES
        ):
            raise RuntimeError("HTTPS smoke sample omitted a bounded byte count")
        g39_baseline._cleanup_sample(sample_root, attempt)
    finally:
        g39_baseline._remove_owned_attempt(attempt, token)
        cleanup_succeeded = not attempt.exists()

    if include_source_identity:
        source = {
            "core_version": CORE_VERSION,
            "fingerprint_sha256": source_fingerprint(repository),
            "revision": source_revision(repository),
        }
    else:
        source = {
            "core_version": "not-recorded",
            "fingerprint_sha256": "not-recorded",
            "revision": "not-recorded",
        }
    return {
        "schema_version": _SCHEMA_VERSION,
        "result": "HTTPS_SMOKE_RECORDED",
        "source": source,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
        },
        "sample_source": {
            "url": _SAMPLE_URL,
            "information_page": _SOURCE_PAGE,
            "context": _SOURCE_CONTEXT,
            "observed_bytes": observed_bytes,
            "observed_sha256": sha256,
        },
        "workload": {
            "id": _WORKLOAD_ID,
            "requests": 1,
            "chunk_bytes": _CHUNK_BYTES,
            "maximum_file_bytes": _MAX_FILE_BYTES,
            "network_performance_claim": False,
        },
        "observation": {
            "elapsed_ms": round(float(sample["elapsed_ms"]), 3),
            "cpu_ms": round(float(sample["cpu_ms"]), 3),
            "throughput_mib_s": round(float(sample["throughput_mib_s"]), 3),
            "progress_events": int(sample["progress_events"]),
        },
        "safety": {
            "network_allowed": True,
            "fixed_reviewed_url_only": True,
            "provider_url_policy_changed": False,
            "provider_size_limit_tightened": True,
            "user_data_read": False,
            "owned_attempt_removed": cleanup_succeeded,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Permit one request to the fixed W3C HTTPS test asset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = _parser().parse_args(argv)
    if not parsed.execute:
        print("HTTPS_SMOKE_NOT_EXECUTED: pass --execute to allow one request")
        return 0
    repository = Path(__file__).resolve().parents[1]
    try:
        report = run_smoke(
            repository_root=repository,
            temp_root=parsed.temp_root,
        )
        output = write_report(report, parsed.output, repository)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Direct HTTP HTTPS smoke failed: {error}")
        return 2
    print(f"Direct HTTP HTTPS smoke written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
