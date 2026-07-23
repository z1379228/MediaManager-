import json
from pathlib import Path

from core.downloads.site_quality import audit_builtin_site_quality
from core.mod_groups import SITE_MOD_CHILDREN
from core.site_routing import (
    BILIBILI_HOSTS,
    FACEBOOK_HOSTS,
    INSTAGRAM_HOSTS,
    MEGA_HOSTS,
    THREADS_HOSTS,
    X_HOSTS,
    YOUTUBE_HOSTS,
)


ROOT = Path(__file__).parents[1]


def test_repository_site_quality_matrix_passes_offline() -> None:
    report = audit_builtin_site_quality(ROOT)
    assert report.valid, report.errors
    assert report.checked_sites == 12
    assert report.checked_features == 34
    assert report.checked_workflows == 49


def test_canonical_host_inventory_covers_every_exact_input_host() -> None:
    generic_manifest = json.loads(
        (
            ROOT / "mod" / "builtin" / "generic-ytdlp" / "provider.json"
        ).read_text(encoding="utf-8")
    )
    expected_hosts = (
        YOUTUBE_HOSTS
        | BILIBILI_HOSTS
        | FACEBOOK_HOSTS
        | MEGA_HOSTS
        | INSTAGRAM_HOSTS
        | THREADS_HOSTS
        | X_HOSTS
        | frozenset(generic_manifest["url_hosts"])
    )
    inventory = (ROOT / "docs" / "site-host-inventory.md").read_text(
        encoding="utf-8"
    )
    exact_input_sections = inventory.split("## 程式會連線但不可貼入的主機", 1)[0]

    missing_hosts = sorted(
        host for host in expected_hosts if f"`{host}`" not in exact_input_sections
    )

    assert missing_hosts == []


def copy_site_matrices(target: Path) -> None:
    provider_ids = (*SITE_MOD_CHILDREN, "generic-ytdlp")
    for provider_id in provider_ids:
        filenames = ["site-matrix.json"]
        if provider_id == "generic-ytdlp":
            filenames.append("provider.json")
        for filename in filenames:
            source = ROOT / "mod" / "builtin" / provider_id / filename
            destination = target / "mod" / "builtin" / provider_id / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
    for provider_id in ("youtube", "bilibili", "facebook", "mega"):
        source = ROOT / "mod" / "builtin" / provider_id / "provider.json"
        destination = target / "mod" / "builtin" / provider_id / "provider.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())


def test_site_quality_rejects_missing_bilibili_policy(tmp_path: Path) -> None:
    copy_site_matrices(tmp_path)
    path = tmp_path / "mod" / "builtin" / "bilibili" / "site-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["boundaries"] = ["No cookie import or automated login"]
    path.write_text(json.dumps(matrix), encoding="utf-8")

    report = audit_builtin_site_quality(tmp_path)
    assert not report.valid
    assert any("bilibili policy boundary missing" in error for error in report.errors)


def test_site_quality_rejects_overclaimed_or_missing_workflow(tmp_path: Path) -> None:
    copy_site_matrices(tmp_path)
    path = tmp_path / "mod" / "builtin" / "facebook" / "site-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["workflow"].pop("cancel")
    matrix["ui_capabilities"].append("subtitle-search")
    path.write_text(json.dumps(matrix), encoding="utf-8")

    report = audit_builtin_site_quality(tmp_path)
    assert not report.valid
    assert any("workflow stages are incomplete" in error for error in report.errors)
    assert any("UI capability list is invalid" in error for error in report.errors)


def test_site_quality_rejects_generic_manifest_host_drift(tmp_path: Path) -> None:
    copy_site_matrices(tmp_path)
    path = tmp_path / "mod" / "builtin" / "generic-ytdlp" / "provider.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["url_hosts"].remove("player.twitch.tv")
    path.write_text(json.dumps(manifest), encoding="utf-8")

    report = audit_builtin_site_quality(tmp_path)

    assert not report.valid
    assert "generic manifest and site matrix hosts differ" in report.errors


def test_site_quality_rejects_dedicated_manifest_host_drift(tmp_path: Path) -> None:
    copy_site_matrices(tmp_path)
    path = tmp_path / "mod" / "builtin" / "youtube" / "provider.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["url_hosts"].remove("www.youtube.com")
    path.write_text(json.dumps(manifest), encoding="utf-8")

    report = audit_builtin_site_quality(tmp_path)

    assert not report.valid
    assert "youtube manifest and canonical route hosts differ" in report.errors
