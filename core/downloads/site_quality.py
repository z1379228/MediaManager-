"""Offline quality audit for advertised built-in site workflows."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from core.mod_groups import SITE_MOD_CHILDREN


_SUPPORT_STATES = frozenset(
    {
        "verified-public-analysis",
        "offline-contract",
        "verified-local-ffmpeg",
        "browser-mediated-official",
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
    matrix: dict[str, object], errors: list[str]
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


def audit_builtin_site_quality(root: Path) -> SiteQualityReport:
    """Check every site-family workflow and policy without network access."""

    errors: list[str] = []
    checked_sites = 0
    checked_features = 0
    checked_workflows = 0
    builtin = root.resolve() / "mod" / "builtin"
    try:
        generic = _load(builtin / "generic-ytdlp" / "site-matrix.json")
    except (OSError, ValueError, TypeError) as error:
        errors.append(str(error))
    else:
        sites, features = _audit_generic_sites(generic, errors)
        checked_sites += sites
        checked_features += features

    for provider_id in SITE_MOD_CHILDREN:
        try:
            matrix = _load(builtin / provider_id / "site-matrix.json")
        except (OSError, ValueError, TypeError) as error:
            errors.append(str(error))
            continue
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
