"""Status and enable controls for MODs bundled with MediaManager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class BuiltinModRow:
    provider_id: str
    display_name: str
    purpose: str
    control_location: str
    available: bool
    enabled: bool


_BUILTIN_MODS = (
    ("youtube", "YouTube", "批量、分段與音訊下載", "下載工作區"),
    (
        "generic-ytdlp",
        "其他網站 Beta",
        "白名單網站的分析、清單與下載",
        "下載工作區（預設停用）",
    ),
    (
        "bilibili",
        "Bilibili",
        "影片、分段與彈幕 XML／ASS／MKV",
        "下載工作區（預設停用）",
    ),
    ("youtube-search", "YouTube Search", "搜尋影片與音樂", "YouTube 搜尋 → 搜尋 MOD"),
    (
        "youtube-player",
        "YouTube Player",
        "可選的低畫質影片預覽",
        "YouTube 搜尋 → 搜尋 MOD",
    ),
    (
        "youtube-history",
        "YouTube History",
        "記錄有限搜尋偏好",
        "YouTube 搜尋 → 搜尋 MOD",
    ),
    (
        "youtube-recovery",
        "YouTube Recovery",
        "尋找失效影片替代項目",
        "YouTube 搜尋 → 搜尋 MOD",
    ),
    (
        "youtube-similar",
        "YouTube Similar",
        "隨機尋找相似內容",
        "YouTube 搜尋 → 搜尋 MOD",
    ),
    (
        "youtube-auto-split",
        "YouTube Auto Split",
        "分析並預覽長影片切割點",
        "下載工作區 → 準備切割",
    ),
    (
        "media-convert",
        "Media Convert",
        "本機轉封裝、轉檔、壓縮、串接、切割與字幕處理",
        "啟用後顯示 Media Convert 工作區",
    ),
    (
        "speech-to-text",
        "Speech to Text",
        "本機語音轉文字與 TXT、SRT、VTT 輸出",
        "啟用後顯示 Speech to Text 工作區",
    ),
    (
        "automation",
        "Automation",
        "排程網址、監看資料夾與剪貼簿網址候選",
        "啟用後顯示 Automation 工作區；規則仍預設關閉",
    ),
)
BUILTIN_MOD_IDS = frozenset(item[0] for item in _BUILTIN_MODS)


def builtin_mod_rows(
    download_statuses: Iterable[object],
    discovery_statuses: Iterable[object],
    feature_statuses: Iterable[object] = (),
) -> tuple[BuiltinModRow, ...]:
    statuses = {
        str(status.provider_id): status
        for status in (
            *tuple(download_statuses),
            *tuple(discovery_statuses),
            *tuple(feature_statuses),
        )
    }
    rows = []
    for provider_id, fallback_name, purpose, control_location in _BUILTIN_MODS:
        status = statuses.get(provider_id)
        rows.append(
            BuiltinModRow(
                provider_id,
                str(status.display_name) if status is not None else fallback_name,
                purpose,
                control_location,
                bool(getattr(status, "available", True))
                if status is not None
                else False,
                bool(status.enabled) if status is not None else False,
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
    from trusted_ui.theme import COLORS

    panel = QWidget(parent)
    page = QVBoxLayout(panel)
    page.setContentsMargins(4, 8, 4, 4)
    page.setSpacing(10)

    intro = QLabel(
        "內建 MOD 隨核心發布並通過固定雜湊驗證；可在此統一開關，"
        "也會同步對應工作區。停用下載 MOD 會取消它目前的工作。"
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
    table.setHorizontalHeaderLabels(
        ("內建 MOD", "狀態", "用途", "控制位置", "啟用")
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
    table.setColumnWidth(1, 78)
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
        rows = builtin_mod_rows(
            context.download_providers.statuses(),
            context.discovery.statuses(),
            feature_source.statuses() if feature_source is not None else (),
        )
        available_count = sum(row.available for row in rows)
        enabled_count = sum(row.enabled for row in rows)
        ready = available_count == len(rows)
        summary.setText(
            f"內建 MOD {available_count}/{len(rows)} 可用 · {enabled_count} 個已啟用"
        )
        summary.setProperty("dependencyState", "ready" if ready else "warning")
        summary.style().unpolish(summary)
        summary.style().polish(summary)
        table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            state_text = (
                "已啟用" if row.enabled else "已停用" if row.available else "不可用"
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
                QTableWidgetItem(f"{row.display_name}\n{row.provider_id}"),
                state,
                QTableWidgetItem(row.purpose),
                QTableWidgetItem(row.control_location),
            )
            for column, item in enumerate(values):
                item.setToolTip(item.text())
                table.setItem(index, column, item)
            toggle = QPushButton("停用" if row.enabled else "啟用")
            toggle.setEnabled(row.available)
            toggle.setAccessibleName(f"{row.display_name} 啟用狀態")
            toggle.setToolTip(
                "立即啟用或停用此內建 MOD"
                if row.available
                else "MOD 未通過載入或完整性檢查"
            )
            toggle.clicked.connect(
                lambda _checked=False, selected=row.provider_id, enabled=not row.enabled: change_state(
                    selected, enabled
                )
            )
            table.setCellWidget(index, 4, toggle)
            table.setRowHeight(index, 52)

    refresh.clicked.connect(populate)
    populate()
    return panel
