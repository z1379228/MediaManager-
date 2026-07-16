from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.builtin_mod_catalog import builtin_mod_ids
from core.dependency_health import DependencyReport
from core.dependency_snapshot import DependencySnapshot, FeatureReadiness
from core.downloads.provider_registry import ProviderStatus
from core.security.safe_mode import SafeMode
from core.self_check import load_provider_smoke_report, run_self_check


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
        settings=SimpleNamespace(language="zh-TW"),
        plugin_ui=SimpleNamespace(locale="zh-TW"),
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
    assert next(
        item for item in report.items if item.check_id == "transport.boundary"
    ).state == "pass"
    assert next(
        item for item in report.items if item.check_id == "downloads.queue"
    ).state == "warning"
    assert next(
        item for item in report.items if item.check_id == "localization.binding"
    ).state == "pass"
    assert next(
        item for item in report.items if item.check_id == "routing.site_matrix"
    ).state == "pass"
    assert next(
        item for item in report.items if item.check_id == "site.capability_matrix"
    ).state == "pass"
    assert next(
        item for item in report.items if item.check_id == "smoke.latest"
    ).state == "warning"


def test_self_check_imports_bounded_manual_provider_smoke(tmp_path: Path) -> None:
    path = tmp_path / "provider-smoke.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mode": "live-public-content",
                "generated_at": "2026-07-16T07:54:27+00:00",
                "status": "PASS",
                "summary": {"passed": 2, "failed": 0, "temporary_upstream": 0},
                "cases": [{"status": "PASS"}, {"status": "PASS"}],
            }
        ),
        encoding="utf-8",
    )

    item = load_provider_smoke_report(path)
    report = run_self_check(context(tmp_path), smoke_item=item)

    assert item.state == "pass"
    assert "通過 2" in item.detail
    assert next(
        value for value in report.items if value.check_id == "smoke.latest"
    ) == item


def test_self_check_rejects_inconsistent_manual_provider_smoke(tmp_path: Path) -> None:
    path = tmp_path / "provider-smoke.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mode": "live-public-content",
                "generated_at": "2026-07-16T07:54:27+00:00",
                "status": "PASS",
                "summary": {"passed": 7, "failed": 0, "temporary_upstream": 0},
                "cases": [],
            }
        ),
        encoding="utf-8",
    )

    item = load_provider_smoke_report(path)

    assert item.state == "block"
    assert item.remediation_id == "smoke.report.replace"


def test_self_check_reports_warm_download_queue_without_starting_work(
    tmp_path: Path,
) -> None:
    value = context(tmp_path)
    value.download_queue = SimpleNamespace(
        snapshots=lambda: (
            SimpleNamespace(state="paused"),
            SimpleNamespace(state=SimpleNamespace(value="queued")),
        )
    )

    report = run_self_check(value)

    item = next(item for item in report.items if item.check_id == "downloads.queue")
    assert item.state == "pass"
    assert "paused=1" in item.detail
    assert "queued=1" in item.detail


def test_self_check_uses_queue_state_counts_when_available(tmp_path: Path) -> None:
    value = context(tmp_path)
    value.download_queue = SimpleNamespace(
        snapshots=lambda: (_ for _ in ()).throw(
            AssertionError("state_counts should be preferred")
        ),
        state_counts=lambda: {"QUEUED": 2, "PAUSED": 1},
    )

    report = run_self_check(value)

    item = next(item for item in report.items if item.check_id == "downloads.queue")
    assert item.state == "pass"
    assert "QUEUED=2" in item.detail
    assert "PAUSED=1" in item.detail


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


def test_self_check_blocks_enabled_children_of_disabled_parent(tmp_path: Path) -> None:
    value = context(tmp_path)
    value.download_providers = SimpleNamespace(
        statuses=lambda: tuple(
            ProviderStatus(provider_id, provider_id, provider_id != "youtube")
            for provider_id in sorted(builtin_mod_ids("download"))
        )
    )

    report = run_self_check(value)

    state = next(item for item in report.items if item.check_id == "state.parent_child")
    assert state.state == "block"
    assert "youtube-search" in state.detail


def test_self_check_blocks_core_and_mod_locale_mismatch(tmp_path: Path) -> None:
    value = context(tmp_path)
    value.plugin_ui.locale = "en"

    report = run_self_check(value)

    locale = next(
        item for item in report.items if item.check_id == "localization.binding"
    )
    assert locale.state == "block"
    assert locale.remediation_id == "localization.binding.repair"


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
        assert panel.table.columnCount() == 5
        assert panel.findChild(QPushButton, "importProviderSmoke") is not None
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_self_check_probes_actual_mod_management_tree(tmp_path: Path, monkeypatch) -> None:
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton, QTabWidget

    from core.bootstrap.bootstrap import Bootstrap
    from core.storage.paths import AppPaths
    from trusted_ui.plugin_manager import create_plugin_manager_dialog

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    monkeypatch.setattr(AppPaths, "discover", lambda **_: paths)
    app = QApplication.instance() or QApplication([])
    context_value = Bootstrap(portable=True).initialize()
    dialog = create_plugin_manager_dialog(context_value)
    try:
        tabs = dialog.findChild(QTabWidget, "pluginManagerTabs")
        panel = tabs.widget(6)
        panel.findChild(QPushButton, "runSelfCheck").click()
        app.processEvents()

        item = next(
            item
            for item in panel.report.items
            if item.check_id == "ui.mod_management"
        )
        assert panel.report.block_count == 0
        assert item.state == "pass"
        assert "啟用按鈕" in item.detail
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        context_value.lifecycle.shutdown()
