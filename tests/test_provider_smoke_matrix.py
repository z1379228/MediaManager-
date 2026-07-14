from __future__ import annotations

import json

import pytest

from tools.provider_smoke_matrix import DEFAULT_CASES, SmokeCase, run_matrix


def test_smoke_matrix_records_pass_and_failure_without_network(tmp_path) -> None:
    cases = (
        SmokeCase("pass", "youtube", "https://youtube.com/watch?v=test"),
        SmokeCase("fail", "bilibili", "https://bilibili.com/video/test"),
    )

    def analyzer(case, _release_root):
        if case.case_id == "fail":
            raise RuntimeError("unavailable")
        return {"media_id": "test", "title": "Test", "duration": 1}

    target = tmp_path / "matrix.json"
    report = run_matrix(
        release_root=tmp_path,
        report_path=target,
        cases=cases,
        analyzer=analyzer,
    )
    assert report["status"] == "FAIL"
    assert [row["status"] for row in report["cases"]] == ["PASS", "FAIL"]
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 1
    assert report["mode"] == "live-public-content"
    assert not target.with_suffix(".json.tmp").exists()


def test_smoke_matrix_rejects_duplicate_case_ids(tmp_path) -> None:
    duplicate = SmokeCase("same", "youtube", "https://youtube.com/watch?v=test")
    with pytest.raises(ValueError, match="unique"):
        run_matrix(
            release_root=tmp_path,
            report_path=tmp_path / "matrix.json",
            cases=(duplicate, duplicate),
            analyzer=lambda *_: {},
        )


def test_default_matrix_covers_every_advertised_site_family() -> None:
    case_ids = {case.case_id for case in DEFAULT_CASES}
    assert {
        "youtube-public-video",
        "generic-vimeo-public-video",
        "generic-dailymotion-public-video",
        "generic-soundcloud-public-track",
        "generic-tiktok-public-video",
        "generic-twitch-public-clip",
        "generic-twitter-public-video",
        "bilibili-public-video",
    }.issubset(case_ids)
