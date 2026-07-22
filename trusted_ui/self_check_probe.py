"""Bounded runtime UI probes used only by the manual trusted self-check page."""

from __future__ import annotations

from core.builtin_mod_catalog import BUILTIN_MOD_PARENT, OPTIONAL_WORKSPACE_IDS
from core.builtin_mod_snapshot import snapshot_for_context
from core.localization import SUPPORTED_LOCALE_CODES, normalized_core_locale
from core.self_check import SelfCheckItem, SelfCheckState
from trusted_ui.builtin_mod_panel import builtin_mod_rows


def _item(
    check_id: str,
    state: SelfCheckState,
    summary: str,
    detail: str,
    remediation_id: str = "",
) -> SelfCheckItem:
    return SelfCheckItem(
        check_id,
        state,
        summary,
        detail,
        remediation_id,
    )


def _main_window(anchor: object) -> object | None:
    current: object | None = anchor
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if hasattr(current, "optional_workspace_manager"):
            return current
        parent_widget = getattr(current, "parentWidget", None)
        current = parent_widget() if callable(parent_widget) else None
    return None


def _mod_management_item(context: object, anchor: object) -> SelfCheckItem:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QCheckBox, QTreeWidget

    window = anchor.window()
    tree = window.findChild(QTreeWidget, "builtinModTree")
    if tree is None:
        return _item(
            "ui.mod_management",
            "warning",
            "未附加 MOD 管理樹",
            "請從主視窗的 MOD 管理開啟本頁，再執行按鈕與父子顯示檢查。",
            "ui.mod_management.open",
        )
    snapshot = snapshot_for_context(context)
    rows = builtin_mod_rows(
        snapshot.download,
        snapshot.discovery,
        snapshot.feature,
        snapshot.errors,
        locale=getattr(getattr(context, "settings", None), "language", "zh-TW"),
    )
    rows_by_id = {row.provider_id: row for row in rows}
    expected_visible = {
        row.provider_id
        for row in rows
        if not (parent_id := BUILTIN_MOD_PARENT.get(row.provider_id))
        or bool(rows_by_id.get(parent_id) and rows_by_id[parent_id].enabled)
    }
    actual_visible: set[str] = set()
    for top_index in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(top_index)
        top_id = str(top.data(0, Qt.ItemDataRole.UserRole) or "")
        if top_id and not top_id.startswith("group:"):
            actual_visible.add(top_id)
        for child_index in range(top.childCount()):
            child_id = str(
                top.child(child_index).data(0, Qt.ItemDataRole.UserRole) or ""
            )
            if child_id:
                actual_visible.add(child_id)
    toggles = {
        toggle.objectName().removeprefix("builtinModToggle-"): toggle
        for toggle in window.findChildren(QCheckBox)
        if toggle.objectName().startswith("builtinModToggle-")
    }
    problems: list[str] = []
    if actual_visible != expected_visible:
        problems.append("父／子 MOD 顯示項目與啟用狀態不一致")
    if set(toggles) != expected_visible:
        problems.append("MOD 啟用按鈕數量或歸屬不一致")
    for provider_id, toggle in toggles.items():
        row = rows_by_id.get(provider_id)
        if row is None:
            problems.append(f"{provider_id} 沒有對應編目")
            continue
        if toggle.isChecked() != row.enabled:
            problems.append(f"{provider_id} 勾選狀態錯誤")
        if toggle.isEnabled() != row.available:
            problems.append(f"{provider_id} 按鈕可用狀態錯誤")
    return _item(
        "ui.mod_management",
        "block" if problems else "pass",
        "MOD 管理顯示或按鈕異常" if problems else "MOD 管理顯示與按鈕正常",
        "; ".join(problems[:12])
        if problems
        else f"已核對 {len(expected_visible)} 個目前可見 MOD 與啟用按鈕",
        "ui.mod_management.rebuild" if problems else "",
    )


