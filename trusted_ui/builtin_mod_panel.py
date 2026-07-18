"""Status and hierarchical enable controls for bundled MODs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Iterable

from core.builtin_mod_catalog import (
    BUILTIN_MOD_CHILDREN,
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_IDS as BUILTIN_MOD_IDS,
    BUILTIN_MOD_PARENT,
)
from core.mod_groups import (
    SITE_MOD_CHILDREN,
    BuiltinModGroup,
    BuiltinModGroupError,
    load_builtin_mod_groups,
)
from core.builtin_mod_snapshot import snapshot_for_context


@dataclass(frozen=True, slots=True)
class BuiltinModRow:
    provider_id: str
    display_name: str
    purpose: str
    control_location: str
    available: bool
    enabled: bool
    unavailable_reason: str = ""
    group_name: str = ""
    parent_provider_id: str = ""
    module_id: str = ""


def builtin_mod_rows(
    download_statuses: Iterable[object],
    discovery_statuses: Iterable[object],
    feature_statuses: Iterable[object] = (),
    unavailable_reasons: Mapping[str, str] | None = None,
    *,
    locale: object = "zh-TW",
    groups: Iterable[BuiltinModGroup] | None = None,
) -> tuple[BuiltinModRow, ...]:
    unavailable_reasons = unavailable_reasons or {}
    statuses = {
        str(status.provider_id): status
        for status in (
            *tuple(download_statuses),
            *tuple(discovery_statuses),
            *tuple(feature_statuses),
        )
    }
    try:
        active_groups = tuple(groups) if groups is not None else load_builtin_mod_groups(locale)
    except BuiltinModGroupError:
        active_groups = ()
    localized_modules = {
        module.provider_id: (group.display_name, module)
        for group in active_groups
        for module in group.modules
    }
    rows = []
    for descriptor in BUILTIN_MOD_CATALOG:
        provider_id = descriptor.provider_id
        status = statuses.get(provider_id)
        localized = localized_modules.get(provider_id)
        group_name = localized[0] if localized is not None else ""
        module = localized[1] if localized is not None else None
        reason = " ".join(
            str(
                unavailable_reasons.get(
                    provider_id,
                    getattr(status, "reason", ""),
                )
            ).split()
        )[:240]
        available = (
            bool(getattr(status, "available", True))
            if status is not None
            else False
        ) and not reason
        rows.append(
            BuiltinModRow(
                provider_id,
                module.display_name
                if module is not None
                else str(status.display_name)
                if status is not None
                else descriptor.display_name,
                module.purpose if module is not None else descriptor.purpose,
                module.control_location
                if module is not None
                else descriptor.control_location,
                available,
                bool(status.enabled) if status is not None and available else False,
                reason,
                group_name,
                BUILTIN_MOD_PARENT.get(provider_id, ""),
                module.module_id if module is not None else "",
            )
        )
    return tuple(rows)


def create_builtin_mod_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
    from trusted_ui.planned_mod_catalog import PLANNED_MODS
    from trusted_ui.theme import COLORS

    panel = QWidget(parent)
    page = QVBoxLayout(panel)
    page.setContentsMargins(4, 8, 4, 4)
    page.setSpacing(10)

    intro = QLabel(
        "網站功能已依父 MOD 與子 MOD 分組。點擊網站名稱展開；先啟用主 MOD，"
        "才會顯示搜尋、批量下載、預覽等子 MOD。停用主 MOD 會同步停用子 MOD，"
        "並取消它目前的工作。表尾的「製作中」尚不可啟用，也不代表已支援。"
    )
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary = QLabel()
    summary.setObjectName("dependencySummary")
    page.addWidget(summary)

    feature_guide = QLabel(
        "使用方式：Media Convert 需先安裝 FFmpeg；Speech to Text 需 whisper-cli "
        "與語音模型；Automation 必須先啟用 Automation MOD，再到自動化頁建立規則。"
    )
    feature_guide.setObjectName("modUsageGuide")
    feature_guide.setWordWrap(True)
    page.addWidget(feature_guide)

    tree = QTreeWidget()
    tree.setObjectName("builtinModTree")
    tree.setAccessibleName("依網站分組的內建 MOD 清單")
    tree.setColumnCount(5)
    tree.setHeaderLabels(
        ("MOD／網站", "狀態", "用途與能力", "控制位置／缺口", "啟用")
    )
    tree.setAlternatingRowColors(True)
    tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    tree.setRootIsDecorated(True)
    tree.setItemsExpandable(True)
    tree.setExpandsOnDoubleClick(True)
    header = tree.header()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
    tree.setColumnWidth(0, 220)
    tree.setColumnWidth(1, 112)
    tree.setColumnWidth(2, 235)
    tree.setColumnWidth(4, 104)
    page.addWidget(tree, 1)

    controls = QHBoxLayout()
    controls.addStretch()
    refresh = QPushButton("重新整理 MOD 狀態")
    controls.addWidget(refresh)
    page.addLayout(controls)

    expanded_groups: set[str] = set()

    def change_state(provider_id: str, enabled: bool) -> None:
        try:
            cancelled = set_builtin_mod_enabled(context, provider_id, enabled)
        except (KeyError, OSError, RuntimeError) as error:
            QMessageBox.critical(
                panel,
                "無法切換 MOD 狀態",
                f"{provider_id}\n{error}",
            )
            QTimer.singleShot(0, populate)
            return
        if cancelled:
            summary.setToolTip(f"停用 {provider_id} 時取消了 {cancelled} 個工作")
        QTimer.singleShot(0, populate)

    def state_text(row: BuiltinModRow) -> str:
        if row.enabled:
            return "已啟用"
        if row.available:
            return "已停用"
        return "初始化失敗"

    def state_color(row: BuiltinModRow) -> QColor:
        return QColor(
            COLORS["success"]
            if row.enabled
            else COLORS["muted"]
            if row.available
            else COLORS["danger"]
        )

    def add_mod_item(parent_item: QTreeWidgetItem | None, row: BuiltinModRow) -> None:
        item = QTreeWidgetItem(
            (
                f"{row.display_name}\n{row.provider_id}",
                state_text(row),
                row.purpose,
                row.control_location,
                "",
            )
        )
        item.setData(0, Qt.ItemDataRole.UserRole, row.provider_id)
        item.setForeground(1, state_color(row))
        tooltip = "\n".join(
            part
            for part in (
                f"{row.display_name} ({row.provider_id})",
                row.purpose,
                row.control_location,
                f"原因：{row.unavailable_reason}" if row.unavailable_reason else "",
            )
            if part
        )
        for column in range(5):
            item.setToolTip(column, tooltip)
        if parent_item is None:
            tree.addTopLevelItem(item)
        else:
            parent_item.addChild(item)

        toggle = QCheckBox("啟用")
        toggle.setObjectName(f"builtinModToggle-{row.provider_id}")
        toggle.setAccessibleName(f"{row.display_name} 啟用狀態")
        toggle.setChecked(row.enabled)
        toggle.setEnabled(row.available)
        if row.available:
            toggle.setToolTip("勾選啟用；取消勾選會停止此 MOD 的新工作")
        elif row.unavailable_reason:
            toggle.setToolTip(f"MOD 初始化失敗：{row.unavailable_reason}")
        else:
            toggle.setToolTip("MOD 尚未正確載入；請重新整理或查看錯誤原因")
        toggle.toggled.connect(
            lambda checked, selected=row.provider_id: change_state(selected, checked)
        )
        tree.setItemWidget(item, 4, toggle)

    def populate() -> None:
        snapshot = snapshot_for_context(context)
        all_rows = builtin_mod_rows(
            snapshot.download,
            snapshot.discovery,
            snapshot.feature,
            snapshot.errors,
            locale=getattr(getattr(context, "settings", None), "language", "zh-TW"),
        )
        rows_by_id = {row.provider_id: row for row in all_rows}
        grouped_ids = frozenset(BUILTIN_MOD_CHILDREN).union(BUILTIN_MOD_PARENT)
        available_count = sum(row.available for row in all_rows)
        enabled_count = sum(row.enabled for row in all_rows)
        ready = available_count == len(all_rows)
        summary.setText(
            f"內建 MOD {available_count}/{len(all_rows)} 已載入 · "
            f"{enabled_count} 個已啟用 · {len(SITE_MOD_CHILDREN)} 個網站父 MOD"
            f" · 規劃中 {len(PLANNED_MODS)} 個"
        )
        summary.setToolTip(
            "點擊網站父節點展開主 MOD；主 MOD 啟用後才顯示並允許管理其子 MOD。"
            "Instagram、Threads 與 X 僅提供官方頁面及官方資料匯出工具，不會自動擷取網站內容。"
            + (
                "\n初始化失敗原因：\n"
                + "\n".join(
                    f"{row.provider_id}：{row.unavailable_reason}"
                    for row in all_rows
                    if row.unavailable_reason
                )
                if any(row.unavailable_reason for row in all_rows)
                else ""
            )
        )
        summary.setProperty("dependencyState", "ready" if ready else "warning")
        summary.style().unpolish(summary)
        summary.style().polish(summary)

        tree.blockSignals(True)
        tree.clear()
        for group_id, children in BUILTIN_MOD_CHILDREN.items():
            parent_row = rows_by_id.get(group_id)
            if parent_row is None:
                continue
            visible_children = (
                tuple(rows_by_id[child] for child in children if child in rows_by_id)
                if parent_row.enabled
                else ()
            )
            group = QTreeWidgetItem(
                (
                    parent_row.group_name or parent_row.display_name,
                    "主 MOD 已啟用" if parent_row.enabled else "主 MOD 已停用",
                    f"展開管理主功能與 {len(children)} 個子 MOD",
                    "點擊左側箭頭展開",
                    "",
                )
            )
            group.setData(0, Qt.ItemDataRole.UserRole, f"group:{group_id}")
            group.setForeground(1, state_color(parent_row))
            tree.addTopLevelItem(group)
            add_mod_item(group, parent_row)
            for child_row in visible_children:
                add_mod_item(group, child_row)
            if group_id in expanded_groups:
                group.setExpanded(True)

        for row in all_rows:
            if row.provider_id not in grouped_ids:
                add_mod_item(None, row)

        for planned in PLANNED_MODS:
            item = QTreeWidgetItem(
                (
                    f"{planned.display_name}\n{planned.provider_id}",
                    f"{planned.state} · {planned.priority}",
                    f"{planned.kind}：{planned.planned_capabilities}",
                    f"待補：{planned.implementation_gap}",
                    "尚不可啟用",
                )
            )
            item.setForeground(1, QColor(COLORS["warning"]))
            item.setForeground(4, QColor(COLORS["muted"]))
            for column in range(5):
                item.setToolTip(column, item.text(column))
            tree.addTopLevelItem(item)
        tree.blockSignals(False)

    def remember_expanded(item: QTreeWidgetItem) -> None:
        value = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if value.startswith("group:"):
            expanded_groups.add(value.removeprefix("group:"))

    def remember_collapsed(item: QTreeWidgetItem) -> None:
        value = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if value.startswith("group:"):
            expanded_groups.discard(value.removeprefix("group:"))

    refresh.clicked.connect(populate)
    tree.itemExpanded.connect(remember_expanded)
    tree.itemCollapsed.connect(remember_collapsed)
    events = getattr(context, "events", None)
    if events is not None:
        events.subscribe("ui.language.changed", lambda _payload: populate())
        events.subscribe("builtin_mod.changed", lambda _payload: populate())
    populate()
    return panel
