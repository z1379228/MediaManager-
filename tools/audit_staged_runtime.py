"""Verify staged portable runtimes against the pinned offline policy."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from core.runtime_policy import (
    DENO_EXECUTABLE_SHA256,
    DENO_VERSION,
    FFMPEG_PORTABLE_SHA256,
    FFMPEG_VERSION,
)
from core.security.release_layout import PORTABLE_RUNTIME_FILES


DENO_LICENSE_SOURCE = Path("third_party/deno/LICENSE.md")
_FIXED_RUNTIME_HASH_FILES = (
    "tools/deno.exe",
    "tools/ffmpeg.exe",
    "tools/ffprobe.exe",
    "tools/FFMPEG-LICENSE.txt",
    "tools/FFMPEG-README.txt",
)
_EXPECTED_PORTABLE_RUNTIME_FILES = (
    "tools/deno.exe",
    "tools/DENO-LICENSE.md",
    "tools/ffmpeg.exe",
    "tools/ffprobe.exe",
    "tools/FFMPEG-LICENSE.txt",
    "tools/FFMPEG-README.txt",
)


@dataclass(frozen=True, slots=True)
class StagedRuntimePolicyReport:
    valid: bool
    checked: int
    deno_version: str
    ffmpeg_version: str
    deno_license_source: str
    deno_license_sha256: str | None
    errors: tuple[str, ...]


def _is_unsafe_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction is not None and is_junction())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_descendant(
    base: Path,
    parts: Sequence[str],
    *,
    expect_directory: bool = False,
) -> Path | None:
    """Return a contained path only when every component is non-reparse."""

    try:
        resolved_base = base.resolve(strict=True)
    except OSError:
        return None
    candidate = base
    for part in parts:
        candidate /= part
        try:
            if _is_unsafe_link(candidate):
                return None
        except OSError:
            return None
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except OSError:
        return None
    if not resolved_candidate.is_relative_to(resolved_base):
        return None
    if expect_directory:
        return candidate if candidate.is_dir() else None
    return candidate if candidate.is_file() else None


def _load_bounded_json_object(path: Path, *, limit: int) -> dict[str, object]:
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("JSON exceeds the audit size limit")

    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    document = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(document, dict):
        raise ValueError("JSON root must be an object")
    return document


def _fixed_hash_policy() -> dict[str, str]:
    return {
        "tools/deno.exe": DENO_EXECUTABLE_SHA256,
        **{
            f"tools/{name}": digest
            for name, digest in FFMPEG_PORTABLE_SHA256.items()
        },
    }


def audit_staged_runtime(
    root: Path,
    *,
    source_root: Path | None = None,
) -> StagedRuntimePolicyReport:
    """Audit one owned, quiescent stage without running or downloading tools."""

    raw_root = root
    raw_source_root = (
        Path(__file__).resolve().parents[1]
        if source_root is None
        else source_root
    )
    errors: list[str] = []
    checked = 0

    if tuple(PORTABLE_RUNTIME_FILES) != _EXPECTED_PORTABLE_RUNTIME_FILES:
        errors.append("portable runtime release layout does not match policy")
    fixed_hashes = _fixed_hash_policy()
    if set(fixed_hashes) != set(_FIXED_RUNTIME_HASH_FILES):
        errors.append("portable runtime hash set does not match policy")

    if _is_unsafe_link(raw_root) or not raw_root.is_dir():
        errors.append("staged release root is missing or unsafe")
        return StagedRuntimePolicyReport(
            valid=False,
            checked=checked,
            deno_version=DENO_VERSION,
            ffmpeg_version=FFMPEG_VERSION,
            deno_license_source=DENO_LICENSE_SOURCE.as_posix(),
            deno_license_sha256=None,
            errors=tuple(errors),
        )
    root = raw_root.resolve()
    tools_root = _safe_descendant(
        root,
        ("tools",),
        expect_directory=True,
    )
    if tools_root is None:
        errors.append("staged tools directory is missing or unsafe")
    else:
        try:
            expected_names = {
                Path(name).name for name in _EXPECTED_PORTABLE_RUNTIME_FILES
            }
            for entry in tools_root.iterdir():
                if entry.name not in expected_names:
                    errors.append(
                        f"unexpected staged runtime entry: tools/{entry.name}"
                    )
        except OSError:
            errors.append("staged tools directory cannot be read")

    source_license: Path | None = None
    source_license_hash: str | None = None
    if _is_unsafe_link(raw_source_root) or not raw_source_root.is_dir():
        errors.append("source root is missing or unsafe")
    else:
        source_license = _safe_descendant(
            raw_source_root,
            tuple(DENO_LICENSE_SOURCE.parts),
        )
        if source_license is None:
            errors.append("canonical Deno license source is missing or unsafe")
        else:
            try:
                source_license_hash = _sha256(source_license)
            except OSError as error:
                errors.append(
                    f"canonical Deno license source cannot be read: {error}"
                )

    if tools_root is not None:
        for relative_name in _EXPECTED_PORTABLE_RUNTIME_FILES:
            candidate = _safe_descendant(
                root,
                tuple(relative_name.split("/")),
            )
            if candidate is None:
                errors.append(
                    f"staged runtime file is missing or unsafe: {relative_name}"
                )
                continue
            try:
                actual_hash = _sha256(candidate)
            except OSError as error:
                errors.append(
                    f"staged runtime file cannot be read: {relative_name}: {error}"
                )
                continue
            checked += 1
            if relative_name == "tools/DENO-LICENSE.md":
                if (
                    source_license_hash is not None
                    and actual_hash != source_license_hash
                ):
                    errors.append(
                        "staged Deno license does not match canonical source"
                    )
                continue
            expected_hash = fixed_hashes.get(relative_name)
            if expected_hash is None:
                errors.append(
                    f"staged runtime file has no hash policy: {relative_name}"
                )
            elif actual_hash != expected_hash:
                errors.append(f"staged runtime hash mismatch: {relative_name}")

    release_info = root / "release-info.json"
    if _is_unsafe_link(release_info) or not release_info.is_file():
        errors.append("release-info.json is missing or unsafe")
    else:
        try:
            document = _load_bounded_json_object(
                release_info,
                limit=64 * 1024,
            )
            portable_tools = document.get("portable_tools")
            expected_tools = sorted(
                Path(name).name for name in _EXPECTED_PORTABLE_RUNTIME_FILES
            )
            if portable_tools != expected_tools:
                errors.append(
                    "release-info.json portable_tools does not match runtime policy"
                )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
            RecursionError,
        ):
            errors.append("release-info.json cannot provide portable_tools")

    return StagedRuntimePolicyReport(
        valid=not errors,
        checked=checked,
        deno_version=DENO_VERSION,
        ffmpeg_version=FFMPEG_VERSION,
        deno_license_source=DENO_LICENSE_SOURCE.as_posix(),
        deno_license_sha256=source_license_hash,
        errors=tuple(errors),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args(argv)
    report = audit_staged_runtime(
        args.root,
        source_root=args.source_root,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
