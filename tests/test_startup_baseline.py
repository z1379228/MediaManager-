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
        sample.update(
            qt_objects=10,
            active_repeat_timers=1,
            tabs=4,
            materialized_workspaces=(
                0 if role == "gui-lazy" else 3
            ),
            loaded_deferred_modules=(
                0 if role == "gui-lazy" else 3
            ),
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
