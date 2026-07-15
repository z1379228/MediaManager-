from __future__ import annotations

from core.dependency_health import DependencyReport, DependencyStatus
from trusted_ui.dependency_dialog import (
    dependency_presentation,
    startup_dependency_prompt_required,
)


def _report(available: tuple[bool, ...]) -> DependencyReport:
    dependency_ids = (
        "yt-dlp",
        "yt-dlp-ejs",
        "ffmpeg",
        "javascript-runtime",
    )
    return DependencyReport(
        tuple(
            DependencyStatus(dependency_id, dependency_id, ready, "", "", "")
            for dependency_id, ready in zip(dependency_ids, available, strict=True)
        )
    )


def test_dependency_badge_is_compact_and_explicit() -> None:
    assert dependency_presentation(_report((True, True, True, True))) == (
        "核心 4/4",
        "ready",
        "核心下載環境已就緒；MEGAcmd、whisper-cli 與語音模型依使用的 MOD 選裝。",
    )
    assert dependency_presentation(_report((True, False, True, False))) == (
        "核心 2/4",
        "warning",
        "缺少 2 項核心依賴，請開啟環境檢查。",
    )


def test_dependency_badge_separates_optional_mod_tools() -> None:
    statuses = _report((True, True, True, True)).statuses + (
        DependencyStatus("mega-get", "MEGAcmd", False, "", "", ""),
        DependencyStatus("whisper-cli", "whisper-cli", False, "", "", ""),
        DependencyStatus("speech-model", "Speech model", False, "", "", ""),
    )
    assert dependency_presentation(DependencyReport(statuses))[0] == (
        "核心 4/4｜選用 0/3"
    )


def test_startup_dependency_prompt_only_appears_for_incomplete_support() -> None:
    assert not startup_dependency_prompt_required(_report((True, True, True, True)))
    assert startup_dependency_prompt_required(_report((True, False, True, True)))
