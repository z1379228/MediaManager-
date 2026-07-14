from __future__ import annotations

from core.dependency_health import DependencyReport, DependencyStatus
from trusted_ui.dependency_dialog import (
    dependency_presentation,
    startup_dependency_prompt_required,
)


def _report(available: tuple[bool, ...]) -> DependencyReport:
    return DependencyReport(
        tuple(
            DependencyStatus(str(index), str(index), ready, "", "", "")
            for index, ready in enumerate(available)
        )
    )


def test_dependency_badge_is_compact_and_explicit() -> None:
    assert dependency_presentation(_report((True, True, True, True))) == (
        "環境 4/4",
        "ready",
        "YouTube 完整支援所需元件均可用",
    )
    assert dependency_presentation(_report((True, False, True, False))) == (
        "環境 2/4",
        "warning",
        "有 2 個元件需要處理",
    )


def test_startup_dependency_prompt_only_appears_for_incomplete_support() -> None:
    assert not startup_dependency_prompt_required(_report((True, True, True, True)))
    assert startup_dependency_prompt_required(_report((True, False, True, True)))
