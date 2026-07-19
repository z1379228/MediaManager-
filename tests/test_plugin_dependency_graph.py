from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from core.plugins.dependency_graph import (
    MAX_MANIFEST_BYTES,
    DependencyGraphIssue,
    DependencyGraphIssueCode,
    snapshot_dependency_graph,
)
from core.plugins.manifest import PluginManifest
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry


def _manifest(
    plugin_id: str,
    dependencies: tuple[str, ...] = (),
    *,
    version: str = "1.0.0",
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "id": plugin_id,
        "name": plugin_id,
        "version": version,
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": "99.0.0",
        "permissions": [],
        "external_tools": [],
        "dependencies": list(dependencies),
        "files_manifest": "files.json",
        "signature": "plugin.sig",
        "runtime": "python-subprocess",
        "runtime_protocol": "1.0",
        "ui_descriptor": "",
    }


def _install_manifest(
    mod_root: Path,
    registry: PluginRegistry,
    plugin_id: str,
    dependencies: tuple[str, ...] = (),
    *,
    manifest_id: str | None = None,
) -> Path:
    root = mod_root / "installed" / plugin_id
    root.mkdir(parents=True)
    manifest_bytes = json.dumps(
        _manifest(manifest_id or plugin_id, dependencies),
        sort_keys=True,
    ).encode("utf-8")
    manifest_path = root / "plugin.json"
    manifest_path.write_bytes(manifest_bytes)
    registry.upsert(
        PluginRecord(
            plugin_id,
            "1.0.0",
            False,
            PendingAction.NONE,
            "TRUSTED_PUBLISHER",
            "trusted.example",
            (),
            hashlib.sha256(manifest_bytes).hexdigest(),
        )
    )
    return manifest_path


def test_dependency_order_is_stable_and_dependency_first(tmp_path: Path) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(mod_root, registry, "alpha.plugin", ("beta.plugin",))
    _install_manifest(mod_root, registry, "beta.plugin")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert snapshot.valid
    assert snapshot.issues == ()
    assert snapshot.dependency_order == ("beta.plugin", "alpha.plugin")
    registry.close()


def test_snapshot_exposes_stable_transitive_dependency_closure(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(
        mod_root,
        registry,
        "alpha.plugin",
        ("beta.plugin", "delta.plugin"),
    )
    _install_manifest(mod_root, registry, "beta.plugin", ("gamma.plugin",))
    _install_manifest(mod_root, registry, "delta.plugin", ("gamma.plugin",))
    _install_manifest(mod_root, registry, "gamma.plugin")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert snapshot.transitive_dependencies("alpha.plugin") == (
        "gamma.plugin",
        "beta.plugin",
        "delta.plugin",
    )
    assert snapshot.transitive_dependencies("gamma.plugin") == ()
    registry.close()


def test_snapshot_exposes_stable_transitive_dependent_closure(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(
        mod_root,
        registry,
        "alpha.plugin",
        ("beta.plugin", "delta.plugin"),
    )
    _install_manifest(mod_root, registry, "beta.plugin", ("gamma.plugin",))
    _install_manifest(mod_root, registry, "delta.plugin", ("gamma.plugin",))
    _install_manifest(mod_root, registry, "gamma.plugin")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert snapshot.transitive_dependents("gamma.plugin") == (
        "alpha.plugin",
        "beta.plugin",
        "delta.plugin",
    )
    assert snapshot.transitive_dependents("alpha.plugin") == ()
    registry.close()


def test_snapshot_rejects_installed_root_escape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mod_root = tmp_path / "mod"
    outside = tmp_path / "outside"
    outside.mkdir()
    installed_root = mod_root / "installed"
    mod_root.mkdir()
    try:
        installed_root.symlink_to(outside, target_is_directory=True)
    except OSError:
        original_resolve = Path.resolve

        def resolve_with_escape(path: Path, *args, **kwargs) -> Path:
            if path == installed_root:
                return outside
            return original_resolve(path, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", resolve_with_escape)
    registry = PluginRegistry(mod_root / "registry.sqlite3")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.nodes == ()
    assert snapshot.issues == (
        DependencyGraphIssue(DependencyGraphIssueCode.MOD_ROOT_UNREADABLE),
    )
    registry.close()


def test_snapshot_rejects_missing_dependency_with_stable_issue(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(
        mod_root,
        registry,
        "alpha.plugin",
        ("zeta.plugin", "missing.plugin"),
    )

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MISSING_DEPENDENCY,
            "alpha.plugin",
            ("missing.plugin", "zeta.plugin"),
        ),
    )
    assert snapshot.dependency_order == ()
    registry.close()


def test_snapshot_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    manifest_path = _install_manifest(mod_root, registry, "alpha.plugin")
    manifest_path.write_text("{}", encoding="utf-8")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MANIFEST_TAMPERED,
            "alpha.plugin",
        ),
    )
    registry.close()


def test_snapshot_rejects_manifest_above_hard_read_limit(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    manifest_path = _install_manifest(mod_root, registry, "alpha.plugin")
    manifest_path.write_bytes(b"x" * (MAX_MANIFEST_BYTES + 1))

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MANIFEST_TOO_LARGE,
            "alpha.plugin",
        ),
    )
    registry.close()


