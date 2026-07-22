import json
from pathlib import Path

from core.downloads.site_quality import audit_builtin_site_quality
from core.mod_groups import SITE_MOD_CHILDREN


ROOT = Path(__file__).parents[1]


def test_repository_site_quality_matrix_passes_offline() -> None:
    report = audit_builtin_site_quality(ROOT)
    assert report.valid, report.errors
    assert report.checked_sites == 12
    assert report.checked_features == 33
    assert report.checked_workflows == 49


def copy_site_matrices(target: Path) -> None:
    provider_ids = (*SITE_MOD_CHILDREN, "generic-ytdlp")
    for provider_id in provider_ids:
        source = ROOT / "mod" / "builtin" / provider_id / "site-matrix.json"
        destination = target / "mod" / "builtin" / provider_id / "site-matrix.json"
        destination.parent.mkdir(parents=True)
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
