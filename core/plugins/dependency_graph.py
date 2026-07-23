"""Read-only, bounded validation for installed plugin dependency graphs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from core.plugins.manifest import ManifestError, PluginManifest
from core.plugins.registry import PendingAction, PluginRecord, PluginRegistry

MAX_PLUGIN_NODES = 512
MAX_DEPENDENCIES_PER_PLUGIN = 64
MAX_MANIFEST_BYTES = 256 * 1024

_PLUGIN_ID = re.compile(r"^[a-z][a-z0-9.-]{1,63}$")


class _ManifestTooLargeError(Exception):
    """Signal a bounded manifest read without exposing filesystem details."""


class DependencyGraphIssueCode(StrEnum):
    REGISTRY_UNREADABLE = "registry_unreadable"
    MOD_ROOT_UNREADABLE = "mod_root_unreadable"
    GRAPH_TOO_LARGE = "graph_too_large"
    UNSAFE_PLUGIN_ID = "unsafe_plugin_id"
    MANIFEST_MISSING = "manifest_missing"
    MANIFEST_TOO_LARGE = "manifest_too_large"
    MANIFEST_TAMPERED = "manifest_tampered"
    MANIFEST_INVALID = "manifest_invalid"
    MANIFEST_IDENTITY_MISMATCH = "manifest_identity_mismatch"
    TOO_MANY_DEPENDENCIES = "too_many_dependencies"
    MISSING_DEPENDENCY = "missing_dependency"
    DEPENDENCY_CYCLE = "dependency_cycle"


@dataclass(frozen=True, slots=True)
class DependencyGraphIssue:
    code: DependencyGraphIssueCode
    plugin_id: str = ""
    related_plugin_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DependencyGraphNode:
    plugin_id: str
    version: str
    dependencies: tuple[str, ...]
    enabled: bool
    pending_action: PendingAction
    candidate: bool = False


@dataclass(frozen=True, slots=True)
class DependencyGraphSnapshot:
    nodes: tuple[DependencyGraphNode, ...]
    issues: tuple[DependencyGraphIssue, ...]
    dependency_order: tuple[str, ...]
    _source_issues: tuple[DependencyGraphIssue, ...] = field(
        default=(), repr=False
    )

    @property
    def valid(self) -> bool:
        return not self.issues

    def transitive_dependencies(self, plugin_id: str) -> tuple[str, ...]:
        """Return the bounded dependency closure in dependency-first order."""

        by_id = {node.plugin_id: node for node in self.nodes}
        if plugin_id not in by_id:
            return ()
        visited: set[str] = set()
        pending = list(by_id[plugin_id].dependencies)
        while pending:
            dependency_id = pending.pop()
            if dependency_id in visited or dependency_id not in by_id:
                continue
            visited.add(dependency_id)
            pending.extend(by_id[dependency_id].dependencies)
        ordered = tuple(
            dependency_id
            for dependency_id in self.dependency_order
            if dependency_id in visited
        )
        return ordered if len(ordered) == len(visited) else tuple(sorted(visited))

    def transitive_dependents(self, plugin_id: str) -> tuple[str, ...]:
        """Return every reverse-reachable installed dependent, stably sorted."""

        by_id = {node.plugin_id: node for node in self.nodes}
        if plugin_id not in by_id:
            return ()
        reverse_edges: dict[str, list[str]] = {
            node_id: [] for node_id in by_id
        }
        for node in self.nodes:
            for dependency_id in node.dependencies:
                if dependency_id in reverse_edges:
                    reverse_edges[dependency_id].append(node.plugin_id)
        visited: set[str] = set()
        pending = list(reverse_edges[plugin_id])
        while pending:
            dependent_id = pending.pop()
            if dependent_id in visited:
                continue
            visited.add(dependent_id)
            pending.extend(reverse_edges[dependent_id])
        return tuple(sorted(visited))

    def with_candidate(
        self,
        manifest: PluginManifest,
    ) -> "DependencyGraphSnapshot":
        """Return an immutable single-node overlay without touching disk or SQLite."""

        nodes = {node.plugin_id: node for node in self.nodes}
        # A proposed manifest may model graph shape, but it cannot repair or
        # erase integrity failures observed in the installed source snapshot.
        source_issues = self._source_issues
        existing = nodes.get(manifest.id)
        if existing is None and len(nodes) >= MAX_PLUGIN_NODES:
            source_issues += (
                DependencyGraphIssue(
                    DependencyGraphIssueCode.GRAPH_TOO_LARGE,
                    manifest.id,
                ),
            )
            return _evaluate(tuple(nodes.values()), source_issues)

        dependencies = manifest.dependencies
        if len(dependencies) > MAX_DEPENDENCIES_PER_PLUGIN:
            source_issues += (
                DependencyGraphIssue(
                    DependencyGraphIssueCode.TOO_MANY_DEPENDENCIES,
                    manifest.id,
                ),
            )
            dependencies = ()
        nodes[manifest.id] = DependencyGraphNode(
            manifest.id,
            manifest.version,
            dependencies,
            existing.enabled if existing is not None else False,
            (
                existing.pending_action
                if existing is not None
                else PendingAction.NONE
            ),
            candidate=True,
        )
        return _evaluate(tuple(nodes.values()), source_issues)

    def with_verified_recovery_candidates(
        self,
        manifests: tuple[PluginManifest, ...],
    ) -> "DependencyGraphSnapshot":
        """Overlay exact registered recovery sources verified by the caller.

        Unlike a normal candidate, an interrupted transaction can make the
        installed directory disagree with the still-canonical registry row.
        Only source-integrity issues for the explicitly verified records are
        replaced; unrelated source failures remain fail-closed.
        """

        nodes = {node.plugin_id: node for node in self.nodes}
        candidate_ids = {manifest.id for manifest in manifests}
        source_issues = tuple(
            issue
            for issue in self._source_issues
            if issue.plugin_id not in candidate_ids
        )
        for manifest in manifests:
            existing = nodes.get(manifest.id)
            if existing is None and len(nodes) >= MAX_PLUGIN_NODES:
                source_issues += (
                    DependencyGraphIssue(
                        DependencyGraphIssueCode.GRAPH_TOO_LARGE,
                        manifest.id,
                    ),
                )
                continue
            dependencies = manifest.dependencies
            if len(dependencies) > MAX_DEPENDENCIES_PER_PLUGIN:
                source_issues += (
                    DependencyGraphIssue(
                        DependencyGraphIssueCode.TOO_MANY_DEPENDENCIES,
                        manifest.id,
                    ),
                )
                dependencies = ()
            nodes[manifest.id] = DependencyGraphNode(
                manifest.id,
                manifest.version,
                dependencies,
                existing.enabled if existing is not None else False,
                (
                    existing.pending_action
                    if existing is not None
                    else PendingAction.NONE
                ),
                candidate=True,
            )
        return _evaluate(tuple(nodes.values()), source_issues)


def snapshot_dependency_graph(
    mod_root: Path,
    registry: PluginRegistry,
) -> DependencyGraphSnapshot:
    """Read the installed graph once and return deterministic fail-closed results."""

    try:
        records = registry.list_dependency_records(limit=MAX_PLUGIN_NODES + 1)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        issue = DependencyGraphIssue(
            DependencyGraphIssueCode.REGISTRY_UNREADABLE
        )
        return _evaluate((), (issue,))
    if len(records) > MAX_PLUGIN_NODES:
        issue = DependencyGraphIssue(DependencyGraphIssueCode.GRAPH_TOO_LARGE)
        return _evaluate((), (issue,))

    try:
        resolved_mod_root = mod_root.resolve()
        unresolved_installed_root = resolved_mod_root / "installed"
        installed_root = unresolved_installed_root.resolve()
        unsafe_installed_root = (
            unresolved_installed_root.is_symlink()
            or not installed_root.is_relative_to(resolved_mod_root)
        )
    except (OSError, RuntimeError):
        unsafe_installed_root = True
    if unsafe_installed_root:
        issue = DependencyGraphIssue(
            DependencyGraphIssueCode.MOD_ROOT_UNREADABLE
        )
        return _evaluate((), (issue,))
    nodes: list[DependencyGraphNode] = []
    source_issues: list[DependencyGraphIssue] = []
    for record in records:
        node, issues = _load_installed_node(installed_root, record)
        source_issues.extend(issues)
        if node is not None:
            nodes.append(node)
    return _evaluate(tuple(nodes), tuple(source_issues))


def dependency_graph_errors(
    snapshot: DependencyGraphSnapshot,
) -> tuple[str, ...]:
    """Format stable, non-sensitive diagnostics for one graph snapshot."""

    errors: list[str] = []
    for issue in snapshot.issues:
        description = issue.code.value.replace("_", " ")
        subject = f" for {issue.plugin_id}" if issue.plugin_id else ""
        related = (
            f": {', '.join(issue.related_plugin_ids)}"
            if issue.related_plugin_ids
            else ""
        )
        errors.append(
            "plugin dependency graph is invalid: "
            f"{description}{subject}{related}"
        )
    return tuple(errors)


def candidate_dependency_graph_errors(
    mod_root: Path,
    registry: PluginRegistry,
    manifest: PluginManifest,
) -> tuple[str, ...]:
    """Validate a proposed single-node overlay without mutating installed state."""

    snapshot = snapshot_dependency_graph(mod_root, registry)
    return dependency_graph_errors(snapshot.with_candidate(manifest))


def read_bounded_manifest(path: Path) -> bytes:
    """Read one regular manifest with the graph's fail-closed size bound."""

    try:
        return _read_bounded_manifest(path)
    except _ManifestTooLargeError as error:
        raise ValueError("plugin manifest exceeds the size limit") from error


