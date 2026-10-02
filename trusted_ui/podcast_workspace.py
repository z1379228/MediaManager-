"""Trusted UI for bounded local Podcast RSS and Atom import."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from core.downloads.direct_http_policy import direct_http_url_candidate
from core.podcast_import import (
    PodcastFeed,
    export_podcast_feed,
    podcast_resource_preview_lines,
)
from trusted_ui.builtin_mod_control import set_builtin_mod_enabled


MAX_PODCAST_HANDOFF = 100


def compatible_podcast_episode_indices(feed: PodcastFeed) -> tuple[int, ...]:
    """Return entries that can use the existing strict Direct HTTP MOD."""

    return tuple(
        index
        for index, episode in enumerate(feed.episodes)
        if direct_http_url_candidate(episode.enclosure_url)
    )


def create_podcast_workspace(
    context: object,
    handoff: Callable[[tuple[str, ...], str], bool],
    parent: object = None,
) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class PodcastWorkspace(QWidget):
        provider_id = "podcast-import"

        def __init__(self) -> None:
            super().__init__(parent)
            self.feed: PodcastFeed | None = None
            self.events = getattr(context, "events", None)

            page = QVBoxLayout(self)
            page.setContentsMargins(2, 4, 2, 2)
            page.setSpacing(12)

            heading = QHBoxLayout()
            titles = QVBoxLayout()
            title = QLabel("Podcast / RSS 匯入")
            title.setObjectName("sectionTitle")
            subtitle = QLabel(
                "只讀取使用者選取的本機 RSS／Atom 檔案；不連線、不訂閱，"
                "選取單集後才交給 Direct HTTP 檢查。"
            )
            subtitle.setObjectName("sectionSubtitle")
            subtitle.setWordWrap(True)
            titles.addWidget(title)
            titles.addWidget(subtitle)
            heading.addLayout(titles, 1)
            self.badge = QLabel()
            self.badge.setObjectName("providerBadge")
            heading.addWidget(self.badge)
            page.addLayout(heading)

            card = QFrame()
            card.setObjectName("card")
            form = QVBoxLayout(card)
            form.setContentsMargins(16, 14, 16, 14)
            form.setSpacing(10)

            self.enabled = QCheckBox("啟用 Podcast / RSS MOD")
            self.enabled.setObjectName("podcastImportEnabled")
            self.enabled.setAccessibleName("Podcast / RSS MOD 啟用狀態")
            self.enabled.toggled.connect(self.toggle_provider)
            form.addWidget(self.enabled)

            source_row = QHBoxLayout()
            source_row.addWidget(QLabel("本機 Feed"))
            self.source = QLineEdit()
            self.source.setReadOnly(True)
            self.source.setAccessibleName("Podcast RSS 或 Atom 本機檔案")
            self.source.setPlaceholderText("選擇 .rss、.xml 或 .atom，最大 2 MiB")
            source_row.addWidget(self.source, 1)
            choose = QPushButton("選擇檔案")
            choose.setAccessibleName("選擇 Podcast Feed 檔案")
            choose.clicked.connect(self.choose_source)
            source_row.addWidget(choose)
            self.load = QPushButton("讀取與預覽")
            self.load.setObjectName("primary")
            self.load.setAccessibleName("讀取 Podcast Feed 並預覽")
            self.load.clicked.connect(self.load_feed)
            source_row.addWidget(self.load)
            form.addLayout(source_row)

            self.summary = QLabel("尚未選擇 Podcast Feed。")
            self.summary.setObjectName("preview")
            self.summary.setAccessibleName("Podcast Feed 讀取摘要")
            self.summary.setWordWrap(True)
            self.summary.setTextFormat(Qt.TextFormat.PlainText)
            form.addWidget(self.summary)
            page.addWidget(card)

            filter_row = QHBoxLayout()
            self.filter = QLineEdit()
            self.filter.setObjectName("podcastEpisodeFilter")
            self.filter.setAccessibleName("篩選 Podcast 單集")
            self.filter.setPlaceholderText("篩選單集名稱、作者或日期…")
            self.filter.setClearButtonEnabled(True)
            self.filter.textChanged.connect(self.apply_filter)
            filter_row.addWidget(self.filter, 1)
            self.visible_count = QLabel("顯示 0／0 集")
            self.visible_count.setObjectName("muted")
            self.visible_count.setAccessibleName("Podcast 單集顯示數量")
            filter_row.addWidget(self.visible_count)
            page.addLayout(filter_row)

            self.table = QTableWidget(0, 5)
            self.table.setObjectName("podcastEpisodeTable")
            self.table.setAccessibleName("Podcast 單集預覽")
            self.table.setHorizontalHeaderLabels(
                ("選取", "單集", "作者／日期", "媒體", "逐字稿／章節")
            )
            self.table.verticalHeader().hide()
            self.table.setAlternatingRowColors(True)
            self.table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.itemChanged.connect(self.update_actions)
            self.table.itemSelectionChanged.connect(self.update_actions)
            header = self.table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 70)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            page.addWidget(self.table, 1)

            controls = QHBoxLayout()
            self.select_compatible = QPushButton("選取可下載項目")
            self.select_compatible.clicked.connect(self.select_visible)
            controls.addWidget(self.select_compatible)
            self.clear_selection = QPushButton("清除選取")
            self.clear_selection.setObjectName("ghost")
            self.clear_selection.clicked.connect(self.clear_selected)
            controls.addWidget(self.clear_selection)
            self.show_issues = QPushButton("查看略過原因")
            self.show_issues.setObjectName("ghost")
            self.show_issues.clicked.connect(self.show_feed_issues)
            controls.addWidget(self.show_issues)
            self.preview_resources = QPushButton("預覽逐字稿／章節")
            self.preview_resources.setObjectName("ghost")
            self.preview_resources.setAccessibleName("預覽 Podcast 逐字稿與章節資源")
            self.preview_resources.clicked.connect(self.preview_resources_for_selected)
            controls.addWidget(self.preview_resources)
            self.export_m3u = QPushButton("匯出 M3U…")
            self.export_m3u.setObjectName("ghost")
            self.export_m3u.clicked.connect(lambda: self.export_feed("m3u"))
            controls.addWidget(self.export_m3u)
            self.export_csv = QPushButton("匯出 CSV…")
            self.export_csv.setObjectName("ghost")
            self.export_csv.clicked.connect(lambda: self.export_feed("csv"))
            controls.addWidget(self.export_csv)
            controls.addStretch()
            self.handoff = QPushButton("送至 Direct HTTP 檢查")
            self.handoff.setObjectName("primary")
            self.handoff.setAccessibleName("將選取 Podcast 單集送至 Direct HTTP")
            self.handoff.clicked.connect(self.handoff_selected)
            controls.addWidget(self.handoff)
            page.addLayout(controls)

            if self.events is not None:
                self.events.subscribe(
                    "builtin_mod.changed",
                    self.handle_mod_changed,
                )
            self.sync_provider()
            self.update_actions()

        def sync_provider(self) -> None:
            status = next(
                (
                    item
                    for item in context.features.statuses()
                    if item.provider_id == self.provider_id
                ),
                None,
            )
            self.enabled.blockSignals(True)
            self.enabled.setEnabled(bool(status and status.available))
            self.enabled.setChecked(bool(status and status.enabled))
            self.enabled.blockSignals(False)
            state = (
                "已啟用"
                if status and status.enabled
                else "已停用"
                if status
                else "不可用"
            )
            self.badge.setText(f"Podcast / RSS MOD {state}")
            self.badge.setProperty("active", bool(status and status.enabled))
            self.badge.style().unpolish(self.badge)
            self.badge.style().polish(self.badge)

        def toggle_provider(self, enabled: bool) -> None:
            try:
                set_builtin_mod_enabled(context, self.provider_id, enabled)
            except (KeyError, OSError, RuntimeError) as error:
                self.summary.setText(str(error)[:300])
            self.sync_provider()
            self.update_actions()

        def handle_mod_changed(self, payload: object) -> None:
            if (
                isinstance(payload, dict)
                and payload.get("provider_id") == self.provider_id
            ):
                self.sync_provider()
                self.update_actions()

        def choose_source(self) -> None:
            selected, _filter = QFileDialog.getOpenFileName(
                self,
                "選擇 Podcast RSS 或 Atom",
                str(Path.home()),
                "Podcast Feed (*.rss *.xml *.atom)",
            )
            if selected:
                self.source.setText(selected)
                self.summary.setText("已選擇本機檔案；按「讀取與預覽」解析。")
                self.load.setFocus()
            self.update_actions()

        def load_feed(self) -> None:
            service = getattr(context, "podcast_import", None)
            path = Path(self.source.text())
            if service is None:
                self.summary.setText("Podcast / RSS MOD 未正確載入。")
                return
            try:
                feed = service.parse(path)
            except (OSError, RuntimeError, ValueError) as error:
                self.feed = None
                self.table.setRowCount(0)
                self.summary.setText(f"Feed 無法讀取：{error}")
                self.apply_filter()
                self.update_actions()
                return
            self.feed = feed
            self.populate()

        def populate(self) -> None:
            feed = self.feed
            self.table.blockSignals(True)
            try:
                self.table.setRowCount(len(feed.episodes) if feed else 0)
                if feed is None:
                    return
                compatible = set(compatible_podcast_episode_indices(feed))
                for row, episode in enumerate(feed.episodes):
                    choose = QTableWidgetItem("可下載" if row in compatible else "僅預覽")
                    choose.setData(Qt.ItemDataRole.UserRole, row)
                    if row in compatible:
                        choose.setFlags(
                            choose.flags() | Qt.ItemFlag.ItemIsUserCheckable
                        )
                        choose.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        choose.setFlags(choose.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    self.table.setItem(row, 0, choose)
                    self.table.setItem(row, 1, QTableWidgetItem(episode.title))
                    author_date = " · ".join(
                        value
                        for value in (episode.author, episode.published)
                        if value
                    ) or "—"
                    self.table.setItem(row, 2, QTableWidgetItem(author_date))
                    media = episode.enclosure_type or (
                        "HTTPS 媒體" if episode.enclosure_url else "沒有媒體附件"
                    )
                    self.table.setItem(row, 3, QTableWidgetItem(media))
                    resources = []
                    if episode.transcripts:
                        resources.append(f"逐字稿 {len(episode.transcripts)}")
                    if episode.chapters is not None:
                        resources.append("章節")
                    self.table.setItem(
                        row,
                        4,
                        QTableWidgetItem(" · ".join(resources) or "—"),
                    )
                    for column in range(5):
                        item = self.table.item(row, column)
                        if item is not None:
                            item.setToolTip(
                                "\n".join(
                                    value
                                    for value in (
                                        episode.title,
                                        episode.enclosure_url,
                                        "可交給 Direct HTTP 檢查"
                                        if row in compatible
                                        else "附件不符合 Direct HTTP 明確 HTTPS 檔案規則",
                                    )
                                    if value
                                )
                            )
                    self.table.setRowHeight(row, 40)
            finally:
                self.table.blockSignals(False)
            compatible_count = len(compatible_podcast_episode_indices(feed))
            self.summary.setText(
                f"{feed.title} · {feed.source_format} · {len(feed.episodes)} 集 · "
                f"{compatible_count} 集可交給 Direct HTTP · {len(feed.issues)} 項略過說明。"
            )
            self.summary.setToolTip(feed.description)
            self.apply_filter()
            self.update_actions()

        def apply_filter(self, _value: str = "") -> None:
            query = self.filter.text().strip().casefold()
            feed = self.feed
            visible = 0
            total = len(feed.episodes) if feed else 0
            for row in range(total):
                episode = feed.episodes[row]
                text = " ".join(
                    (
                        episode.title,
                        episode.author,
                        episode.published,
                        episode.enclosure_type,
                    )
                ).casefold()
                matched = not query or query in text
                self.table.setRowHidden(row, not matched)
                visible += int(matched)
            self.visible_count.setText(f"顯示 {visible}／{total} 集")

        def select_visible(self) -> None:
            feed = self.feed
            if feed is None:
                return
            compatible = set(compatible_podcast_episode_indices(feed))
            selected = 0
            self.table.blockSignals(True)
            try:
                for row in range(len(feed.episodes)):
                    item = self.table.item(row, 0)
                    should_select = (
                        row in compatible
                        and not self.table.isRowHidden(row)
                        and selected < MAX_PODCAST_HANDOFF
                    )
                    if item is not None and row in compatible:
                        item.setCheckState(
                            Qt.CheckState.Checked
                            if should_select
                            else Qt.CheckState.Unchecked
                        )
                    selected += int(should_select)
            finally:
                self.table.blockSignals(False)
            self.summary.setText(
                f"已選取 {selected} 集；單次最多送出 {MAX_PODCAST_HANDOFF} 集。"
            )
            self.update_actions()

        def clear_selected(self) -> None:
            self.table.blockSignals(True)
            try:
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if item is not None and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        item.setCheckState(Qt.CheckState.Unchecked)
            finally:
                self.table.blockSignals(False)
            self.update_actions()

        def selected_urls(self) -> tuple[str, ...]:
            feed = self.feed
            if feed is None:
                return ()
            urls = []
            for row, episode in enumerate(feed.episodes):
                item = self.table.item(row, 0)
                if item is not None and item.checkState() == Qt.CheckState.Checked:
                    urls.append(episode.enclosure_url)
            return tuple(dict.fromkeys(urls))[:MAX_PODCAST_HANDOFF]

        def selected_episode(self) -> object | None:
            feed = self.feed
            row = self.table.currentRow()
            if feed is None or row < 0 or row >= len(feed.episodes):
                return None
            return feed.episodes[row]

        def update_actions(self, _item: object = None) -> None:
            enabled = bool(
                getattr(getattr(context, "podcast_import", None), "is_enabled", False)
            )
            has_source = bool(self.source.text())
            compatible = (
                len(compatible_podcast_episode_indices(self.feed))
                if self.feed is not None
                else 0
            )
            self.load.setEnabled(enabled and has_source)
            self.select_compatible.setEnabled(enabled and bool(compatible))
            self.clear_selection.setEnabled(bool(self.selected_urls()))
            self.show_issues.setEnabled(bool(self.feed and self.feed.issues))
            selected = self.selected_episode()
            self.preview_resources.setEnabled(
                bool(selected and podcast_resource_preview_lines(selected))
            )
            self.export_m3u.setEnabled(bool(self.feed))
            self.export_csv.setEnabled(bool(self.feed))
            self.handoff.setEnabled(enabled and bool(self.selected_urls()))

        def show_feed_issues(self) -> None:
            if self.feed is None or not self.feed.issues:
                return
            visible = self.feed.issues[:20]
            suffix = (
                f"\n另有 {len(self.feed.issues) - len(visible)} 項。"
                if len(self.feed.issues) > len(visible)
                else ""
            )
            QMessageBox.information(
                self,
                "Podcast Feed 略過原因",
                "\n".join(visible) + suffix,
            )

        def preview_resources_for_selected(self) -> None:
            episode = self.selected_episode()
            if episode is None:
                return
            lines = podcast_resource_preview_lines(episode)
            if not lines:
                return
            QMessageBox.information(
                self,
                "逐字稿／章節資源預覽",
                "\n\n".join(lines)
                + "\n\n僅顯示 Feed 宣告的本機解析結果；不會連線或下載資源。",
            )

        def export_feed(self, format_id: str) -> None:
            feed = self.feed
            if feed is None:
                return
            defaults = {
                "m3u": ("podcast-episodes.m3u8", "M3U 播放清單 (*.m3u8)"),
                "csv": ("podcast-episodes.csv", "CSV 表格 (*.csv)"),
            }
            suggested, file_filter = defaults[format_id]
            filename, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "匯出 Podcast Feed",
                suggested,
                file_filter,
            )
            if not filename:
                return
            try:
                destination = export_podcast_feed(feed, Path(filename), format_id)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "Podcast 匯出失敗", str(error))
                return
            self.summary.setText(
                f"已匯出 {len(feed.episodes)} 集至本機檔案：{destination.name}"
            )

        def handoff_selected(self) -> None:
            urls = self.selected_urls()
            if not urls or self.feed is None:
                return
            try:
                accepted = handoff(urls, self.feed.title)
            except (RuntimeError, ValueError) as error:
                self.summary.setText(f"無法交付 Direct HTTP：{error}")
                return
            if not accepted:
                self.summary.setText(
                    "Direct HTTP MOD 目前不可用或未啟用；請先在 MOD 管理中檢查。"
                )
                return
            self.summary.setText(
                f"已送出 {len(urls)} 集至 Direct HTTP；請確認輸出位置後再加入佇列。"
            )
            self.clear_selected()

        def shutdown(self) -> None:
            if self.events is not None:
                self.events.unsubscribe(
                    "builtin_mod.changed",
                    self.handle_mod_changed,
                )

        def closeEvent(self, event: object) -> None:
            self.shutdown()
            super().closeEvent(event)

    return PodcastWorkspace()
