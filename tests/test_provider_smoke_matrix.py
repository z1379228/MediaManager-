from __future__ import annotations

import json

import pytest
import tools.provider_smoke_matrix as smoke_matrix

from tools.provider_smoke_matrix import (
    DEFAULT_CASES,
    SmokeCase,
    classify_smoke_failure,
    run_matrix,
)


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
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 2
    assert report["mode"] == "live-public-content"
    assert report["summary"] == {
        "passed": 1,
        "failed": 1,
        "temporary_upstream": 0,
    }
    assert report["cases"][1]["failure_class"] == "local-or-contract"
    assert not target.with_suffix(".json.tmp").exists()


def test_smoke_matrix_retries_only_temporary_upstream_failures(tmp_path) -> None:
    calls = 0

    def analyzer(_case, _release_root):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("HTTP Error 502: Bad Gateway")
        return {"media_id": "ok", "title": "Recovered", "duration": 1}

    report = run_matrix(
        release_root=tmp_path,
        report_path=tmp_path / "matrix.json",
        cases=(SmokeCase("retry", "youtube", "https://youtube.com/watch?v=x"),),
        analyzer=analyzer,
    )

    assert report["status"] == "PASS"
    assert report["cases"][0]["attempt_count"] == 2
    assert [attempt["status"] for attempt in report["cases"][0]["attempts"]] == [
        "FAIL",
        "PASS",
    ]


def test_smoke_failure_taxonomy_keeps_access_and_unknown_explicit() -> None:
    assert classify_smoke_failure(RuntimeError("HTTP Error 503")) == (
        "temporary-upstream"
    )
    assert classify_smoke_failure(RuntimeError("login required")) == (
        "access-restriction"
    )
    assert classify_smoke_failure(Exception("unexpected")) == "unknown"


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
        "bilibili-public-video",
    }.issubset(case_ids)
    tiktok = next(
        case for case in DEFAULT_CASES if case.case_id == "generic-tiktok-public-video"
    )
    assert tiktok.url.endswith("/video/6984138651336838402")


def test_live_analyzer_uses_provider_from_release_root(
    tmp_path,
    monkeypatch,
) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "deno.exe").write_bytes(b"deno")
    (tmp_path / "tools" / "ffmpeg.exe").write_bytes(b"ffmpeg")
    provider_root = tmp_path / "mod" / "builtin" / "generic-ytdlp"
    provider_root.mkdir(parents=True)
    captured = {}

    class FakeProvider:
        def __init__(self, root, **options):
            captured["root"] = root
            captured["application_root"] = options["application_root"]
            captured["runtime_home"] = options["runtime_home"]

        def analyze(self, url):
            captured["url"] = url
            return {"id": "example", "title": "Example", "duration": 1}

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(smoke_matrix, "SubprocessDownloadProvider", FakeProvider)
    case = SmokeCase(
        "release-copy",
        "generic-ytdlp",
        "https://vimeo.com/123",
    )

    result = smoke_matrix.analyze_case(case, tmp_path)

    assert captured["root"] == provider_root
    assert captured["application_root"] == tmp_path.resolve()
    assert captured["runtime_home"].parent == (
        smoke_matrix.ROOT / ".work" / "provider-smoke-runtime"
    )
    assert captured["runtime_home"].name.startswith("generic-ytdlp-")
    assert not captured["runtime_home"].exists()
    assert captured["closed"] is True
    assert result["media_id"] == "example"
