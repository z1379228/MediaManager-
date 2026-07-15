"""Status and enable controls for MODs bundled with MediaManager."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Iterable

from core.builtin_mod_catalog import (
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_IDS as BUILTIN_MOD_IDS,
)
from core.mod_groups import (
    SITE_MOD_PARENT,
    BuiltinModGroup,
    BuiltinModGroupError,
    load_builtin_mod_groups,
)


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
                SITE_MOD_PARENT.get(provider_id, ""),
                module.module_id if module is not None else "",
            )
        )
    return tuple(rows)


def create_builtin_mod_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
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
        "內建 MOD 隨核心發布並通過固定雜湊驗證；可在此統一開關，"
        "也會同步對應工作區。網站主 MOD 啟用後才顯示其子 MOD；"
        "停用主 MOD 會同步停用子 MOD並取消它目前的工作。"
        "表尾的「製作中」是已確立的排程，尚未安裝、不可啟用，也不代表已支援。"
    )
    intro.setObjectName("sectionSubtitle")
    intro.setWordWrap(True)
    page.addWidget(intro)

    summary = QLabel()
    summary.setObjectName("dependencySummary")
    page.addWidget(summary)

    feature_guide = QLabel(
        "選用功能使用說明：啟用 Media Convert 後到主畫面同名分頁轉檔（需要 FFmpeg）；"
        "啟用 Speech to Text 後到同名分頁匯入本機模型並轉錄（需要 whisper-cli）；"
        "啟用 Automation 後到 Automation 分頁建立規則。Automation 的轉檔／轉錄動作"
        "還必須先啟用前兩個 MOD。"
    )
    feature_guide.setObjectName("modUsageGuide")
    feature_guide.setWordWrap(True)
    page.addWidget(feature_guide)

    table = QTableWidget(0, 5)
    table.setObjectName("builtinModTable")
    table.setAccessibleName("內建與製作中 MOD 狀態")
    table.setHorizontalHeaderLabels(
        ("MOD／規劃", "狀態", "用途／預定能力", "控制位置／尚缺", "啟用")
    )
    table.verticalHeader().hide()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
    table.setColumnWidth(0, 180)
    table.setColumnWidth(1, 104)
    table.setColumnWidth(2, 205)
    table.setColumnWidth(4, 84)
    page.addWidget(table, 1)

    controls = QHBoxLayout()
    controls.addStretch()
    refresh = QPushButton("重新整理狀態")
    controls.addWidget(refresh)
    page.addLayout(controls)

    def change_state(provider_id: str, enabled: bool) -> None:
        try:
            cancelled = set_builtin_mod_enabled(context, provider_id, enabled)
        except (KeyError, OSError, RuntimeError) as error:
            QMessageBox.critical(
                panel,
                "無法變更 MOD 狀態",
                f"{provider_id}\n{error}",
            )
            return
        if cancelled:
            summary.setToolTip(f"停用 {provider_id} 時取消 {cancelled} 個工作")
        QTimer.singleShot(0, populate)

    def populate() -> None:
        feature_source = getattr(context, "features", None)
        all_rows = builtin_mod_rows(
            context.download_providers.statuses(),
            context.discovery.statuses(),
            feature_source.statuses() if feature_source is not None else (),
            getattr(context, "builtin_mod_errors", {}),
            locale=getattr(getattr(context, "settings", None), "language", "zh-TW"),
        )
        parent_enabled = {
            row.provider_id: row.enabled
            for row in all_rows
            if not row.parent_provider_id
        }
        rows = tuple(
            row
            for row in all_rows
            if not row.parent_provider_id
            or parent_enabled.get(row.parent_provider_id, False)
        )
        planned_rows = tuple(
            planned
            for planned in PLANNED_MODS
            if planned.provider_id != "bilibili-danmaku"
            or parent_enabled.get("bilibili", False)
        )
        available_count = sum(row.available for row in all_rows)
        enabled_count = sum(row.enabled for row in all_rows)
        ready = available_count == len(all_rows)
        summary.setText(
            f"內建 MOD {available_count}/{len(all_rows)} 已註冊 · "
            f"{enabled_count} 個已啟用 · 目前顯示 {len(rows)} 個父／子 MOD"
            f" · 製作中 {len(PLANNED_MODS)} 項"
        )
        summary.setToolTip(
            "製作中表示已確立但尚未成為可執行 MOD；P0／P1／P2 代表優先級。"
            "Instagram、Threads 與動畫瘋保留官方橋接；Facebook、MEGA 已有獨立下載 MOD。"
            + (
                "\n初始化失敗：\n"
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
        table.setRowCount(len(rows) + len(planned_rows))
        for index, row in enumerate(rows):
            state_text = (
                "已啟用"
                if row.enabled
                else "已停用"
                if row.available
                else "初始化失敗"
            )
            state = QTableWidgetItem(state_text)
            state.setForeground(
                QColor(
                    COLORS["success"]
                    if row.enabled
                    else COLORS["muted"]
                    if row.available
                    else COLORS["danger"]
                )
            )
            values = (
                QTableWidgetItem(
                    (
                        f"{row.group_name} › {row.display_name}"
                        if row.group_name
                        else row.display_name
                    )
                    + f"\n{row.provider_id}"
                ),
                state,
                QTableWidgetItem(row.purpose),
                QTableWidgetItem(row.control_location),
            )
            for column, item in enumerate(values):
                item.setToolTip(
                    f"{item.text()}\n原因：{row.unavailable_reason}"
                    if row.unavailable_reason
                    else item.text()
                )
                table.setItem(index, column, item)
            toggle = QPushButton("停用" if row.enabled else "啟用")
            toggle.setObjectName(f"builtinModToggle-{row.provider_id}")
            toggle.setEnabled(row.available)
            toggle.setAccessibleName(
                (
                    f"{row.group_name} › {row.display_name}"
                    if row.group_name
                    else row.display_name
                )
                + " 啟用狀態"
            )
            toggle.setToolTip(
                "立即啟用或停用此內建 MOD"
                if row.available
                else (
                    f"這個內建 MOD 初始化失敗：{row.unavailable_reason}"
                    if row.unavailable_reason
                    else "這個內建 MOD 尚未註冊；請重新啟動或重新安裝 MediaManager。"
                )
            )
            toggle.clicked.connect(
                lambda _checked=False, selected=row.provider_id, enabled=not row.enabled: change_state(
                    selected, enabled
                )
            )
            table.setCellWidget(index, 4, toggle)
            table.setRowHeight(index, 52)

        for offset, planned in enumerate(planned_rows, start=len(rows)):
            state = QTableWidgetItem(f"{planned.state} · {planned.priority}")
            state.setForeground(QColor(COLORS["warning"]))
            unavailable = QTableWidgetItem("尚不可用")
            unavailable.setForeground(QColor(COLORS["muted"]))
            values = (
                QTableWidgetItem(f"{planned.display_name}\n{planned.provider_id}"),
                state,
                QTableWidgetItem(
                    f"{planned.kind}：{planned.planned_capabilities}"
                ),
                QTableWidgetItem(f"尚缺：{planned.implementation_gap}"),
                unavailable,
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(offset, column, item)
            table.setRowHeight(offset, 68)

    refresh.clicked.connect(populate)
    events = getattr(context, "events", None)
    if events is not None:
        events.subscribe("ui.language.changed", lambda _payload: populate())
        events.subscribe("builtin_mod.changed", lambda _payload: populate())
    populate()
    return panel
