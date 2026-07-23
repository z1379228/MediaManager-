from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from core.settings import Settings, SettingsService
from trusted_ui import initial_mod_setup
from trusted_ui.initial_mod_setup import (
    complete_initial_mod_setup,
    initial_mod_selection_is_pristine,
    initial_mod_setup_required,
    initial_mod_setup_preserve_reasons,
    mark_initial_mod_setup_complete,
    ordered_selection_ids,
)
from trusted_ui.builtin_mod_panel import BuiltinModRow


def _pristine_runtime(tmp_path: Path) -> dict[str, object]:
    return {
        "settings_load": SimpleNamespace(state="missing"),
        "paths": SimpleNamespace(
            settings=tmp_path / "settings",
            mod=tmp_path / "mod",
            data=tmp_path / "data",
        ),
        "download_queue": SimpleNamespace(snapshots=lambda: ()),
        "conversion": None,
        "transcription": None,
    }


def test_initial_mod_setup_is_one_time_and_persisted(tmp_path: Path) -> None:
    settings = Settings()
    assert initial_mod_setup_required(settings)
    context = SimpleNamespace(
        settings=settings,
        paths=SimpleNamespace(settings=tmp_path / "settings"),
    )

    mark_initial_mod_setup_complete(context)

    assert not initial_mod_setup_required(settings)
    assert SettingsService(tmp_path / "settings" / "settings.json").load().initial_mod_setup_completed


def test_initial_mod_setup_orders_parents_before_children() -> None:
    rows = (
        BuiltinModRow("youtube-search", "Search", "", "", True, False, parent_provider_id="youtube"),
        BuiltinModRow("youtube", "YouTube", "", "", True, False),
        BuiltinModRow("mega", "MEGA", "", "", True, False),
    )

    assert ordered_selection_ids(rows) == ("youtube", "mega", "youtube-search")


