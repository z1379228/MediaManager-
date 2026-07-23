"""Offline quality audit for advertised built-in site workflows."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from core.mod_groups import SITE_MOD_CHILDREN
from core.site_routing import (
    BILIBILI_MEDIA_HOSTS,
    FACEBOOK_HOSTS,
    MEGA_HOSTS,
    YOUTUBE_HOSTS,
)


_SUPPORT_STATES = frozenset(
    {
        "verified-public-analysis",
        "offline-contract",
        "verified-local-ffmpeg",
        "browser-mediated-official",
        "local-only",
        "local-ui",
    }
)
_WORKFLOW_STAGES = (
    "identify",
    "discover",
    "analyze",
    "preview",
    "queue",
    "cancel",
    "complete",
)
_WORKFLOW_STATES = frozenset(
    {"supported", "conditional", "browser-mediated", "not-applicable"}
)
_UI_CAPABILITIES = frozenset(
    {
        "search",
        "thumbnail",
        "audio-preview",
        "video-preview",
        "batch",
        "download",
        "danmaku",
        "offline-archive",
        "official-page",
        "embedded-official-page",
        "local-watch-history",
        "user-controlled-next-episode",
        "tree-preview",
        "pause",
        "cancel",
    }
)
_REQUIRED_BOUNDARY_TOKENS = (
    "cookie",
    "login",
    "region",
    "payment",
    "drm",
    "advertisement",
    "private",
)
_DATE = re.compile(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}$")
_DEDICATED_ROUTE_HOSTS = {
    "youtube": YOUTUBE_HOSTS,
    "bilibili": BILIBILI_MEDIA_HOSTS,
    "facebook": FACEBOOK_HOSTS,
    "mega": MEGA_HOSTS,
}


@dataclass(frozen=True, slots=True)
class SiteQualityReport:
    valid: bool
    checked_sites: int
    checked_features: int
    checked_workflows: int
    errors: tuple[str, ...]


def _load(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256_000:
        raise ValueError(f"site matrix is missing or unsafe: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"site matrix must be an object: {path}")
    return raw


def _audit_generic_sites(
    matrix: dict[str, object],
    manifest: dict[str, object],
    errors: list[str],
) -> tuple[int, int]:
    sites = matrix.get("sites")
    if not isinstance(sites, list) or not 1 <= len(sites) <= 20:
        errors.append("generic site list is invalid")
        return 0, 0
    site_ids: set[str] = set()
    hosts: set[str] = set()
    checked_sites = 0
    for site in sites:
        if not isinstance(site, dict):
            errors.append("generic site entry is invalid")
            continue
        site_id = site.get("site_id")
        site_hosts = site.get("hosts")
        if not isinstance(site_id, str) or not site_id or site_id in site_ids:
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
    manifest_hosts = manifest.get("url_hosts")
    if manifest.get("provider_id") != matrix.get("provider_id"):
        errors.append("generic manifest and site matrix identities differ")
    if (
        not isinstance(manifest_hosts, list)
        or any(not isinstance(host, str) or not host for host in manifest_hosts)
        or len(manifest_hosts) != len(set(manifest_hosts))
    ):
        errors.append("generic manifest host list is invalid")
    elif set(manifest_hosts) != hosts:
        errors.append("generic manifest and site matrix hosts differ")
    return checked_sites, 0


def _audit_site_family(
    provider_id: str,
    matrix: dict[str, object],
    errors: list[str],
) -> tuple[int, int]:
    expected_fields = {
        "schema_version",
        "provider_id",
        "last_live_check",
        "workflow",
        "ui_capabilities",
        "features",
        "boundaries",
    }
    if set(matrix) != expected_fields:
        errors.append(f"{provider_id} site matrix fields are invalid")
    if matrix.get("schema_version") != 2 or matrix.get("provider_id") != provider_id:
        errors.append(f"{provider_id} site matrix identity is invalid")
    last_live_check = matrix.get("last_live_check")
    if not isinstance(last_live_check, str) or not _DATE.fullmatch(last_live_check):
        errors.append(f"{provider_id} live-check date is invalid")

    workflow = matrix.get("workflow")
    checked_workflows = 0
    if not isinstance(workflow, dict) or tuple(workflow) != _WORKFLOW_STAGES:
        errors.append(f"{provider_id} workflow stages are incomplete")
    else:
        for stage, state in workflow.items():
            if state not in _WORKFLOW_STATES:
                errors.append(f"{provider_id} workflow state is invalid: {stage}")
            else:
                checked_workflows += 1

    raw_capabilities = matrix.get("ui_capabilities")
    if (
        not isinstance(raw_capabilities, list)
        or len(raw_capabilities) != len(set(raw_capabilities))
        or any(value not in _UI_CAPABILITIES for value in raw_capabilities)
    ):
        errors.append(f"{provider_id} UI capability list is invalid")

    features = matrix.get("features")
    checked_features = 0
    feature_ids: set[str] = set()
    if not isinstance(features, list) or not features:
        errors.append(f"{provider_id} feature declarations are missing")
    else:
        for feature in features:
            if not isinstance(feature, dict) or set(feature) != {
                "feature_id",
                "support_status",
            }:
                errors.append(f"{provider_id} feature declaration is invalid")
                continue
            feature_id = feature.get("feature_id")
            if (
                not isinstance(feature_id, str)
                or not feature_id
                or feature_id in feature_ids
            ):
                errors.append(f"{provider_id} feature IDs must be unique")
                continue
            feature_ids.add(feature_id)
            if feature.get("support_status") not in _SUPPORT_STATES:
                errors.append(f"{provider_id} feature status is invalid: {feature_id}")
            checked_features += 1

    boundaries = matrix.get("boundaries")
    boundary_text = (
        " ".join(boundaries).casefold()
        if isinstance(boundaries, list)
        and boundaries
        and all(isinstance(item, str) for item in boundaries)
        else ""
    )
    if not boundary_text:
        errors.append(f"{provider_id} policy boundaries are invalid")
    for token in _REQUIRED_BOUNDARY_TOKENS:
        if token not in boundary_text:
            errors.append(f"{provider_id} policy boundary missing: {token}")
    return checked_features, checked_workflows


def _audit_dedicated_manifest_hosts(
    provider_id: str,
    manifest: dict[str, object],
    errors: list[str],
) -> None:
    expected = _DEDICATED_ROUTE_HOSTS.get(provider_id)
    if expected is None:
        return
    raw_hosts = manifest.get("url_hosts")
    if (
        manifest.get("provider_id") != provider_id
        or not isinstance(raw_hosts, list)
        or any(not isinstance(host, str) or not host for host in raw_hosts)
        or len(raw_hosts) != len(set(raw_hosts))
    ):
        errors.append(f"{provider_id} manifest host list is invalid")
    elif set(raw_hosts) != expected:
        errors.append(f"{provider_id} manifest and canonical route hosts differ")


def audit_builtin_site_quality(root: Path) -> SiteQualityReport:
    """Check every site-family workflow and policy without network access."""

    errors: list[str] = []
    checked_sites = 0
    checked_features = 0
    checked_workflows = 0
    builtin = root.resolve() / "mod" / "builtin"
    try:
        generic = _load(builtin / "generic-ytdlp" / "site-matrix.json")
        generic_manifest = _load(builtin / "generic-ytdlp" / "provider.json")
    except (OSError, ValueError, TypeError) as error:
        errors.append(str(error))
    else:
        sites, features = _audit_generic_sites(generic, generic_manifest, errors)
        checked_sites += sites
        checked_features += features

    for provider_id in SITE_MOD_CHILDREN:
        try:
            matrix = _load(builtin / provider_id / "site-matrix.json")
            manifest = (
                _load(builtin / provider_id / "provider.json")
                if provider_id in _DEDICATED_ROUTE_HOSTS
                else None
            )
        except (OSError, ValueError, TypeError) as error:
            errors.append(str(error))
            continue
        if manifest is not None:
            _audit_dedicated_manifest_hosts(provider_id, manifest, errors)
        checked_sites += 1
        features, workflows = _audit_site_family(provider_id, matrix, errors)
        checked_features += features
        checked_workflows += workflows
    return SiteQualityReport(
        not errors,
        checked_sites,
        checked_features,
        checked_workflows,
        tuple(errors),
    )
