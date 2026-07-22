"""Trusted UI for the localhost-only Gopeed and P2P transfer MODs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path


TRANSFER_WORKSPACE_LABEL = "Gopeed / P2P"


def create_transfer_panel(context: object, parent: object = None) -> object:
    """Create an explicit-action panel without starting Gopeed or opening ports."""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLayout,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    bridge = getattr(context, "gopeed", None)
    p2p = getattr(context, "p2p_transfer", None)
    if bridge is None or p2p is None:
        raise RuntimeError("Gopeed / P2P 服務無法使用")

    panel = QWidget(parent)
    shell = QVBoxLayout(panel)
    shell.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setObjectName("workspaceScroll")
    scroll.setAccessibleName("Gopeed 與 P2P 傳輸工作區捲動內容")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll_content = QWidget()
    page = QVBoxLayout(scroll_content)
    page.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)
    scroll.setWidget(scroll_content)
    shell.addWidget(scroll)

    title = QLabel(TRANSFER_WORKSPACE_LABEL)
    title.setObjectName("sectionTitle")
    subtitle = QLabel(
        "只連線至使用者自行啟動的 localhost Gopeed REST API。MediaManager "
        "不啟動 Gopeed、不開放遠端連線、不自動開埠，也不保存 API Token。"
    )
    subtitle.setObjectName("sectionSubtitle")
    subtitle.setWordWrap(True)
    page.addWidget(title)
    page.addWidget(subtitle)

    bridge_card = QFrame()
    bridge_card.setObjectName("card")
    bridge_layout = QVBoxLayout(bridge_card)
    bridge_title = QLabel("Gopeed Bridge")
    bridge_title.setObjectName("cardTitle")
    bridge_layout.addWidget(bridge_title)
    bridge_form = QFormLayout()
    endpoint = QLineEdit(bridge.config.endpoint)
    endpoint.setPlaceholderText("http://127.0.0.1:9999")
    token = QLineEdit()
    token.setEchoMode(QLineEdit.EchoMode.Password)
    token.setPlaceholderText("本次工作階段 API Token（至少 32 字元）")
    timeout = QSpinBox()
    timeout.setRange(1, 60)
    timeout.setValue(10)
    timeout.setSuffix(" 秒")
    task_limit = QSpinBox()
    task_limit.setRange(1, 16)
    task_limit.setValue(4)
    bridge_form.addRow("本機 API", endpoint)
    bridge_form.addRow("API Token", token)
    bridge_form.addRow("逾時", timeout)
    bridge_form.addRow("同時工作上限", task_limit)
    bridge_layout.addLayout(bridge_form)
    bridge_actions = QHBoxLayout()
    apply_bridge = QPushButton("套用本次工作階段")
    test_bridge = QPushButton("測試連線")
    bridge_status = QLabel("尚未設定；啟用 MOD 不會自動連線。")
    bridge_status.setObjectName("muted")
    bridge_status.setWordWrap(True)
    bridge_actions.addWidget(bridge_status, 1)
    bridge_actions.addWidget(apply_bridge)
    bridge_actions.addWidget(test_bridge)
    bridge_layout.addLayout(bridge_actions)
    page.addWidget(bridge_card)

    direct_card = QFrame()
    direct_card.setObjectName("card")
    direct_layout = QVBoxLayout(direct_card)
    direct_title = QLabel("HTTPS 直接檔案傳輸")
    direct_title.setObjectName("cardTitle")
    direct_layout.addWidget(direct_title)
    direct_url = QLineEdit()
    direct_url.setPlaceholderText("使用者明確提供、非網站 MOD 網域的 https:// 直接檔案網址")
    direct_name = QLineEdit()
    direct_name.setPlaceholderText("可選檔名；不可包含路徑")
    direct_output = QLineEdit()
    direct_output.setReadOnly(True)
    direct_output.setPlaceholderText("選擇已存在的下載資料夾")
    choose_direct_output = QPushButton("選擇資料夾")
    direct_output_row = QHBoxLayout()
    direct_output_row.addWidget(direct_output, 1)
    direct_output_row.addWidget(choose_direct_output)
    submit_direct = QPushButton("交給 Gopeed")
    submit_direct.setObjectName("primary")
    direct_layout.addWidget(direct_url)
    direct_layout.addWidget(direct_name)
    direct_layout.addLayout(direct_output_row)
    direct_layout.addWidget(submit_direct, alignment=Qt.AlignmentFlag.AlignRight)
    page.addWidget(direct_card)

    p2p_card = QFrame()
    p2p_card.setObjectName("card")
    p2p_layout = QVBoxLayout(p2p_card)
    p2p_title = QLabel("P2P Transfer")
    p2p_title.setObjectName("cardTitle")
    p2p_note = QLabel(
        "只接受使用者明確提供的 magnet 或 ed2k 連結；不提供搜尋、不自動開埠。"
        "P2P 會上傳資料，必須明確確認合法使用與上傳行為。下列頻寬值是本機政策紀錄；"
        "Gopeed 目前仍需由使用者在其設定中套用實際限速。"
    )
    p2p_note.setObjectName("muted")
    p2p_note.setWordWrap(True)
    p2p_layout.addWidget(p2p_title)
    p2p_layout.addWidget(p2p_note)
    p2p_url = QLineEdit()
    p2p_url.setPlaceholderText("magnet:?xt=urn:btih:… 或 ed2k://|file|…|/")
    p2p_name = QLineEdit()
    p2p_name.setPlaceholderText("可選工作名稱；不可包含路徑")
    p2p_output = QLineEdit()
    p2p_output.setReadOnly(True)
    p2p_output.setPlaceholderText("選擇已存在的儲存資料夾")
    choose_p2p_output = QPushButton("選擇資料夾")
    p2p_output_row = QHBoxLayout()
    p2p_output_row.addWidget(p2p_output, 1)
    p2p_output_row.addWidget(choose_p2p_output)
    policy_form = QFormLayout()
    storage_limit = QSpinBox()
    storage_limit.setRange(1, 1024)
    storage_limit.setValue(10)
    storage_limit.setSuffix(" GiB")
    download_limit = QSpinBox()
    download_limit.setRange(1, 10240)
    download_limit.setValue(10)
    download_limit.setSuffix(" MiB/s")
    upload_limit = QSpinBox()
    upload_limit.setRange(1, 10240)
    upload_limit.setValue(1)
    upload_limit.setSuffix(" MiB/s")
    policy_form.addRow("單一資源容量上限", storage_limit)
    policy_form.addRow("下載政策值", download_limit)
    policy_form.addRow("上傳政策值", upload_limit)
    legal_use = QCheckBox("我確認只傳輸有權使用的內容")
    upload_ack = QCheckBox("我了解 P2P 會上傳資料")
    submit_p2p = QPushButton("解析大小後交給 Gopeed")
    submit_p2p.setObjectName("primary")
    p2p_layout.addWidget(p2p_url)
    p2p_layout.addWidget(p2p_name)
    p2p_layout.addLayout(p2p_output_row)
    p2p_layout.addLayout(policy_form)
    p2p_layout.addWidget(legal_use)
    p2p_layout.addWidget(upload_ack)
    p2p_layout.addWidget(submit_p2p, alignment=Qt.AlignmentFlag.AlignRight)
    page.addWidget(p2p_card)

    tasks_card = QFrame()
    tasks_card.setObjectName("card")
    tasks_layout = QVBoxLayout(tasks_card)
    task_table = QTableWidget(0, 4)
    task_table.setHorizontalHeaderLabels(("工作 ID", "名稱", "狀態", "進度"))
    task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    task_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    task_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )
    task_controls = QHBoxLayout()
    refresh_tasks = QPushButton("重新整理")
    pause_task = QPushButton("暫停")
    continue_task = QPushButton("繼續")
    delete_task = QPushButton("移除工作（保留檔案）")
    task_controls.addStretch(1)
    for button in (refresh_tasks, pause_task, continue_task, delete_task):
        task_controls.addWidget(button)
    tasks_layout.addWidget(QLabel("Gopeed 工作"))
    tasks_layout.addWidget(task_table)
    tasks_layout.addLayout(task_controls)
    page.addWidget(tasks_card, 1)

    def show_error(error: Exception) -> None:
        QMessageBox.warning(panel, TRANSFER_WORKSPACE_LABEL, str(error))

    def apply_bridge_config() -> None:
        bridge.configure(
            {
                "enabled": True,
                "endpoint": endpoint.text().strip(),
                "token": token.text(),
                "request_timeout_seconds": timeout.value(),
                "max_tasks": task_limit.value(),
                "auto_start": False,
                "allow_remote": False,
            }
        )
        bridge_status.setText("已套用至記憶體；關閉 MOD 或程式後 Token 會清除。")

    def choose_folder(target: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(panel, "選擇資料夾")
        if selected:
            target.setText(str(Path(selected).resolve()))

    def selected_task_id() -> str:
        row = task_table.currentRow()
        if row < 0:
            raise ValueError("請先選擇 Gopeed 工作")
        item = task_table.item(row, 0)
        value = item.text() if item is not None else ""
        if not value:
            raise ValueError("選取工作沒有有效 ID")
        return value

    def task_name(task: Mapping[str, object]) -> str:
        name = task.get("name")
        if isinstance(name, str):
            return name
        meta = task.get("meta")
        if isinstance(meta, Mapping) and isinstance(meta.get("name"), str):
            return str(meta["name"])
        return ""

    def render_tasks() -> None:
        tasks = bridge.list_tasks()
        task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            progress = task.get("progress", "")
            values = (
                str(task.get("id", "")),
                task_name(task),
                str(task.get("status", "")),
                str(progress),
            )
            for column, value in enumerate(values):
                task_table.setItem(row, column, QTableWidgetItem(value))

    def run(action: Callable[[], object], *, refresh: bool = False) -> None:
        try:
            action()
            if refresh:
                render_tasks()
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            show_error(error)

    apply_bridge.clicked.connect(lambda: run(apply_bridge_config))
    test_bridge.clicked.connect(
        lambda: run(
            lambda: (
                apply_bridge_config(),
                bridge.info(),
                bridge_status.setText("Gopeed localhost API 連線成功。"),
            )
        )
    )
    choose_direct_output.clicked.connect(lambda: choose_folder(direct_output))
    choose_p2p_output.clicked.connect(lambda: choose_folder(p2p_output))
    submit_direct.clicked.connect(
        lambda: run(
            lambda: (
                apply_bridge_config(),
                bridge.create_download(
                    direct_url.text().strip(),
                    direct_output.text(),
                    name=direct_name.text().strip(),
                ),
            ),
            refresh=True,
        )
    )

    def submit_p2p_task() -> None:
        apply_bridge_config()
        p2p.configure(
            {
                "enabled": True,
                "storage_root": p2p_output.text(),
                "max_storage_bytes": storage_limit.value() * 1024**3,
                "max_download_bps": download_limit.value() * 1024**2,
                "max_upload_bps": upload_limit.value() * 1024**2,
                "legal_use_confirmed": legal_use.isChecked(),
                "upload_enabled": upload_ack.isChecked(),
                "seeding_enabled": False,
                "search_enabled": False,
                "auto_port_forward": False,
            }
        )
        p2p.submit(p2p_url.text().strip(), name=p2p_name.text().strip())

    submit_p2p.clicked.connect(
        lambda: run(submit_p2p_task, refresh=True)
    )
    refresh_tasks.clicked.connect(lambda: run(render_tasks))
    pause_task.clicked.connect(
        lambda: run(lambda: bridge.pause_task(selected_task_id()), refresh=True)
    )
    continue_task.clicked.connect(
        lambda: run(lambda: bridge.continue_task(selected_task_id()), refresh=True)
    )
    delete_task.clicked.connect(
        lambda: run(lambda: bridge.delete_task(selected_task_id()), refresh=True)
    )

    panel.title = title
    panel.scroll_area = scroll
    panel.scroll_content = scroll_content
    panel.endpoint = endpoint
    panel.token = token
    panel.task_table = task_table
    panel.refresh_tasks = refresh_tasks
    return panel
