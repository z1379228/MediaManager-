"""Trusted official-page workspaces for Instagram, Threads, and X/Twitter."""

from __future__ import annotations

from pathlib import Path

from core.archive_import import (
    ArchivePreview,
    extract_media_archive,
    preview_media_archive,
)
from core.localization import normalized_core_locale
from core.mod_groups import load_builtin_mod_group
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled
from trusted_ui.site_mod_catalog import (
    INSTAGRAM_EXPORT_HELP,
    THREADS_EXPORT_HELP,
    X_EXPORT_HELP,
    validated_instagram_url,
    validated_threads_url,
    validated_twitter_url,
)


_SITE_SETTINGS = {
    "instagram": {
        "page_id": "instagram-page",
        "export_id": "instagram-export",
        "export_url": INSTAGRAM_EXPORT_HELP,
        "validator": validated_instagram_url,
        "media_suffixes": frozenset(
            {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}
        ),
    },
    "threads": {
        "page_id": "threads-page",
        "export_id": "threads-export",
        "export_url": THREADS_EXPORT_HELP,
        "validator": validated_threads_url,
        "media_suffixes": frozenset(
            {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}
        ),
    },
    "twitter": {
        "page_id": "twitter-page",
        "export_id": "twitter-export",
        "export_url": X_EXPORT_HELP,
        "validator": validated_twitter_url,
        "media_suffixes": frozenset(
            {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}
        ),
    },
}

_ARCHIVE_TEXT = {
    "zh-TW": {
        "title": "官方封存 ZIP 本機匯入",
        "choose": "選擇官方封存 ZIP",
        "import": "匯入媒體並建立索引",
        "empty": "只讀取本機 ZIP；不會上傳、執行腳本或自動登入。",
    },
    "zh-CN": {
        "title": "官方存档 ZIP 本地导入",
        "choose": "选择官方存档 ZIP",
        "import": "导入媒体并建立索引",
        "empty": "只读取本地 ZIP；不会上传、执行脚本或自动登录。",
    },
    "en": {
        "title": "Local official-export ZIP import",
        "choose": "Choose official-export ZIP",
        "import": "Import media and build index",
        "empty": "Reads a local ZIP only; nothing is uploaded or executed.",
    },
    "ja": {
        "title": "公式エクスポート ZIP のローカル取込",
        "choose": "公式エクスポート ZIP を選択",
        "import": "メディアを取り込み索引を作成",
        "empty": "ローカル ZIP のみを読み取り、アップロードや実行はしません。",
    },
}