def _load_installed_node(
    installed_root: Path,
    record: PluginRecord,
) -> tuple[DependencyGraphNode | None, tuple[DependencyGraphIssue, ...]]:
    if not _PLUGIN_ID.fullmatch(record.plugin_id):
        return None, (
            DependencyGraphIssue(
                DependencyGraphIssueCode.UNSAFE_PLUGIN_ID,
                record.plugin_id,
            ),
        )
    unresolved_root = installed_root / record.plugin_id
    try:
        plugin_root = unresolved_root.resolve()
        unsafe_root = unresolved_root.is_symlink() or not plugin_root.is_relative_to(
            installed_root
        )
    except (OSError, RuntimeError):
        unsafe_root = True
    if unsafe_root:
        return None, (
            DependencyGraphIssue(
                DependencyGraphIssueCode.UNSAFE_PLUGIN_ID,
                record.plugin_id,
            ),
        )
    manifest_path = plugin_root / "plugin.json"
    try:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            return _record_node(record), (
                DependencyGraphIssue(
                    DependencyGraphIssueCode.MANIFEST_MISSING,
                    record.plugin_id,
                ),
            )
        manifest_bytes = _read_bounded_manifest(manifest_path)
    except _ManifestTooLargeError:
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.MANIFEST_TOO_LARGE,
                record.plugin_id,
            ),
        )
    except OSError:
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.MANIFEST_MISSING,
                record.plugin_id,
            ),
        )
    if (
        hashlib.sha256(manifest_bytes).hexdigest().lower()
        != record.manifest_hash.lower()
    ):
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.MANIFEST_TAMPERED,
                record.plugin_id,
            ),
        )
    try:
        raw = json.loads(manifest_bytes)
        manifest = PluginManifest.from_dict(raw)
    except (TypeError, ValueError, ManifestError):
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.MANIFEST_INVALID,
                record.plugin_id,
            ),
        )
    if (
        manifest.id != record.plugin_id
        or manifest.version != record.installed_version
    ):
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.MANIFEST_IDENTITY_MISMATCH,
                record.plugin_id,
            ),
        )
    if len(manifest.dependencies) > MAX_DEPENDENCIES_PER_PLUGIN:
        return _record_node(record), (
            DependencyGraphIssue(
                DependencyGraphIssueCode.TOO_MANY_DEPENDENCIES,
                record.plugin_id,
            ),
        )
    return (
        _record_node(record, manifest.dependencies),
        (),
    )


