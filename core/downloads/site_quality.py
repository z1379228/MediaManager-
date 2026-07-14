"""Offline quality audit for advertised built-in site capabilities."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


_SUPPORT_STATES = frozenset(
    {"verified-public-analysis", "offline-contract", "verified-local-ffmpeg"}
)
_BILIBILI_FEATURES = frozenset(
    {
        "public-video-analysis",
        "multipart-playlist",
        "bangumi-public-episode",
        "subtitles",
        "danmaku-xml-ass-mkv",
    }
)


@dataclass(frozen=True, slots=True)
class SiteQualityReport:
    valid: bool
    checked_sites: int
    checked_features: int
    errors: tuple[str, ...]


def _load(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256_000:
        raise ValueError(f"site matrix is missing or unsafe: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"site matrix must be an object: {path}")
    return raw


def audit_builtin_site_quality(root: Path) -> SiteQualityReport:
    """Check declared coverage and policy boundaries without network access."""

    errors: list[str] = []
    checked_sites = 0
    checked_features = 0
    builtin = root.resolve() / "mod" / "builtin"
    try:
        generic = _load(builtin / "generic-ytdlp" / "site-matrix.json")
        bilibili = _load(builtin / "bilibili" / "site-matrix.json")
    except (OSError, ValueError, TypeError) as error:
        return SiteQualityReport(False, 0, 0, (str(error),))

    sites = generic.get("sites")
    if not isinstance(sites, list) or not 1 <= len(sites) <= 20:
        errors.append("generic site list is invalid")
        sites = []
    site_ids: set[str] = set()
    hosts: set[str] = set()
    for site in sites:
        if not isinstance(site, dict):
            errors.append("generic site entry is invalid")
            continue
        site_id = site.get("site_id")
        site_hosts = site.get("hosts")
        if not isinstance(site_id, str) or site_id in site_ids:
            errors.append("generic site IDs must be non-empty and unique")
            continue
        site_ids.add(site_id)
        if site.get("support_status") not in _SUPPORT_STATES:
            errors.append(f"unsupported status for site: {site_id}")
        if not isinstance(site_hosts, list) or not site_hosts:
            errors.append(f"site has no declared hosts: {site_id}")
            continue
        for host in site_hosts:
            if not isinstance(host, str) or not host or host in hosts:
                errors.append(f"duplicate or invalid host: {host}")
            else:
                hosts.add(host)
        checked_sites += 1

    features = bilibili.get("features")
    feature_ids = {
        feature.get("feature_id")
        for feature in features
        if isinstance(feature, dict)
    } if isinstance(features, list) else set()
    checked_features = len(feature_ids)
    missing = _BILIBILI_FEATURES - feature_ids
    if missing:
        errors.append(f"Bilibili feature declarations missing: {sorted(missing)}")
    boundaries = bilibili.get("boundaries")
    boundary_text = " ".join(boundaries).casefold() if isinstance(boundaries, list) and all(isinstance(item, str) for item in boundaries) else ""
    for required in ("cookie", "region", "drm", "payment"):
        if required not in boundary_text:
            errors.append(f"Bilibili policy boundary missing: {required}")
    return SiteQualityReport(not errors, checked_sites, checked_features, tuple(errors))
