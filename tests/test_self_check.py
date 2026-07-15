from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.builtin_mod_catalog import builtin_mod_ids
from core.dependency_health import DependencyReport
from core.dependency_snapshot import DependencySnapshot, FeatureReadiness
from core.downloads.provider_registry import ProviderStatus
from core.security.safe_mode import SafeMode
from core.self_check import run_self_check


class Registry:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    def statuses(self) -> tuple[ProviderStatus, ...]:
        return tuple(
            ProviderStatus(provider_id, provider_id, True)
            for provider_id in sorted(builtin_mod_ids(self.kind))  # type: ignore[arg-type]
        )


class Dependencies:
    def __init__(self, snapshot: DependencySnapshot | None = None) -> None:
        self.value = snapshot
        self.peek_calls = 0

    def peek(self) -> DependencySnapshot | None:
        self.peek_calls += 1
        return self.value

    def refresh(self) -> None:
        raise AssertionError("self-check must not refresh dependencies")


def context(root: Path, dependencies: Dependencies | None = None) -> object:
    security = SafeMode()
    security.enter_safe_mode("development")
    return SimpleNamespace(
        download_providers=Registry("download"),
        discovery=Registry("discovery"),
        features=Registry("feature"),
        builtin_mod_errors={},
        dependencies=dependencies or Dependencies(),
        security=security,
        paths=SimpleNamespace(application=root),
    )


def test_self_check_is_manual_read_only_and_uses_only_warm_snapshot(
    tmp_path: Path,
) -> None:
    dependencies = Dependencies()
    report = run_self_check(context(tmp_path, dependencies))

    assert dependencies.peek_calls == 1
    assert report.block_count == 0
    assert any(item.check_id == "dependencies.snapshot" for item in report.items)
    assert any(item.check_id == "security.mode" for item in report.items)


def test_self_check_blocks_missing_registry_and_builtin_initialization(
    tmp_path: Path,
) -> None:
    value = context(tmp_path)
    value.download_providers = SimpleNamespace(statuses=lambda: ())
    value.builtin_mod_errors = {"youtube": "local absolute path is not exported"}

    report = run_self_check(value)

    assert report.block_count == 2
    assert {item.check_id for item in report.items if item.state == "block"} == {
        "registry.download",
        "builtin.initialization",
    }


def test_self_check_export_is_deidentified(tmp_path: Path) -> None:
    readiness = tuple(
        FeatureReadiness(provider_id, True, ())
        for kind in ("download", "discovery", "feature")
        for provider_id in sorted(builtin_mod_ids(kind))  # type: ignore[arg-type]
    )
    dependencies = Dependencies(
        DependencySnapshot(DependencyReport(()), readiness, "test-fingerprint")
    )
    report = run_self_check(context(tmp_path, dependencies))
    document = json.loads(report.to_json())

    assert document["schema_version"] == 1
    assert str(tmp_path) not in report.to_json()
    assert "test-fingerprint" not in report.to_json()
    assert set(document["summary"]) == {"pass", "warning", "block"}


def test_self_check_plugin_page_does_not_run_until_button_click(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton
    from trusted_ui.self_check_panel import create_self_check_panel

    dependencies = Dependencies()
    app = QApplication.instance() or QApplication([])
    panel = create_self_check_panel(context(tmp_path, dependencies))
    try:
        assert dependencies.peek_calls == 0
        button = panel.findChild(QPushButton, "runSelfCheck")
        button.click()
        app.processEvents()
        assert dependencies.peek_calls == 1
        assert panel.report is not None
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