def _read_bounded_manifest(path: Path) -> bytes:
    """Read one stable regular manifest through one owned descriptor."""

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("manifest is not a regular file")
        if before.st_size > MAX_MANIFEST_BYTES:
            raise _ManifestTooLargeError
        chunks: list[bytes] = []
        remaining = MAX_MANIFEST_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 16 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(payload) > MAX_MANIFEST_BYTES:
        raise _ManifestTooLargeError
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or len(payload) != after.st_size:
        raise OSError("manifest changed while it was read")
    return payload


def _record_node(
    record: PluginRecord,
    dependencies: tuple[str, ...] = (),
) -> DependencyGraphNode:
    return DependencyGraphNode(
        record.plugin_id,
        record.installed_version,
        dependencies,
        record.enabled,
        record.pending_action,
    )


def _evaluate(
    nodes: tuple[DependencyGraphNode, ...],
    source_issues: tuple[DependencyGraphIssue, ...],
) -> DependencyGraphSnapshot:
    ordered_nodes = tuple(sorted(nodes, key=lambda node: node.plugin_id))
    by_id = {node.plugin_id: node for node in ordered_nodes}
    issues = list(source_issues)
    for node in ordered_nodes:
        missing = tuple(sorted(
            dependency
            for dependency in node.dependencies
            if dependency not in by_id
        ))
        if missing:
            issues.append(
                DependencyGraphIssue(
                    DependencyGraphIssueCode.MISSING_DEPENDENCY,
                    node.plugin_id,
                    missing,
                )
            )
    issues.extend(_cycle_issues(by_id))
    ordered_issues = tuple(
        sorted(
            set(issues),
            key=lambda issue: (
                issue.code.value,
                issue.plugin_id,
                issue.related_plugin_ids,
            ),
        )
    )
    dependency_order = (
        _dependency_first_order(by_id) if not ordered_issues else ()
    )
    return DependencyGraphSnapshot(
        ordered_nodes,
        ordered_issues,
        dependency_order,
        tuple(
            sorted(
                set(source_issues),
                key=lambda issue: (
                    issue.code.value,
                    issue.plugin_id,
                    issue.related_plugin_ids,
                ),
            )
        ),
    )


