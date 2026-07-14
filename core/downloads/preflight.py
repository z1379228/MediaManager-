"""Bounded, side-effect-free checks before a download batch is queued."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import shutil

from core.downloads.models import DownloadRequest


DEFAULT_FREE_SPACE_RESERVE = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DownloadPreflight:
    output_directories: tuple[Path, ...]
    minimum_free_bytes: int
    lowest_free_bytes: int
    estimated_bytes: int | None = None
    required_free_bytes: int = DEFAULT_FREE_SPACE_RESERVE


def _existing_anchor(path: Path) -> Path:
    candidate = path.resolve(strict=False)
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError(f"download output path is unavailable or unsafe: {path}")
    return candidate


def preflight_download_batch(
    requests: Iterable[DownloadRequest],
    *,
    minimum_free_bytes: int = DEFAULT_FREE_SPACE_RESERVE,
    estimated_bytes: int | None = None,
) -> DownloadPreflight:
    """Reject unsafe destinations and obviously insufficient disk space."""

    values = tuple(requests)
    if not values:
        raise ValueError("download batch is empty")
    if minimum_free_bytes < 0:
        raise ValueError("minimum free-space reserve is invalid")
    if (
        estimated_bytes is not None
        and (
            not isinstance(estimated_bytes, int)
            or isinstance(estimated_bytes, bool)
            or not 0 <= estimated_bytes <= 10**15
        )
    ):
        raise ValueError("estimated download size is invalid")
    required_free = minimum_free_bytes + (estimated_bytes or 0)
    outputs = tuple(dict.fromkeys(request.output_dir.resolve(strict=False) for request in values))
    free_values = []
    for output in outputs:
        anchor = _existing_anchor(output)
        free = shutil.disk_usage(anchor).free
        free_values.append(free)
        if free < required_free:
            required_mib = required_free // (1024 * 1024)
            available_mib = free // (1024 * 1024)
            raise RuntimeError(
                f"下載磁碟空間不足：至少保留 {required_mib} MiB，"
                f"目前約 {available_mib} MiB"
            )
    for request in values:
        if not request.output_filename:
            continue
        target = (request.output_dir / request.output_filename).resolve(strict=False)
        output = request.output_dir.resolve(strict=False)
        if not target.is_relative_to(output):
            raise ValueError("download output filename escapes destination")
        if target.exists():
            raise FileExistsError(f"下載目標已存在，不會覆蓋：{target.name}")
    return DownloadPreflight(
        outputs,
        minimum_free_bytes,
        min(free_values),
        estimated_bytes,
        required_free,
    )