def test_snapshot_rejects_invalid_manifest_with_stable_issue(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    manifest_path = _install_manifest(mod_root, registry, "alpha.plugin")
    invalid_manifest = b"{"
    manifest_path.write_bytes(invalid_manifest)
    record = registry.get("alpha.plugin")
    assert record is not None
    registry.upsert(
        replace(
            record,
            manifest_hash=hashlib.sha256(invalid_manifest).hexdigest(),
        )
    )

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MANIFEST_INVALID,
            "alpha.plugin",
        ),
    )
    registry.close()


def test_snapshot_rejects_manifest_identity_mismatch(tmp_path: Path) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(
        mod_root,
        registry,
        "alpha.plugin",
        manifest_id="different.plugin",
    )

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MANIFEST_IDENTITY_MISMATCH,
            "alpha.plugin",
        ),
    )
    registry.close()


def test_candidate_preserves_source_integrity_issue_and_registry_state(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    manifest_path = _install_manifest(mod_root, registry, "alpha.plugin")
    manifest_path.write_text("{}", encoding="utf-8")
    record = registry.get("alpha.plugin")
    assert record is not None
    registry.upsert(
        replace(
            record,
            enabled=True,
            pending_action=PendingAction.UPDATE,
        )
    )
    baseline = snapshot_dependency_graph(mod_root, registry)
    candidate = PluginManifest.from_dict(
        _manifest("alpha.plugin", version="1.1.0")
    )

    overlay = baseline.with_candidate(candidate)

    assert not baseline.valid
    assert not overlay.valid
    assert overlay.issues == baseline.issues
    assert overlay.nodes == (
        replace(
            baseline.nodes[0],
            version="1.1.0",
            enabled=True,
            pending_action=PendingAction.UPDATE,
            candidate=True,
        ),
    )
    registry.close()


def test_verified_recovery_overlay_only_replaces_named_source_issues(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    alpha_manifest = _install_manifest(mod_root, registry, "alpha.plugin")
    beta_manifest = _install_manifest(mod_root, registry, "beta.plugin")
    alpha_manifest.write_text("{}", encoding="utf-8")
    beta_manifest.write_text("{}", encoding="utf-8")
    baseline = snapshot_dependency_graph(mod_root, registry)
    verified_alpha = PluginManifest.from_dict(_manifest("alpha.plugin"))

    overlay = baseline.with_verified_recovery_candidates((verified_alpha,))

    assert not baseline.valid
    assert not overlay.valid
    assert overlay.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MANIFEST_TAMPERED,
            "beta.plugin",
        ),
    )
    assert next(
        node for node in overlay.nodes if node.plugin_id == "alpha.plugin"
    ).candidate
    registry.close()


def test_removed_tombstones_do_not_consume_graph_node_limit(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    for index in range(512):
        registry.upsert(
            PluginRecord(
                f"tombstone{index:03d}.plugin",
                "1.0.0",
                False,
                PendingAction.REMOVE,
                "TRUSTED_PUBLISHER",
                "trusted.example",
                (),
                "0" * 64,
            )
        )
    _install_manifest(mod_root, registry, "alpha.plugin")

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert snapshot.valid
    assert tuple(node.plugin_id for node in snapshot.nodes) == ("alpha.plugin",)
    registry.close()


def test_candidate_overlay_rejects_indirect_cycle_without_mutating_snapshot(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(mod_root, registry, "alpha.plugin", ("beta.plugin",))
    _install_manifest(mod_root, registry, "beta.plugin", ("gamma.plugin",))
    _install_manifest(mod_root, registry, "gamma.plugin")
    baseline = snapshot_dependency_graph(mod_root, registry)
    candidate = PluginManifest.from_dict(
        _manifest("gamma.plugin", ("alpha.plugin",), version="1.1.0")
    )

    overlay = baseline.with_candidate(candidate)

    assert baseline.valid
    assert baseline.dependency_order == (
        "gamma.plugin",
        "beta.plugin",
        "alpha.plugin",
    )
    assert not overlay.valid
    assert overlay.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.DEPENDENCY_CYCLE,
            "alpha.plugin",
            ("alpha.plugin", "beta.plugin", "gamma.plugin"),
        ),
    )
    assert overlay.dependency_order == ()
    assert registry.get("gamma.plugin").installed_version == "1.0.0"
    registry.close()


def test_removed_dependency_is_excluded_and_dependents_fail_closed(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    _install_manifest(mod_root, registry, "alpha.plugin", ("beta.plugin",))
    _install_manifest(mod_root, registry, "beta.plugin")
    removed = registry.get("beta.plugin")
    assert removed is not None
    registry.upsert(replace(removed, pending_action=PendingAction.REMOVE))

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.MISSING_DEPENDENCY,
            "alpha.plugin",
            ("beta.plugin",),
        ),
    )
    assert tuple(node.plugin_id for node in snapshot.nodes) == ("alpha.plugin",)
    registry.close()


def test_dependency_fanout_is_bounded_before_missing_node_expansion(
    tmp_path: Path,
) -> None:
    mod_root = tmp_path / "mod"
    registry = PluginRegistry(mod_root / "registry.sqlite3")
    dependencies = tuple(f"dep{index:02d}.plugin" for index in range(65))
    _install_manifest(mod_root, registry, "alpha.plugin", dependencies)

    snapshot = snapshot_dependency_graph(mod_root, registry)

    assert not snapshot.valid
    assert snapshot.issues == (
        DependencyGraphIssue(
            DependencyGraphIssueCode.TOO_MANY_DEPENDENCIES,
            "alpha.plugin",
        ),
    )
    registry.close()
