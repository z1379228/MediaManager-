from __future__ import annotations

from pathlib import Path

import pytest

from tools import direct_http_https_baseline


ROOT = Path(__file__).parents[1]
_DIGEST = "a" * 64


def test_https_smoke_is_dry_run_by_default(tmp_path: Path) -> None:
    output = tmp_path / "evidence.json"

    assert direct_http_https_baseline.main(["--output", str(output)]) == 0
    assert not output.exists()


def test_https_smoke_records_one_fixed_bounded_request(tmp_path: Path) -> None:
    calls = 0

    def sample_runner(
        _provider: object,
        sample_root: Path,
    ) -> dict[str, int | float | str]:
        nonlocal calls
        calls += 1
        sample_root.mkdir()
        (sample_root / "owned.tmp").write_bytes(b"sample")
        return {
            "elapsed_ms": 100.0,
            "cpu_ms": 10.0,
            "throughput_mib_s": 45.0,
            "progress_events": 5,
            "observed_bytes": 4_802_157,
            "sha256": _DIGEST,
        }

    report = direct_http_https_baseline.run_smoke(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        sample_runner=sample_runner,
        include_source_identity=False,
    )

    assert calls == 1
    assert report["result"] == "HTTPS_SMOKE_RECORDED"
    assert report["sample_source"]["observed_bytes"] == 4_802_157
    assert report["sample_source"]["observed_sha256"] == _DIGEST
    assert report["workload"] == {
        "id": "direct-http-w3c-html5-video-smoke-v1",
        "requests": 1,
        "chunk_bytes": 1024 * 1024,
        "maximum_file_bytes": 8 * 1024 * 1024,
        "network_performance_claim": False,
    }
    assert report["observation"]["progress_events"] == 5
    assert report["safety"]["fixed_reviewed_url_only"] is True
    assert report["safety"]["owned_attempt_removed"] is True
    assert not tuple((tmp_path / "runs").glob("g39-*"))


@pytest.mark.parametrize(
    ("observed_bytes", "sha256"),
    ((0, _DIGEST), (8 * 1024 * 1024 + 1, _DIGEST), (1, "bad")),
)
def test_https_smoke_rejects_invalid_sample_evidence_and_cleans_up(
    tmp_path: Path,
    observed_bytes: int,
    sha256: str,
) -> None:
    def sample_runner(
        _provider: object,
        sample_root: Path,
    ) -> dict[str, int | float | str]:
        sample_root.mkdir()
        (sample_root / "owned.tmp").write_bytes(b"sample")
        return {
            "elapsed_ms": 100.0,
            "cpu_ms": 10.0,
            "throughput_mib_s": 45.0,
            "progress_events": 1,
            "observed_bytes": observed_bytes,
            "sha256": sha256,
        }

    with pytest.raises(RuntimeError):
        direct_http_https_baseline.run_smoke(
            repository_root=ROOT,
            temp_root=tmp_path / "runs",
            sample_runner=sample_runner,
            include_source_identity=False,
        )

    assert not tuple((tmp_path / "runs").glob("g39-*"))
