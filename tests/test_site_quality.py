import json
from pathlib import Path

from core.downloads.site_quality import audit_builtin_site_quality


ROOT = Path(__file__).parents[1]


def test_repository_site_quality_matrix_passes_offline() -> None:
    report = audit_builtin_site_quality(ROOT)
    assert report.valid, report.errors
    assert report.checked_sites == 6
    assert report.checked_features >= 11


def test_site_quality_rejects_missing_bilibili_policy(tmp_path: Path) -> None:
    generic_source = ROOT / "mod" / "builtin" / "generic-ytdlp" / "site-matrix.json"
    generic = tmp_path / "mod" / "builtin" / "generic-ytdlp"
    generic.mkdir(parents=True)
    (generic / "site-matrix.json").write_bytes(generic_source.read_bytes())
    youtube_source = ROOT / "mod" / "builtin" / "youtube" / "site-matrix.json"
    youtube = tmp_path / "mod" / "builtin" / "youtube"
    youtube.mkdir(parents=True)
    (youtube / "site-matrix.json").write_bytes(youtube_source.read_bytes())
    bilibili = tmp_path / "mod" / "builtin" / "bilibili"
    bilibili.mkdir(parents=True)
    (bilibili / "site-matrix.json").write_text(
        json.dumps(
            {
                "features": [
                    {"feature_id": value}
                    for value in (
                        "public-video-analysis",
                        "multipart-playlist",
                        "bangumi-public-episode",
                        "subtitles",
                        "danmaku-xml-ass-mkv",
                    )
                ],
                "boundaries": [],
            }
        ),
        encoding="utf-8",
    )
    report = audit_builtin_site_quality(tmp_path)
    assert not report.valid
    assert any("policy boundary" in error for error in report.errors)
