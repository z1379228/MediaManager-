from pathlib import Path
import sys

import pytest

from tools import startup_baseline


ROOT = Path(__file__).parents[1]


def _sample(role: str, *_args: object) -> dict[str, object]:
    exit_code = 1 if role == "provider-host" else 0
    sample: dict[str, object] = {
        "app_exit_code": exit_code,
        "cpu_time_ms": 10.0,
        "elapsed_ms": 20.0,
        "network_attempts": [],
        "graphical_shell_loaded": False,
        "status": "supported",
        "private_bytes": 100,
        "working_set_bytes": 200,
        "peak_working_set_bytes": 300,
        "os_threads": 2,
    }
    if role.startswith("gui-"):
        materialized = role in {
            "gui-materialized",
            "gui-materialized-foreground-idle",
            "gui-materialized-background-idle",
        }
        sample.update(
            qt_objects=(30 if materialized else 10),
            active_repeat_timers=(0 if role.endswith("background-idle") else 1),
            tabs=4,
            materialized_workspaces=(3 if materialized else 0),
            loaded_deferred_modules=(3 if materialized else 0),
        )
    if role.endswith(("foreground-idle", "background-idle")):
        background = role.endswith("background-idle")
        sample.update(
            background_idle=int(background),
            window_visible=int(not background),
            suspended_timers=(2 if background else 0),
            observation_elapsed_ms=1_000.0,
            observation_cpu_time_ms=(1.0 if background else 5.0),
        )
    if role.startswith("table-"):
        sample.update(
            table_workload_ms=12.5,
            rendered_rows=200,
            refresh_iterations=50,
            item_allocations=(40_000 if role == "table-rebuild" else 800),
            progress_allocations=(
                10_000 if role == "table-rebuild" else 200
            ),
            table_qt_objects=400,
        )
    if role in {
        "search-results",
        "youtube-results",
        "bilibili-results",
    }:
        sample.update(
            search_workload_ms=18.5,
            search_cpu_time_ms=15.625,
            scroll_workload_ms=2.5,
            rendered_rows=200,
            initial_thumbnail_requests=12,
            total_thumbnail_requests=24,
            search_qt_objects=1_500,
            search_resource_status="supported",
            search_private_bytes=70_000_000,
            search_working_set_bytes=95_000_000,
            search_peak_working_set_bytes=96_000_000,
            search_os_threads=8,
        )
    return sample


def test_baseline_aggregates_isolated_role_samples(tmp_path: Path) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=1,
        iterations=2,
        roles=("version", "provider-host"),
        sample_runner=_sample,
    )

    assert report["result"] == "BASELINE_RECORDED"
    assert report["schema_version"] == 4
    assert report["workload"]["network_allowed"] is False
    assert report["workload"]["visible_ui_allowed"] is False
    assert report["roles"]["version"]["samples"] == 2
    assert report["roles"]["provider-host"]["app_exit_codes"] == [1]
    assert not tuple((tmp_path / "runs").glob("g39-*"))


def test_evidence_path_must_stay_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        startup_baseline.validate_output_path(
            ROOT / "startup-baseline.json",
            ROOT,
        )

    destination = startup_baseline.validate_output_path(
        tmp_path / "startup-baseline.json",
        ROOT,
    )

    assert destination == (tmp_path / "startup-baseline.json").resolve()


def test_baseline_summarizes_lazy_and_materialized_gui_samples(
    tmp_path: Path,
) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=("gui-lazy", "gui-materialized"),
        sample_runner=_sample,
    )

    assert report["roles"]["gui-lazy"]["gui"]["materialized_workspaces"][
        "p50"
    ] == 0
    assert report["roles"]["gui-materialized"]["gui"][
        "loaded_deferred_modules"
    ]["p50"] == 3


def test_baseline_summarizes_foreground_and_background_idle_samples(
    tmp_path: Path,
) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=("gui-foreground-idle", "gui-background-idle"),
        sample_runner=_sample,
    )

    foreground = report["roles"]["gui-foreground-idle"]
    background = report["roles"]["gui-background-idle"]
    assert foreground["idle_observation"]["background_idle"]["p50"] == 0
    assert background["idle_observation"]["background_idle"]["p50"] == 1
    assert background["idle_observation"]["window_visible"]["p50"] == 0
    assert background["idle_observation"]["suspended_timers"]["p50"] == 2
    assert background["idle_observation"]["observation_cpu_time_ms"]["p50"] == 1.0
    assert report["workload"]["idle_observation_seconds"] == 5.0


def test_baseline_summarizes_materialized_background_idle_samples(
    tmp_path: Path,
) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=(
            "gui-materialized-foreground-idle",
            "gui-materialized-background-idle",
        ),
        sample_runner=_sample,
    )

    foreground = report["roles"]["gui-materialized-foreground-idle"]
    background = report["roles"]["gui-materialized-background-idle"]
    assert foreground["gui"]["materialized_workspaces"]["p50"] == 3
    assert background["gui"]["materialized_workspaces"]["p50"] == 3
    assert background["idle_observation"]["background_idle"]["p50"] == 1
    assert background["idle_observation"]["window_visible"]["p50"] == 0


def test_probe_uses_the_real_application_entry_for_path_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main

    captured: list[str] = []
    monkeypatch.setattr(
        startup_baseline,
        "_install_network_guard",
        lambda: [],
    )
    monkeypatch.setattr(
        startup_baseline,
        "_windows_process_metrics",
        lambda: {"status": "unsupported"},
    )
    monkeypatch.setattr(
        main,
        "main",
        lambda _arguments: captured.append(sys.argv[0]) or 0,
    )

    assert startup_baseline._run_probe("version", ROOT, tmp_path) == 0
    assert captured == [str(ROOT / "main.py")]


def test_baseline_summarizes_table_rebuild_and_reuse_samples(
    tmp_path: Path,
) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=("table-rebuild", "table-reuse"),
        sample_runner=_sample,
    )

    assert report["roles"]["table-rebuild"]["table"]["item_allocations"][
        "p50"
    ] == 40_000
    assert report["roles"]["table-reuse"]["table"][
        "progress_allocations"
    ]["p50"] == 200


def test_baseline_summarizes_bounded_search_result_samples(
    tmp_path: Path,
) -> None:
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=("search-results",),
        sample_runner=_sample,
    )

    search = report["roles"]["search-results"]["search_results"]
    assert search["rendered_rows"]["p50"] == 200
    assert search["initial_thumbnail_requests"]["p50"] == 12
    assert search["total_thumbnail_requests"]["p50"] == 24
    assert search["search_cpu_time_ms"]["p50"] == 15.625
    assert search["live_process"]["private_bytes"]["p50"] == 70_000_000
    assert report["workload"]["search_result_rows"] == 200


def test_baseline_covers_each_trusted_search_result_surface(
    tmp_path: Path,
) -> None:
    roles = (
        "search-results",
        "youtube-results",
        "bilibili-results",
    )
    report = startup_baseline.run_baseline(
        repository_root=ROOT,
        temp_root=tmp_path / "runs",
        warmups=0,
        iterations=1,
        roles=roles,
        sample_runner=_sample,
    )

    assert report["schema_version"] == 4
    for role in roles:
        search = report["roles"][role]["search_results"]
        assert search["rendered_rows"]["p50"] == 200
        assert search["initial_thumbnail_requests"]["p50"] == 12
        assert search["total_thumbnail_requests"]["p50"] == 24