def test_initial_mod_setup_stays_incomplete_after_partial_apply_failure(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    rows = (
        BuiltinModRow("youtube", "YouTube", "", "", True, False),
        BuiltinModRow("mega", "MEGA", "", "", True, False),
    )
    states = {"youtube": False, "mega": False}
    context = SimpleNamespace(
        settings=settings,
        **_pristine_runtime(tmp_path),
        download_providers=SimpleNamespace(
            statuses=lambda: tuple(
                SimpleNamespace(provider_id=provider_id, enabled=enabled)
                for provider_id, enabled in states.items()
            )
        ),
        discovery=SimpleNamespace(statuses=lambda: ()),
        features=SimpleNamespace(statuses=lambda: ()),
    )
    attempted: list[tuple[str, bool]] = []

    def change_provider(_context: object, provider_id: str, enabled: bool) -> int:
        attempted.append((provider_id, enabled))
        states[provider_id] = enabled
        if provider_id == "mega" and enabled:
            raise RuntimeError("deterministic apply failure")
        return 0

    monkeypatch.setattr(
        initial_mod_setup,
        "set_builtin_mod_enabled",
        change_provider,
    )

    completed = complete_initial_mod_setup(
        context,
        {"youtube", "mega"},
        rows,
        apply_selection=True,
    )

    assert attempted == [
        ("youtube", True),
        ("mega", True),
        ("mega", False),
        ("youtube", False),
    ]
    assert states == {"youtube": False, "mega": False}
    assert not completed
    assert initial_mod_setup_required(settings)
    assert not (tmp_path / "settings" / "settings.json").exists()


def test_initial_mod_setup_restores_completion_when_save_fails(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    context = SimpleNamespace(
        settings=settings,
        paths=SimpleNamespace(settings=tmp_path / "settings"),
    )

    def fail_patch(_service: SettingsService, **_changes: object) -> Settings:
        raise OSError("deterministic save failure")

    monkeypatch.setattr(SettingsService, "patch", fail_patch)

    completed = complete_initial_mod_setup(
        context,
        set(),
        (),
        apply_selection=False,
    )

    assert not completed
    assert initial_mod_setup_required(settings)


def test_initial_mod_setup_restores_mod_states_when_completion_save_fails(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    states = {"youtube": False, "mega": False}
    rows = (
        BuiltinModRow("youtube", "YouTube", "", "", True, False),
        BuiltinModRow("mega", "MEGA", "", "", True, False),
    )
    context = SimpleNamespace(
        settings=settings,
        **_pristine_runtime(tmp_path),
        download_providers=SimpleNamespace(
            statuses=lambda: tuple(
                SimpleNamespace(provider_id=provider_id, enabled=enabled)
                for provider_id, enabled in states.items()
            )
        ),
        discovery=SimpleNamespace(statuses=lambda: ()),
        features=SimpleNamespace(statuses=lambda: ()),
    )
    changes: list[tuple[str, bool]] = []

    def change_provider(_context: object, provider_id: str, enabled: bool) -> int:
        states[provider_id] = enabled
        changes.append((provider_id, enabled))
        return 0

    def fail_patch(_service: SettingsService, **_changes: object) -> Settings:
        raise OSError("deterministic save failure")

    monkeypatch.setattr(initial_mod_setup, "set_builtin_mod_enabled", change_provider)
    monkeypatch.setattr(SettingsService, "patch", fail_patch)

    completed = complete_initial_mod_setup(
        context,
        {"youtube", "mega"},
        rows,
        apply_selection=True,
    )

    assert not completed
    assert states == {"youtube": False, "mega": False}
    assert changes == [
        ("youtube", True),
        ("mega", True),
        ("mega", False),
        ("youtube", False),
    ]
    assert initial_mod_setup_required(settings)


def test_initial_mod_setup_audits_irreversible_cancellation_on_save_failure(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    states = {"youtube": True}
    rows = (BuiltinModRow("youtube", "YouTube", "", "", True, True),)
    audit = Mock()
    context = SimpleNamespace(
        settings=settings,
        **_pristine_runtime(tmp_path),
        download_providers=SimpleNamespace(
            statuses=lambda: tuple(
                SimpleNamespace(provider_id=provider_id, enabled=enabled)
                for provider_id, enabled in states.items()
            )
        ),
        discovery=SimpleNamespace(statuses=lambda: ()),
        features=SimpleNamespace(statuses=lambda: ()),
        audit=audit,
    )

    def change_provider(_context: object, provider_id: str, enabled: bool) -> int:
        states[provider_id] = enabled
        return 2 if not enabled else 0

    def fail_patch(_service: SettingsService, **_changes: object) -> Settings:
        raise OSError("deterministic save failure")

    monkeypatch.setattr(initial_mod_setup, "set_builtin_mod_enabled", change_provider)
    monkeypatch.setattr(SettingsService, "patch", fail_patch)

    assert not complete_initial_mod_setup(
        context,
        set(),
        rows,
        apply_selection=True,
    )

    assert states == {"youtube": True}
    audit.write.assert_any_call(
        "builtin_mod.initial_setup_rollback_incomplete",
        cancelled_work=2,
        failed_provider_ids=(),
    )


def test_existing_settings_preserve_mod_states_without_toggles(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    audit = Mock()
    context = SimpleNamespace(
        settings=settings,
        settings_load=SimpleNamespace(state="legacy"),
        paths=SimpleNamespace(
            settings=tmp_path / "settings",
            mod=tmp_path / "mod",
            data=tmp_path / "data",
        ),
        download_queue=SimpleNamespace(snapshots=lambda: ()),
        conversion=None,
        transcription=None,
        audit=audit,
    )
    toggle = Mock(side_effect=AssertionError("must preserve existing states"))
    monkeypatch.setattr(initial_mod_setup, "set_builtin_mod_enabled", toggle)

    assert complete_initial_mod_setup(
        context,
        set(),
        (BuiltinModRow("youtube", "YouTube", "", "", True, True),),
        apply_selection=True,
    )

    toggle.assert_not_called()
    assert settings.initial_mod_setup_completed
    audit.write.assert_any_call(
        "builtin_mod.initial_setup_existing_state_preserved",
        reason_codes=("settings_not_missing",),
    )


def test_missing_settings_with_existing_queue_fails_closed(
    tmp_path: Path,
) -> None:
    runtime = _pristine_runtime(tmp_path)
    runtime["download_queue"] = SimpleNamespace(
        snapshots=lambda: (SimpleNamespace(task_id="existing"),)
    )
    context = SimpleNamespace(settings=Settings(), **runtime)

    assert not initial_mod_selection_is_pristine(context)
    assert initial_mod_setup_preserve_reasons(context) == (
        "download_work_present",
    )


def test_missing_settings_with_feature_work_fails_closed(tmp_path: Path) -> None:
    runtime = _pristine_runtime(tmp_path)
    runtime["conversion"] = SimpleNamespace(
        snapshots=lambda: (SimpleNamespace(task_id="existing"),)
    )
    context = SimpleNamespace(settings=Settings(), **runtime)

    assert not initial_mod_selection_is_pristine(context)
    assert initial_mod_setup_preserve_reasons(context) == (
        "conversion_work_present",
    )


def test_missing_settings_with_mod_state_marker_fails_closed(
    tmp_path: Path,
) -> None:
    runtime = _pristine_runtime(tmp_path)
    marker = runtime["paths"].mod / "provider-state.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}", encoding="utf-8")
    context = SimpleNamespace(settings=Settings(), **runtime)

    assert not initial_mod_selection_is_pristine(context)
    assert "durable_state_present" in initial_mod_setup_preserve_reasons(context)


def test_unknown_settings_origin_fails_closed(tmp_path: Path) -> None:
    runtime = _pristine_runtime(tmp_path)
    runtime.pop("settings_load")
    context = SimpleNamespace(settings=Settings(), **runtime)

    assert not initial_mod_selection_is_pristine(context)
    assert "settings_not_missing" in initial_mod_setup_preserve_reasons(context)


def test_existing_state_save_failure_never_toggles_or_cancels(
    tmp_path: Path, monkeypatch,
) -> None:
    settings = Settings()
    toggle = Mock(side_effect=AssertionError("must not toggle"))
    cancel = Mock(side_effect=AssertionError("must not cancel"))
    context = SimpleNamespace(
        settings=settings,
        settings_load=SimpleNamespace(state="current"),
        paths=SimpleNamespace(
            settings=tmp_path / "settings",
            mod=tmp_path / "mod",
            data=tmp_path / "data",
        ),
        download_queue=SimpleNamespace(snapshots=lambda: (), cancel=cancel),
        conversion=None,
        transcription=None,
    )

    def fail_patch(_service: SettingsService, **_changes: object) -> Settings:
        raise OSError("deterministic save failure")

    monkeypatch.setattr(initial_mod_setup, "set_builtin_mod_enabled", toggle)
    monkeypatch.setattr(SettingsService, "patch", fail_patch)

    assert not complete_initial_mod_setup(
        context,
        set(),
        (BuiltinModRow("youtube", "YouTube", "", "", True, True),),
        apply_selection=True,
    )
    assert not settings.initial_mod_setup_completed
    toggle.assert_not_called()
    cancel.assert_not_called()