def _optional_workspace_item(context: object, owner: object | None) -> SelfCheckItem:
    if owner is None:
        return _item(
            "ui.optional_workspaces.runtime",
            "warning",
            "未附加主視窗工作區",
            "核心檢查已完成；從主視窗開啟 MOD 管理可一併檢查選用分頁。",
            "ui.optional_workspaces.open",
        )
    manager = owner.optional_workspace_manager
    problems: list[str] = []
    spec_ids = set(manager.specs)
    if spec_ids != set(OPTIONAL_WORKSPACE_IDS):
        problems.append("選用工作區規格與編目不同步")
    expected_panels: set[str] = set()
    for provider_id, spec in manager.specs.items():
        try:
            if spec.available() and spec.enabled():
                expected_panels.add(provider_id)
        except (AttributeError, KeyError, RuntimeError, TypeError):
            problems.append(f"{provider_id} 工作區狀態無法讀取")
    actual_panels = set(manager.panels)
    if actual_panels != expected_panels:
        problems.append("已啟用 MOD 與實際分頁不一致")
    return _item(
        "ui.optional_workspaces.runtime",
        "block" if problems else "pass",
        "選用工作區生命週期異常" if problems else "選用工作區生命週期正常",
        "; ".join(problems)
        if problems
        else f"已核對 {len(spec_ids)} 個規格與 {len(actual_panels)} 個已開啟分頁",
        "ui.optional_workspaces.sync" if problems else "",
    )


def _language_actions_item(context: object, owner: object | None) -> SelfCheckItem:
    if owner is None or not hasattr(owner, "language_group"):
        return _item(
            "ui.language_actions",
            "warning",
            "未附加主視窗語言選單",
            "核心與 MOD 語言資源已檢查；主選單需從主視窗執行時核對。",
            "ui.language_actions.open",
        )
    actions = tuple(owner.language_group.actions())
    action_locales = {str(action.data()) for action in actions}
    checked = tuple(str(action.data()) for action in actions if action.isChecked())
    selected = normalized_core_locale(
        getattr(getattr(context, "settings", None), "language", None)
    )
    valid = action_locales == set(SUPPORTED_LOCALE_CODES) and checked == (selected,)
    return _item(
        "ui.language_actions",
        "pass" if valid else "block",
        "四語言選單狀態正常" if valid else "四語言選單狀態異常",
        (
            f"目前選擇 {selected}；共 {len(actions)} 個固定語言選項"
            if valid
            else "語言選項缺漏、重複或勾選狀態與核心不同步"
        ),
        "ui.language_actions.rebuild" if not valid else "",
    )


def _download_actions_item(context: object, owner: object | None) -> SelfCheckItem:
    if owner is None:
        return _item(
            "ui.download_actions",
            "warning",
            "未附加下載工作區",
            "從主視窗開啟 MOD 管理後，可核對停用 MOD 的下載按鈕是否確實關閉。",
            "ui.download_actions.open",
        )
    panels = dict(getattr(owner, "site_download_panels", {}))
    panels.update(getattr(owner.optional_workspace_manager, "panels", {}))
    problems: list[str] = []
    for provider_id, panel in panels.items():
        try:
            enabled = context.download_providers.is_enabled(provider_id)
        except (AttributeError, KeyError, RuntimeError):
            continue
        enable_toggle = getattr(panel, "enabled", None)
        if enable_toggle is not None and enable_toggle.isChecked() != enabled:
            problems.append(f"{provider_id} 工作區開關不同步")
        if enabled:
            continue
        for action_name in ("read_info", "add_download", "expand_playlist"):
            action = getattr(panel, action_name, None)
            if action is not None and action.isEnabled():
                problems.append(f"{provider_id}.{action_name} 停用時仍可按")
    return _item(
        "ui.download_actions",
        "block" if problems else "pass",
        "下載按鈕啟用狀態異常" if problems else "下載按鈕啟用狀態正常",
        "; ".join(problems[:12])
        if problems
        else f"已核對 {len(panels)} 個已建立下載工作區",
        "ui.download_actions.sync" if problems else "",
    )


def collect_ui_self_check_items(
    context: object,
    anchor: object,
) -> tuple[SelfCheckItem, ...]:
    """Inspect current widgets only; never create workspaces or start a provider."""

    owner = _main_window(anchor)
    return (
        _mod_management_item(context, anchor),
        _optional_workspace_item(context, owner),
        _language_actions_item(context, owner),
        _download_actions_item(context, owner),
    )
