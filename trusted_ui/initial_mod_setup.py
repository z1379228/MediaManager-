"""One-time trusted UI for selecting built-in MODs before the shell opens."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from core.builtin_mod_catalog import BUILTIN_MOD_PARENT
from core.builtin_mod_snapshot import snapshot_for_context
from core.settings import SettingsService
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.builtin_mod_panel import BuiltinModRow, builtin_mod_rows


@dataclass(frozen=True, slots=True)
class _InitialSelectionResult:
    errors: tuple[str, ...]
    original_states: tuple[tuple[str, bool], ...]
    cancelled_work: int = 0


def _current_mod_state(context: object, provider_id: str) -> bool:
    return bool(
        next(
            status.enabled
            for registry in (
                context.download_providers,
                context.discovery,
                context.features,
            )
            for status in registry.statuses()
            if status.provider_id == provider_id
        )
    )


def _restore_initial_mod_states(
    context: object,
    original_states: tuple[tuple[str, bool], ...],
) -> tuple[str, ...]:
    """Best-effort restore while respecting parent-before-child enable gates."""

    enabled = tuple(item for item in original_states if item[1])
    disabled = tuple(item for item in reversed(original_states) if not item[1])
    failures: list[str] = []
    for provider_id, desired in enabled + disabled:
        try:
            if _current_mod_state(context, provider_id) != desired:
                set_builtin_mod_enabled(context, provider_id, desired)
        except (AttributeError, KeyError, RuntimeError, StopIteration) as error:
            failures.append(provider_id)
            audit = getattr(context, "audit", None)
            if audit is not None:
                audit.write(
                    "builtin_mod.initial_setup_rollback_failed",
                    provider_id=provider_id,
                    error_type=type(error).__name__,
                )
    return tuple(failures)


def _apply_initial_mod_selection(
    context: object, selected: set[str], rows: Iterable[BuiltinModRow]
) -> _InitialSelectionResult:
    by_id = {row.provider_id: row for row in rows if row.available}
    selected = set(selected)
    for provider_id in tuple(selected):
        parent_id = BUILTIN_MOD_PARENT.get(provider_id)
        if parent_id in by_id:
            selected.add(parent_id)

    ordered_ids = ordered_selection_ids(by_id.values())
    try:
        original_states = tuple(
            (provider_id, _current_mod_state(context, provider_id))
            for provider_id in ordered_ids
        )
    except (AttributeError, StopIteration) as error:
        audit = getattr(context, "audit", None)
        if audit is not None:
            audit.write(
                "builtin_mod.initial_setup_failed",
                provider_id="registry-snapshot",
                error=" ".join(str(error).split())[:240],
            )
        return _InitialSelectionResult(("registry-snapshot",), ())

    cancelled_work = 0
    for provider_id, current in original_states:
        desired = provider_id in selected
        if current == desired:
            continue
        try:
            cancelled_work += int(
                set_builtin_mod_enabled(context, provider_id, desired)
            )
        except (AttributeError, KeyError, RuntimeError, StopIteration) as error:
            audit = getattr(context, "audit", None)
            if audit is not None:
                audit.write(
                    "builtin_mod.initial_setup_failed",
                    provider_id=provider_id,
                    error=" ".join(str(error).split())[:240],
                )
            rollback_failures = _restore_initial_mod_states(
                context,
                original_states,
            )
            if cancelled_work or rollback_failures:
                if audit is not None:
                    audit.write(
                        "builtin_mod.initial_setup_rollback_incomplete",
                        cancelled_work=cancelled_work,
                        failed_provider_ids=rollback_failures,
                    )
            return _InitialSelectionResult(
                (provider_id,),
                original_states,
                cancelled_work,
            )
    return _InitialSelectionResult((), original_states, cancelled_work)


def initial_mod_setup_required(settings: object) -> bool:
    """Return whether the one-time MOD selection has not been completed."""

    return not bool(getattr(settings, "initial_mod_setup_completed", False))


def initial_mod_setup_preserve_reasons(context: object) -> tuple[str, ...]:
    """Explain why the one-time wizard must preserve existing MOD states."""

    reasons: list[str] = []
    settings_load = getattr(context, "settings_load", None)
    if getattr(settings_load, "state", None) != "missing":
        reasons.append("settings_not_missing")

    paths = getattr(context, "paths", None)
    mod_root = getattr(paths, "mod", None)
    data_root = getattr(paths, "data", None)
    if not isinstance(mod_root, Path) or not isinstance(data_root, Path):
        reasons.append("runtime_paths_unknown")
    else:
        markers = (
            mod_root / "provider-state.json",
            mod_root / "discovery-state.json",
            mod_root / "feature-state.json",
            data_root / "download-queue.json",
        )
        if any(path.exists() or path.is_symlink() for path in markers):
            reasons.append("durable_state_present")

    download_queue = getattr(context, "download_queue", None)
    if download_queue is None or not callable(
        getattr(download_queue, "snapshots", None)
    ):
        reasons.append("download_queue_unknown")
    else:
        try:
            if download_queue.snapshots():
                reasons.append("download_work_present")
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            reasons.append("download_work_unknown")

    for name in ("conversion", "transcription"):
        service = getattr(context, name, None)
        if service is None:
            continue
        snapshots = getattr(service, "snapshots", None)
        if not callable(snapshots):
            reasons.append(f"{name}_work_unknown")
            continue
        try:
            if snapshots():
                reasons.append(f"{name}_work_present")
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            reasons.append(f"{name}_work_unknown")
    return tuple(dict.fromkeys(reasons))


def initial_mod_selection_is_pristine(context: object) -> bool:
    """Allow initial selection only when no prior settings or work exist."""

    return not initial_mod_setup_preserve_reasons(context)


def ordered_selection_ids(rows: Iterable[BuiltinModRow]) -> tuple[str, ...]:
    """Return parent MODs before children so dependency checks can succeed."""

    values = tuple(row.provider_id for row in rows if row.available)
    parents = tuple(
        provider_id for provider_id in values if provider_id not in BUILTIN_MOD_PARENT
    )
    children = tuple(
        provider_id for provider_id in values if provider_id in BUILTIN_MOD_PARENT
    )
    return parents + children


def apply_initial_mod_selection(
    context: object, selected: set[str], rows: Iterable[BuiltinModRow]
) -> tuple[str, ...]:
    """Apply a one-time selection and compensate every state after failure."""

    return _apply_initial_mod_selection(context, selected, rows).errors


def mark_initial_mod_setup_complete(context: object) -> None:
    """Persist completion atomically through the existing settings service."""

    saved = SettingsService(
        Path(context.paths.settings) / "settings.json"
    ).patch(initial_mod_setup_completed=True)
    context.settings.initial_mod_setup_completed = (
        saved.initial_mod_setup_completed
    )


def complete_initial_mod_setup(
    context: object,
    selected: set[str],
    rows: Iterable[BuiltinModRow],
    *,
    apply_selection: bool,
) -> bool:
    """Persist completion only after every requested MOD change succeeds."""

    selection_result = _InitialSelectionResult((), ())
    if apply_selection:
        preserve_reasons = initial_mod_setup_preserve_reasons(context)
        if preserve_reasons:
            audit = getattr(context, "audit", None)
            if audit is not None:
                audit.write(
                    "builtin_mod.initial_setup_existing_state_preserved",
                    reason_codes=preserve_reasons,
                )
            apply_selection = False
    if apply_selection:
        settings_status = SettingsService(
            Path(context.paths.settings) / "settings.json"
        ).load_with_status()
        if not settings_status.writable:
            audit = getattr(context, "audit", None)
            if audit is not None:
                audit.write(
                    "builtin_mod.initial_setup_save_blocked",
                    settings_state=settings_status.state,
                )
            return False
        selection_result = _apply_initial_mod_selection(context, selected, rows)
        if selection_result.errors:
            return False
    try:
        mark_initial_mod_setup_complete(context)
    except (OSError, TypeError, ValueError) as error:
        audit = getattr(context, "audit", None)
        if audit is not None:
            audit.write(
                "builtin_mod.initial_setup_save_failed",
                error_type=type(error).__name__,
            )
        rollback_failures = _restore_initial_mod_states(
            context,
            selection_result.original_states,
        )
        if selection_result.cancelled_work or rollback_failures:
            if audit is not None:
                audit.write(
                    "builtin_mod.initial_setup_rollback_incomplete",
                    cancelled_work=selection_result.cancelled_work,
                    failed_provider_ids=rollback_failures,
                )
        return False
    return True


def show_initial_mod_setup(context: object, parent: object = None) -> bool:
    """Show the one-time MOD selection dialog before creating the main window."""

    if not initial_mod_setup_required(context.settings):
        return True

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
    )

    snapshot = snapshot_for_context(context)
    rows = builtin_mod_rows(
        snapshot.download,
        snapshot.discovery,
        snapshot.feature,
        snapshot.errors,
        locale=getattr(context.settings, "language", "zh-TW"),
    )
    preserve_reasons = initial_mod_setup_preserve_reasons(context)
    dialog = QDialog(parent)
    dialog.setWindowTitle("首次啟動：選擇要啟用的 MOD")
    dialog.setMinimumSize(680, 520)
    dialog.setModal(True)
    layout = QVBoxLayout(dialog)
    intro_text = (
        "偵測到既有設定、狀態或工作；本次只保留目前 MOD 狀態，不執行任何啟停。"
        "稍後可在 MOD 管理頁明確調整。"
        if preserve_reasons
        else "第一次啟動時，請選擇要載入的 MOD 模組。主 MOD 會在啟用後顯示可用的子 MOD；"
        "未來可在 MOD 管理中再次調整。不可用的模組會保留並標示原因。"
    )
    intro = QLabel(intro_text)
    intro.setWordWrap(True)
    intro.setAccessibleName("首次啟動 MOD 設定說明")
    layout.addWidget(intro)
    tree = QTreeWidget(dialog)
    tree.setHeaderLabels(("MOD 模組", "用途與狀態"))
    tree.setAccessibleName("首次啟動 MOD 選擇清單")
    tree.setColumnWidth(0, 250)
    items: dict[str, QTreeWidgetItem] = {}
    for row in rows:
        item = QTreeWidgetItem((row.display_name, row.purpose))
        item.setData(0, Qt.ItemDataRole.UserRole, row.provider_id)
        item.setCheckState(
            0, Qt.CheckState.Checked if row.enabled else Qt.CheckState.Unchecked
        )
        item.setToolTip(0, row.control_location)
        item.setToolTip(1, row.purpose)
        item.setDisabled(not row.available or bool(preserve_reasons))
        items[row.provider_id] = item
    for row in rows:
        item = items[row.provider_id]
        parent_id = row.parent_provider_id
        if parent_id and parent_id in items:
            items[parent_id].addChild(item)
        else:
            tree.addTopLevelItem(item)
    tree.expandAll()
    layout.addWidget(tree, 1)
    note = QLabel(
        "提示：勾選子 MOD 時會自動啟用其主 MOD；取消勾選不會刪除設定或使用者資料。"
    )
    note.setWordWrap(True)
    layout.addWidget(note)
    actions = QHBoxLayout()
    actions.addStretch()
    skip = QPushButton("略過，維持目前設定")
    start = QPushButton(
        "保留目前 MOD 狀態並開始"
        if preserve_reasons
        else "儲存選擇並開始"
    )
    start.setObjectName("primary")
    actions.addWidget(skip)
    actions.addWidget(start)
    layout.addLayout(actions)

    def finish(apply_selection: bool) -> None:
        selected = (
            {
                provider_id
                for provider_id, item in items.items()
                if item.checkState(0) == Qt.CheckState.Checked
            }
            if apply_selection
            else set()
        )
        if complete_initial_mod_setup(
            context,
            selected,
            rows,
            apply_selection=apply_selection,
        ):
            dialog.accept()
        else:
            QMessageBox.warning(
                dialog,
                "MOD 設定尚未完成",
                "無法安全保存這次選擇；可回復的狀態已復原，"
                "任何無法復原的工作取消均已寫入安全稽核。",
            )

    start.clicked.connect(lambda: finish(True))
    skip.clicked.connect(lambda: finish(False))
    dialog.exec()
    return True
