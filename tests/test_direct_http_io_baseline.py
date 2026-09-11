from __future__ import annotations

from pathlib import Path

import pytest

from tools import direct_http_io_baseline


def test_small_baseline_uses_provider_path_without_network_and_cleans_attempt(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).parents[1]
    temp_root = tmp_path / "benchmarks"

    report = direct_http_io_baseline.run_baseline(
        repository_root=repository,
        temp_root=temp_root,
        warmups=0,
        iterations=2,
        payload_bytes=65,
        chunk_sizes=(4, 16),
        include_source_identity=False,
    )

    assert report["schema_version"] == 1
    assert report["workload"] == {
        "id": "direct-http-synthetic-stream-v1",
        "warmups": 0,
        "iterations": 2,
        "payload_bytes": 65,
        "chunk_sizes": [4, 16],
        "expected_transient_write_bytes": 260,
    }
    assert [item["chunk_bytes"] for item in report["results"]] == [4, 16]
    assert all(item["samples"] == 2 for item in report["results"])
    assert all(
        item["progress_events"]["min"] >= 5 for item in report["results"]
    )
    assert report["safety"] == {
        "network_allowed": False,
        "real_url_opened": False,
        "user_data_read": False,
        "provider_security_policy_changed": False,
        "owned_attempt_removed": True,
    }
    assert temp_root.is_dir()
    assert not any(temp_root.iterdir())


@pytest.mark.parametrize(
    ("payload_bytes", "chunk_sizes", "message"),
    (
        (0, (1024,), "payload_bytes"),
        (1024, (), "chunk_sizes"),
        (1024, (0,), "chunk size"),
        (1024, (1024,) * 9, "at most 8"),
    ),
)
def test_baseline_rejects_unbounded_or_empty_workloads_before_writing(
    tmp_path: Path,
    payload_bytes: int,
    chunk_sizes: tuple[int, ...],
    message: str,
) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    temp_root = tmp_path / "benchmarks"

    with pytest.raises(ValueError, match=message):
        direct_http_io_baseline.run_baseline(
            repository_root=repository,
            temp_root=temp_root,
            warmups=0,
            iterations=1,
            payload_bytes=payload_bytes,
            chunk_sizes=chunk_sizes,
            include_source_identity=False,
        )

    assert not temp_root.exists()