def create_official_social_workspace(
    context: object,
    parent: object = None,
    *,
    site_family: str,
) -> object:
    """Create an explicit-click official tool surface with no background access."""

    if site_family not in _SITE_SETTINGS:
        raise ValueError("unsupported official social site")

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QCheckBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QMessageBox,
        QVBoxLayout,
        QWidget,
    )

    class OfficialSocialWorkspace(QWidget):
        def __init__(self) -> None:
            super().__init__(parent)
            self.settings = _SITE_SETTINGS[site_family]
            self.events = getattr(context, "events", None)
            self.text: dict[str, str] = {}
            self.module_names: dict[str, str] = {}
            self.closing = False
            self.archive_preview: ArchivePreview | None = None

            layout = QVBoxLayout(self)
            layout.setContentsMargins(4, 8, 4, 4)
            layout.setSpacing(12)

            self.title = QLabel()
            self.title.setObjectName("sectionTitle")
            self.subtitle = QLabel()
            self.subtitle.setObjectName("sectionSubtitle")
            self.subtitle.setWordWrap(True)
            layout.addWidget(self.title)
            layout.addWidget(self.subtitle)

            self.boundary = QLabel()
            self.boundary.setObjectName("dependencySummary")
            self.boundary.setProperty("dependencyState", "ready")
            self.boundary.setWordWrap(True)
            layout.addWidget(self.boundary)

            child_card = QFrame()
            child_card.setObjectName("card")
            child_layout = QVBoxLayout(child_card)
            child_layout.setContentsMargins(16, 12, 16, 12)
            child_layout.setSpacing(8)
            child_title = QLabel("子 MOD")
            child_title.setObjectName("fieldLabel")
            child_layout.addWidget(child_title)
            self.page_toggle = QCheckBox()
            self.page_toggle.setObjectName(
                f"officialSocialToggle-{self.settings['page_id']}"
            )
            self.export_toggle = QCheckBox()
            self.export_toggle.setObjectName(
                f"officialSocialToggle-{self.settings['export_id']}"
            )
            child_layout.addWidget(self.page_toggle)
            child_layout.addWidget(self.export_toggle)
            layout.addWidget(child_card)

            tools = QFrame()
            tools.setObjectName("card")
            tools_layout = QVBoxLayout(tools)
            tools_layout.setContentsMargins(16, 12, 16, 12)
            tools_layout.setSpacing(8)
            self.url_label = QLabel()
            self.url_label.setObjectName("fieldLabel")
            self.url = QLineEdit()
            self.url.setObjectName(f"officialSocialUrl-{site_family}")
            self.open_page = QPushButton()
            self.open_page.setObjectName(f"officialSocialOpenPage-{site_family}")
            self.open_page.setProperty("kind", "primary")
            self.open_export = QPushButton()
            self.open_export.setObjectName(f"officialSocialOpenExport-{site_family}")
            actions = QHBoxLayout()
            actions.addWidget(self.open_page)
            actions.addWidget(self.open_export)
            actions.addStretch()
            tools_layout.addWidget(self.url_label)
            tools_layout.addWidget(self.url)
            tools_layout.addLayout(actions)
            self.status = QLabel()
            self.status.setObjectName("officialSocialStatus")
            self.status.setWordWrap(True)
            tools_layout.addWidget(self.status)
            layout.addWidget(tools)

            archive_card = QFrame()
            archive_card.setObjectName("card")
            archive_layout = QVBoxLayout(archive_card)
            archive_layout.setContentsMargins(16, 12, 16, 12)
            archive_layout.setSpacing(8)
            self.archive_title = QLabel()
            self.archive_title.setObjectName("fieldLabel")
            archive_layout.addWidget(self.archive_title)
            archive_actions = QHBoxLayout()
            self.archive_path = QLineEdit()
            self.archive_path.setObjectName(f"officialSocialArchive-{site_family}")
            self.archive_path.setReadOnly(True)
            archive_actions.addWidget(self.archive_path, 1)
            self.choose_archive = QPushButton()
            self.choose_archive.setObjectName(
                f"officialSocialChooseArchive-{site_family}"
            )
            archive_actions.addWidget(self.choose_archive)
            self.import_archive = QPushButton()
            self.import_archive.setObjectName(
                f"officialSocialImportArchive-{site_family}"
            )
            archive_actions.addWidget(self.import_archive)
            archive_layout.addLayout(archive_actions)
            self.archive_summary = QLabel()
            self.archive_summary.setObjectName("dependencySummary")
            self.archive_summary.setWordWrap(True)
            archive_layout.addWidget(self.archive_summary)
            layout.addWidget(archive_card)
            layout.addStretch()

            self.page_toggle.toggled.connect(
                lambda checked: self.set_child_enabled(
                    str(self.settings["page_id"]), checked
                )
            )
            self.export_toggle.toggled.connect(
                lambda checked: self.set_child_enabled(
                    str(self.settings["export_id"]), checked
                )
            )
            self.open_page.clicked.connect(self.open_official_page)
            self.open_export.clicked.connect(self.open_export_help)
            self.choose_archive.clicked.connect(self.select_archive)
            self.import_archive.clicked.connect(self.import_selected_archive)
            if self.events is not None:
                self.events.subscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.subscribe("ui.language.changed", self.apply_language)
            self.apply_language()
            self.refresh_state()

        def feature_state(self, provider_id: str) -> tuple[bool, bool]:
            try:
                statuses = context.features.statuses()
            except (AttributeError, RuntimeError):
                return False, False
            for status in statuses:
                if status.provider_id == provider_id:
                    return bool(status.available), bool(status.enabled)
            return False, False

        def apply_language(self, _payload: object = None) -> None:
            language = getattr(getattr(context, "settings", None), "language", "zh-TW")
            group = load_builtin_mod_group(site_family, locale=language)
            self.text = {**group.workspace, **group.ui}
            self.module_names = {
                module.provider_id: module.display_name for module in group.modules
            }
            self.title.setText(group.workspace["title"])
            self.subtitle.setText(group.workspace["subtitle"])
            self.boundary.setText(group.ui["boundary"])
            self.url_label.setText(group.workspace["url_label"])
            self.url.setPlaceholderText(group.workspace["placeholder"])
            self.page_toggle.setText(self.module_names[str(self.settings["page_id"])])
            self.export_toggle.setText(
                self.module_names[str(self.settings["export_id"])]
            )
            self.open_page.setText(group.ui["open_page"])
            self.open_export.setText(group.ui["open_export"])
            archive_text = _ARCHIVE_TEXT[normalized_core_locale(language)]
            self.archive_title.setText(archive_text["title"])
            self.choose_archive.setText(archive_text["choose"])
            self.import_archive.setText(archive_text["import"])
            if self.archive_preview is None:
                self.archive_summary.setText(archive_text["empty"])
            if not self.status.text():
                self.status.setText(group.workspace["initial_preview"])

        def refresh_state(self) -> None:
            parent_available, parent_enabled = self.feature_state(site_family)
            page_available, page_enabled = self.feature_state(
                str(self.settings["page_id"])
            )
            export_available, export_enabled = self.feature_state(
                str(self.settings["export_id"])
            )
            for toggle, available, enabled in (
                (self.page_toggle, page_available, page_enabled),
                (self.export_toggle, export_available, export_enabled),
            ):
                toggle.blockSignals(True)
                toggle.setChecked(enabled)
                toggle.setEnabled(parent_available and parent_enabled and available)
                toggle.blockSignals(False)
            self.open_page.setEnabled(parent_enabled and page_enabled)
            self.open_export.setEnabled(parent_enabled and export_enabled)
            self.choose_archive.setEnabled(parent_enabled and export_enabled)
            self.import_archive.setEnabled(
                parent_enabled
                and export_enabled
                and self.archive_preview is not None
                and bool(self.archive_preview.media_entries)
            )

        def set_child_enabled(self, provider_id: str, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(context, provider_id, enabled)
            except (KeyError, OSError, RuntimeError) as error:
                self.status.setText(str(error)[:300])
            self.refresh_state()

        def handle_mod_changed(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            provider_id = str(payload.get("provider_id", ""))
            if provider_id in {
                site_family,
                str(self.settings["page_id"]),
                str(self.settings["export_id"]),
            }:
                self.refresh_state()

        def open_official_page(self) -> None:
            _available, enabled = self.feature_state(str(self.settings["page_id"]))
            if not enabled:
                self.status.setText(self.text["page_disabled"])
                return
            validator = self.settings["validator"]
            target = validator(self.url.text())
            if target is None:
                self.status.setText(self.text["invalid_url"])
                return
            opened = QDesktopServices.openUrl(QUrl(str(target)))
            self.status.setText(
                self.text["opened_page"] if opened else self.text["browser_failed"]
            )

        def open_export_help(self) -> None:
            _available, enabled = self.feature_state(str(self.settings["export_id"]))
            if not enabled:
                self.status.setText(self.text["export_disabled"])
                return
            opened = QDesktopServices.openUrl(QUrl(str(self.settings["export_url"])))
            self.status.setText(
                self.text["opened_export"] if opened else self.text["browser_failed"]
            )

        def select_archive(self) -> None:
            _available, enabled = self.feature_state(str(self.settings["export_id"]))
            if not enabled:
                self.status.setText(self.text["export_disabled"])
                return
            filename, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "選擇官方封存 ZIP",
                "",
                "ZIP archive (*.zip)",
            )
            if not filename:
                return
            try:
                preview = preview_media_archive(
                    Path(filename),
                    allowed_media_suffixes=self.settings["media_suffixes"],
                )
            except (OSError, ValueError) as error:
                self.archive_preview = None
                self.archive_path.clear()
                self.archive_summary.setText(f"無法讀取封存檔：{error}")
                self.refresh_state()
                return
            self.archive_preview = preview
            self.archive_path.setText(str(preview.archive))
            media_bytes = sum(entry.size for entry in preview.media_entries)
            self.archive_summary.setText(
                f"可匯入媒體 {len(preview.media_entries)} 項（{media_bytes / 1024**2:.1f} MiB）；"
                f"另辨識 {preview.metadata_count} 個中繼資料檔。"
                "ZIP 結構只做安全檢查，不代表平台內容真實性驗證。"
            )
            self.refresh_state()

        def import_selected_archive(self) -> None:
            preview = self.archive_preview
            if preview is None:
                return
            destination = QFileDialog.getExistingDirectory(
                self,
                "選擇本機媒體索引資料夾",
                str(context.paths.downloads),
            )
            if not destination:
                return
            answer = QMessageBox.question(
                self,
                "確認匯入官方封存",
                f"將解壓 {len(preview.media_entries)} 個媒體檔並建立 media-index.json。\n"
                "不會匯入腳本、Cookie 或登入資料。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                extracted = extract_media_archive(
                    preview.archive,
                    Path(destination),
                    allowed_media_suffixes=self.settings["media_suffixes"],
                )
            except (OSError, ValueError) as error:
                self.status.setText(f"封存匯入失敗：{error}")
                return
            self.status.setText(
                f"已匯入 {len(extracted)} 個媒體檔，並建立本機 media-index.json。"
            )

        def shutdown(self) -> None:
            if self.closing:
                return
            self.closing = True
            if self.events is not None:
                self.events.unsubscribe("builtin_mod.changed", self.handle_mod_changed)
                self.events.unsubscribe("ui.language.changed", self.apply_language)

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return OfficialSocialWorkspace()