def _cycle_issues(
    nodes: dict[str, DependencyGraphNode],
) -> tuple[DependencyGraphIssue, ...]:
    next_index = 0
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    issues: list[DependencyGraphIssue] = []

    def visit(plugin_id: str) -> None:
        nonlocal next_index
        indices[plugin_id] = next_index
        low_links[plugin_id] = next_index
        next_index += 1
        stack.append(plugin_id)
        on_stack.add(plugin_id)
        for dependency in sorted(nodes[plugin_id].dependencies):
            if dependency not in nodes:
                continue
            if dependency not in indices:
                visit(dependency)
                low_links[plugin_id] = min(
                    low_links[plugin_id], low_links[dependency]
                )
            elif dependency in on_stack:
                low_links[plugin_id] = min(
                    low_links[plugin_id], indices[dependency]
                )
        if low_links[plugin_id] != indices[plugin_id]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == plugin_id:
                break
        members = tuple(sorted(component))
        if len(members) > 1 or plugin_id in nodes[plugin_id].dependencies:
            issues.append(
                DependencyGraphIssue(
                    DependencyGraphIssueCode.DEPENDENCY_CYCLE,
                    members[0],
                    members,
                )
            )

    for plugin_id in sorted(nodes):
        if plugin_id not in indices:
            visit(plugin_id)
    return tuple(issues)


def _dependency_first_order(
    nodes: dict[str, DependencyGraphNode],
) -> tuple[str, ...]:
    visited: set[str] = set()
    order: list[str] = []

    def visit(plugin_id: str) -> None:
        if plugin_id in visited:
            return
        visited.add(plugin_id)
        for dependency in sorted(nodes[plugin_id].dependencies):
            visit(dependency)
        order.append(plugin_id)

    for plugin_id in sorted(nodes):
        visit(plugin_id)
    return tuple(order)
