"""UI for the optional local Media Convert MOD."""

from __future__ import annotations

import math
from pathlib import Path
import threading

from core.conversion import (
    ConversionCapabilities,
    ConversionRequest,
    ConversionState,
    MediaHealthReport,
    MediaInspection,
    MediaStreamInfo,
)
from core.drop_intake import DropIntake
from trusted_ui.drop_intake import install_drop_intake, issue_summary
from trusted_ui.table_refresh import task_table_interval, visible_rows_signature
from trusted_ui.idle_state import (
    PAUSE_IN_BACKGROUND_PROPERTY,
    is_background_idle,
)


CONVERSION_WORKSPACE_LABEL = "格式工廠"


def accepted_conversion_drop_sources(intake: DropIntake) -> tuple[Path, ...]:
    """Return media-only drop sources without mutating or starting work."""

    if intake.urls or intake.batch_files:
        raise ValueError("格式工廠來源只接受本機媒體檔案")
    if not intake.media_files:
        detail = issue_summary(intake)
        raise ValueError(
            "拖放內容沒有可用的本機媒體" + (f"：{detail}" if detail else "")
        )
    return intake.media_files


def _time_seconds(value: str) -> float:
    token = value.strip()
    if not token:
        raise ValueError("時間不可留空")
    parts = token.split(":")
    if len(parts) > 3:
        raise ValueError(f"無效時間：{value}")
    try:
        numbers = tuple(float(part) for part in parts)
    except ValueError as error:
        raise ValueError(f"無效時間：{value}") from error
    if any(not math.isfinite(number) or number < 0 for number in numbers):
        raise ValueError(f"無效時間：{value}")
    if len(numbers) > 1 and any(number >= 60 for number in numbers[1:]):
        raise ValueError(f"分與秒必須小於 60：{value}")
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def parse_removal_ranges(value: str) -> tuple[tuple[float, float], ...]:
    """Parse ``start-end`` ranges using seconds or HH:MM:SS values."""

    normalized = value.replace("；", ";").replace("\n", ";").strip()
    if not normalized:
        return ()
    ranges: list[tuple[float, float]] = []
    for raw_range in normalized.split(";"):
        item = raw_range.strip()
        if not item:
            continue
        if item.count("-") != 1:
            raise ValueError(f"區間格式應為 開始-結束：{item}")
        start, end = (_time_seconds(part) for part in item.split("-", 1))
        ranges.append((start, end))
    if len(ranges) > 50:
        raise ValueError("最多可輸入 50 個剪除區間")
    return tuple(ranges)


def create_conversion_panel(context: object, parent: object = None) -> object:
    from PySide6.QtCore import QObject, QSignalBlocker, Qt, QTimer, QUrl, Signal
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from trusted_ui.builtin_mod_control import (
        builtin_mod_is_enabled,
        set_builtin_mod_enabled,
    )

    service = context.conversion
    if service is None:
        raise RuntimeError(f"{CONVERSION_WORKSPACE_LABEL}服務無法使用")
    panel = QWidget(parent)
    panel.sources = []
    panel.render_signature = None
    panel.preview_dialog = None
    panel.output_sample_dialog = None
    panel.output_sample_path = None
    panel.inspection_generation = 0
    panel.inspection_requested_source = None
    panel.inspection = None
    panel.auxiliary_generation = 0
    panel.auxiliary_cancel_event = None
    panel.auxiliary_busy = False
    panel.capability_generation = 0
    panel.capability_busy = False
    panel.capability_cancel_event = None
    panel.detected_encoders = frozenset()
    panel.detected_filters = frozenset()
    panel.closing = False

    class InspectionBridge(QObject):
        finished = Signal(int, object, str)

    class AuxiliaryBridge(QObject):
        finished = Signal(int, str, object, str)

    class CapabilityBridge(QObject):
        finished = Signal(int, object, str)

    inspection_bridge = InspectionBridge(panel)
    auxiliary_bridge = AuxiliaryBridge(panel)
    capability_bridge = CapabilityBridge(panel)
    page = QVBoxLayout(panel)
    page.setContentsMargins(2, 4, 2, 2)
    page.setSpacing(12)

    title = QLabel(CONVERSION_WORKSPACE_LABEL)
    title.setObjectName("sectionTitle")
    subtitle = QLabel(
        "使用本機 FFmpeg 轉封裝、轉檔與剪輯；工作可取消、先寫入 .part，"
        "完成後才建立輸出檔。"
    )
    subtitle.setObjectName("sectionSubtitle")
    subtitle.setWordWrap(True)
    page.addWidget(title)
    page.addWidget(subtitle)

    guide = QLabel(
        "使用方式：先選擇來源和輸出位置，再選格式；影音與靜態影像都由本機 FFmpeg 處理。"
        "Local Ad Segment Trim 是可獨立停用的"
        "子 MOD，只接受本機檔案與手動時間區間，不會存取網站或繞過廣告限制；"
        "輸出一定是新檔，不覆寫原檔。"
    )
    guide.setObjectName("modUsageGuide")
    guide.setWordWrap(True)
    page.addWidget(guide)

    capability_row = QHBoxLayout()
    capability_note = QLabel(
        "尚未偵測本機 FFmpeg 能力；未取得 encoder 證據前只使用 CPU。"
    )
    capability_note.setObjectName("muted")
    capability_note.setWordWrap(True)
    refresh_capabilities = QPushButton("偵測本機轉檔能力")
    capability_row.addWidget(capability_note, 1)
    capability_row.addWidget(refresh_capabilities)
    page.addLayout(capability_row)
    panel.gpu_available = False
    panel.hevc_nvenc_available = False

    card = QFrame()
    card.setObjectName("card")
    form = QVBoxLayout(card)
    form.setSpacing(10)

    source_row = QHBoxLayout()
    source_text = QLineEdit()
    source_text.setReadOnly(True)
    source_text.setPlaceholderText("尚未選擇本機媒體")
    choose_sources = QPushButton("選擇來源")
    source_row.addWidget(source_text, 1)
    source_row.addWidget(choose_sources)
    form.addLayout(source_row)

    track_card = QFrame()
    track_card.setObjectName("subtleCard")
    track_layout = QGridLayout(track_card)
    track_layout.setContentsMargins(12, 10, 12, 10)
    track_label = QLabel("無損軌道")
    track_label.setObjectName("fieldLabel")
    track_select = QComboBox()
    track_select.setAccessibleName("無損輸出音訊或字幕軌道")
    track_select.setEnabled(False)
    inspect_again = QPushButton("重新檢查")
    inspect_again.setObjectName("ghost")
    inspect_again.setEnabled(False)
    track_status = QLabel("選擇單一來源後，才會在背景讀取音訊與字幕軌。")
    track_status.setObjectName("sectionSubtitle")
    track_status.setWordWrap(True)
    track_layout.addWidget(track_label, 0, 0)
    track_layout.addWidget(track_select, 0, 1)
    track_layout.addWidget(inspect_again, 0, 2)
    track_layout.addWidget(track_status, 1, 0, 1, 3)
    form.addWidget(track_card)

    option_grid = QGridLayout()
    option_grid.setColumnStretch(1, 1)
    option_grid.setColumnStretch(5, 1)
    preset = QComboBox()
    labels = {
        "remux-copy": "串流複製封裝",
        "stream-copy-matroska": "無損選取音訊／字幕軌",
        "split-copy": "依時間切割",
        "join-copy": "相同格式串接",
        "video-h264": "H.264 相容轉檔",
        "compress-h265": "H.265 CPU 壓縮",
        "video-h264-target-size": "H.264 目標容量（兩階段）",
        "video-h264-qsv": "H.264 Intel Quick Sync",
        "video-hevc-qsv": "H.265 Intel Quick Sync",
        "video-h264-amf": "H.264 AMD AMF",
        "video-hevc-amf": "H.265 AMD AMF",
        "video-av1-nvenc": "AV1 NVIDIA NVENC",
        "video-av1-qsv": "AV1 Intel Quick Sync",
        "video-av1-amf": "AV1 AMD AMF",
        "hevc10-nvenc-opus-copy": "H.265 10-bit NVENC 300 kbps／Opus Passthru（MKV）",
        "watermark-h264": "影片加本機影像浮水印",
        "video-vp9-webm": "VP9 / Opus WebM",
        "video-mpeg4-avi": "MPEG-4 / MP3 AVI",
        "audio-mp3": "音訊 MP3",
        "audio-flac": "音訊 FLAC",
        "audio-loudnorm-flac": "音量標準化／FLAC 品質優先",
        "audio-aac": "音訊 AAC（M4A）",
        "audio-opus": "音訊 Opus",
        "audio-loudnorm-opus": "音量標準化／Opus 容量優先",
        "audio-wav": "音訊 WAV（PCM）",
        "image-png": "影像 PNG",
        "image-jpeg": "影像 JPEG",
        "image-webp": "影像 WebP",
        "image-bmp": "影像 BMP",
        "image-tiff": "影像 TIFF",
        "subtitle-srt": "抽取 SRT 字幕",
        "ad-trim-h264": "本機廣告段落剪除（子 MOD）",
    }
    for preset_id in service.preset_ids():
        preset.addItem(labels.get(preset_id, preset_id), preset_id)

    start = QDoubleSpinBox()
    end = QDoubleSpinBox()
    for control in (start, end):
        control.setRange(0, 604_800)
        control.setDecimals(3)
        control.setSpecialValueText("未設定")
        control.setSuffix(" 秒")
    gpu = QCheckBox("H.264 使用 NVIDIA GPU（失敗回退 CPU）")
    gpu.setToolTip("必須先偵測到本機 FFmpeg 提供 h264_nvenc 才能啟用。")
    output_text = QLineEdit()
    output_text.setReadOnly(True)
    output_text.setPlaceholderText("尚未選擇輸出新檔")
    choose_output = QPushButton("選擇輸出")

    option_grid.addWidget(QLabel("格式"), 0, 0)
    option_grid.addWidget(preset, 0, 1, 1, 2)
    option_grid.addWidget(gpu, 0, 3, 1, 3)
    option_grid.addWidget(QLabel("開始"), 1, 0)
    option_grid.addWidget(start, 1, 1)
    option_grid.addWidget(QLabel("結束"), 1, 2)
    option_grid.addWidget(end, 1, 3)
    option_grid.addWidget(output_text, 1, 4)
    option_grid.addWidget(choose_output, 1, 5)
    form.addLayout(option_grid)

    watermark_row = QHBoxLayout()
    watermark_text = QLineEdit()
    watermark_text.setReadOnly(True)
    watermark_text.setPlaceholderText("尚未選擇 PNG／JPEG／WebP 等本機浮水印影像")
    watermark_text.setAccessibleName("浮水印影像")
    choose_watermark = QPushButton("選擇浮水印影像")
    watermark_label = QLabel("浮水印")
    watermark_row.addWidget(watermark_label)
    watermark_row.addWidget(watermark_text, 1)
    watermark_row.addWidget(choose_watermark)
    form.addLayout(watermark_row)

    target_card = QFrame()
    target_card.setObjectName("subtleCard")
    target_layout = QGridLayout(target_card)
    target_size_mib = QSpinBox()
    target_size_mib.setRange(8, 2_097_152)
    target_size_mib.setValue(100)
    target_size_mib.setSuffix(" MiB")
    target_size_mib.setAccessibleName("目標輸出容量")
    target_inspect_again = QPushButton("重新讀取時長")
    target_inspect_again.setObjectName("ghost")
    target_inspect_again.setEnabled(False)
    target_note = QLabel(
        "選擇單一來源後會在背景讀取時長，再計算兩階段平均位元率。"
    )
    target_note.setObjectName("muted")
    target_note.setWordWrap(True)
    target_layout.addWidget(QLabel("容量上限"), 0, 0)
    target_layout.addWidget(target_size_mib, 0, 1)
    target_layout.addWidget(target_inspect_again, 0, 2)
    target_layout.addWidget(target_note, 1, 0, 1, 3)
    form.addWidget(target_card)

    trim_card = QFrame()
    trim_card.setObjectName("subtleCard")
    trim_layout = QGridLayout(trim_card)
    ad_trim_enabled = QCheckBox("啟用 Local Ad Segment Trim 子 MOD")
    ad_ranges = QLineEdit()
    ad_ranges.setPlaceholderText("例：30-45; 01:30-01:45")
    preview_trim = QPushButton("預覽第一個切點 ±5 秒")
    trim_note = QLabel(
        "以分號分隔區間；可輸入秒數或 HH:MM:SS。只剪除指定區間並另存新檔。"
    )
    trim_note.setObjectName("muted")
    trim_note.setWordWrap(True)
    trim_layout.addWidget(ad_trim_enabled, 0, 0, 1, 2)
    trim_layout.addWidget(QLabel("剪除區間"), 1, 0)
    trim_layout.addWidget(ad_ranges, 1, 1)
    trim_layout.addWidget(preview_trim, 1, 2)
    trim_layout.addWidget(trim_note, 2, 0, 1, 3)
    form.addWidget(trim_card)

    submit_row = QHBoxLayout()
    estimate = QLabel("選擇來源、輸出與格式後會顯示估算。")
    estimate.setObjectName("muted")
    submit = QPushButton("加入轉換")
    submit.setObjectName("primary")
    submit_row.addWidget(estimate, 1)
    submit_row.addWidget(submit)
    form.addLayout(submit_row)

    auxiliary_row = QHBoxLayout()
    auxiliary_status = QLabel(
        "快速健康檢查只解碼檔案開頭；輸出試轉最多 20 秒，關閉預覽即清除。"
    )
    auxiliary_status.setObjectName("muted")
    auxiliary_status.setWordWrap(True)
    quick_health = QPushButton("快速健康檢查")
    output_sample = QPushButton("輸出試轉 20 秒")
    cancel_auxiliary = QPushButton("停止試轉／檢查")
    cancel_auxiliary.setEnabled(False)
    auxiliary_row.addWidget(auxiliary_status, 1)
    auxiliary_row.addWidget(quick_health)
    auxiliary_row.addWidget(output_sample)
    auxiliary_row.addWidget(cancel_auxiliary)
    form.addLayout(auxiliary_row)
    page.addWidget(card)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("狀態", "來源", "處理", "輸出", "訊息"))
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    page.addWidget(table, 1)
    cancel = QPushButton("取消選取工作")
    page.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def trim_enabled() -> bool:
        return builtin_mod_is_enabled(context, "media-ad-trim")

    def selected_track() -> MediaStreamInfo | None:
        inspection = panel.inspection
        stream_index = track_select.currentData()
        if not isinstance(inspection, MediaInspection) or not isinstance(
            stream_index, int
        ):
            return None
        return next(
            (
                stream
                for stream in inspection.streams
                if stream.index == stream_index
            ),
            None,
        )

    def show_stream_inspection(
        generation: int,
        result: object,
        error: str,
    ) -> None:
        if panel.closing or generation != panel.inspection_generation:
            return
        inspect_again.setEnabled(len(panel.sources) == 1)
        target_inspect_again.setEnabled(len(panel.sources) == 1)
        with QSignalBlocker(track_select):
            track_select.clear()
            track_select.setEnabled(False)
            if error:
                panel.inspection = None
                track_status.setText(f"軌道檢查失敗：{error}")
                target_note.setText(f"來源時長檢查失敗：{error}")
            elif not isinstance(result, MediaInspection):
                panel.inspection = None
                track_status.setText("軌道檢查失敗：回傳資料無效")
                target_note.setText("來源時長檢查失敗：回傳資料無效")
            else:
                panel.inspection = result
                tracks = tuple(
                    stream
                    for stream in result.streams
                    if stream.codec_type in {"audio", "subtitle"}
                )
                type_labels = {"audio": "音訊", "subtitle": "字幕"}
                for stream in tracks:
                    details = [
                        f"#{stream.index}",
                        type_labels[stream.codec_type],
                        stream.codec_name or "未知 codec",
                    ]
                    if stream.language:
                        details.append(stream.language)
                    if stream.title:
                        details.append(stream.title)
                    if stream.channels:
                        details.append(f"{stream.channels} 聲道")
                    if stream.default:
                        details.append("預設")
                    if stream.forced:
                        details.append("強制")
                    track_select.addItem(" · ".join(details), stream.index)
                track_select.setEnabled(bool(tracks))
                if tracks:
                    duration = (
                        f"，{result.duration_seconds:.1f} 秒"
                        if result.duration_seconds is not None
                        else ""
                    )
                    track_status.setText(
                        f"找到 {len(tracks)} 條可無損輸出的軌道{duration}；"
                        "音訊輸出 .mka，字幕輸出 .mks。"
                    )
                else:
                    track_status.setText("來源沒有可選取的音訊或字幕軌道。")
                if result.duration_seconds is None:
                    target_note.setText(
                        "來源沒有可用時長，不能使用目標容量轉檔。"
                    )
                else:
                    target_note.setText(
                        f"來源時長 {result.duration_seconds:.3f} 秒；"
                        "使用 3% 容器餘裕，輸出不會超過設定容量。"
                    )
        update_preview()

    def begin_stream_inspection(*, force: bool = False) -> None:
        selected_preset = str(preset.currentData())
        if selected_preset not in {
            "stream-copy-matroska",
            "video-h264-target-size",
        }:
            return
        if len(panel.sources) != 1:
            panel.inspection = None
            panel.inspection_requested_source = None
            with QSignalBlocker(track_select):
                track_select.clear()
                track_select.setEnabled(False)
            inspect_again.setEnabled(False)
            target_inspect_again.setEnabled(False)
            track_status.setText("請只選擇一個來源，才能檢查音訊與字幕軌道。")
            target_note.setText("請只選擇一個來源，才能計算目標容量。")
            return
        source = panel.sources[0].resolve()
        if not force and panel.inspection_requested_source == source:
            return
        panel.inspection_generation += 1
        generation = panel.inspection_generation
        panel.inspection_requested_source = source
        panel.inspection = None
        with QSignalBlocker(track_select):
            track_select.clear()
            track_select.setEnabled(False)
        inspect_again.setEnabled(False)
        target_inspect_again.setEnabled(False)
        track_status.setText("正在背景檢查音訊與字幕軌道…")
        target_note.setText("正在背景讀取來源時長…")

        def worker() -> None:
            try:
                result = service.inspect_source(source)
            except (OSError, RuntimeError, TypeError, ValueError) as caught:
                inspection_bridge.finished.emit(generation, None, str(caught))
            else:
                inspection_bridge.finished.emit(generation, result, "")

        threading.Thread(
            target=worker,
            name="media-track-inspection",
            daemon=True,
        ).start()

    def current_request() -> ConversionRequest:
        if not panel.sources or not output_text.text():
            raise ValueError("請先選擇來源與輸出新檔")
        selected_preset = str(preset.currentData())
        target_selected = selected_preset == "video-h264-target-size"
        stream_index = None
        if selected_preset == "stream-copy-matroska":
            track = selected_track()
            if track is None:
                raise ValueError("請先選擇已完成檢查的音訊或字幕軌道")
            stream_index = track.index
        ranges = ()
        if selected_preset == "ad-trim-h264":
            if not trim_enabled():
                raise ValueError("請先啟用 Local Ad Segment Trim 子 MOD")
            ranges = parse_removal_ranges(ad_ranges.text())
        source_duration = None
        target_size_bytes = None
        if target_selected:
            inspection = panel.inspection
            if (
                not isinstance(inspection, MediaInspection)
                or len(panel.sources) != 1
                or inspection.source != panel.sources[0].resolve()
                or inspection.duration_seconds is None
            ):
                raise ValueError("請等待來源時長檢查完成")
            source_duration = inspection.duration_seconds
            target_size_bytes = target_size_mib.value() * 1024 * 1024
        return ConversionRequest(
            tuple(panel.sources),
            Path(output_text.text()),
            selected_preset,
            None
            if selected_preset in {"ad-trim-h264", "stream-copy-matroska"}
            or start.value() == 0
            else float(start.value()),
            None
            if selected_preset in {"ad-trim-h264", "stream-copy-matroska"}
            or end.value() == 0
            else float(end.value()),
            hardware_acceleration=gpu.isChecked() and selected_preset == "video-h264",
            remove_ranges=ranges,
            watermark=(
                panel.watermark
                if selected_preset == "watermark-h264"
                else None
            ),
            stream_index=stream_index,
            target_size_bytes=target_size_bytes,
            source_duration_seconds=source_duration,
        )

    def size_text(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if number < 1024 or unit == "TB":
                return f"{number:.1f} {unit}"
            number /= 1024
        return str(value)

    def update_mode() -> None:
        selected_preset = str(preset.currentData())
        selected = selected_preset == "ad-trim-h264"
        watermark_selected = selected_preset == "watermark-h264"
        hevc10_selected = selected_preset == "hevc10-nvenc-opus-copy"
        target_selected = selected_preset == "video-h264-target-size"
        required_encoder = service.preset_required_encoder(selected_preset)
        required_filter = service.preset_required_filter(selected_preset)
        encoder_ready = (
            not required_encoder
            or required_encoder in panel.detected_encoders
        )
        filter_ready = (
            not required_filter
            or required_filter in panel.detected_filters
        )
        track_selected = selected_preset == "stream-copy-matroska"
        child_enabled = trim_enabled()
        trim_card.setVisible(selected)
        track_card.setVisible(track_selected)
        watermark_label.setVisible(watermark_selected)
        watermark_text.setVisible(watermark_selected)
        choose_watermark.setVisible(watermark_selected)
        target_card.setVisible(target_selected)
        start.setEnabled(not selected and not track_selected)
        end.setEnabled(not selected and not track_selected)
        gpu_enabled = (
            selected_preset == "video-h264"
            and panel.gpu_available
        )
        gpu.setEnabled(gpu_enabled)
        if not gpu_enabled:
            gpu.setChecked(False)
        ad_ranges.setEnabled(selected and child_enabled)
        preview_trim.setEnabled(
            selected and child_enabled and len(panel.sources) == 1
        )
        submit.setEnabled(
            (not selected or child_enabled)
            and encoder_ready
            and filter_ready
            and (not track_selected or selected_track() is not None)
            and (
                not target_selected
                or (
                    isinstance(panel.inspection, MediaInspection)
                    and panel.inspection.duration_seconds is not None
                )
            )
        )
        one_source = len(panel.sources) == 1
        auxiliary_ready = (
            one_source and service.is_enabled and not panel.auxiliary_busy
        )
        choose_sources.setEnabled(not panel.auxiliary_busy)
        quick_health.setEnabled(auxiliary_ready)
        output_sample.setEnabled(
            auxiliary_ready
            and bool(output_text.text())
            and service.supports_output_sample(selected_preset)
        )
        cancel_auxiliary.setEnabled(panel.auxiliary_busy)
        output_sample.setToolTip(
            "使用目前轉檔設定產生最多 20 秒暫存新檔；不加入正式佇列。"
            if service.supports_output_sample(selected_preset)
            else "串流複製、軌道抽取、影像與剪除格式不提供輸出試轉。"
        )
        requirements = tuple(
            value
            for value in (required_encoder, required_filter)
            if value
        )
        tooltip = (
            "需要本機 hevc_nvenc；來源第一條音訊必須是 Opus，才會直接複製。"
            if hevc10_selected
            else (
                "需要 FFmpeg build 提供 "
                + "、".join(requirements)
                + "；實際工作仍會驗證本機能力。"
                if requirements
                else ""
            )
        )
        if selected_preset.startswith("audio-loudnorm-"):
            tooltip += " 音量標準化會處理音訊樣本，不是 Passthru。"
        preset.setToolTip(tooltip)
        if track_selected or target_selected:
            begin_stream_inspection()

    def update_preview() -> None:
        update_mode()
        selected_preset = str(preset.currentData())
        required_encoder = service.preset_required_encoder(selected_preset)
        required_filter = service.preset_required_filter(selected_preset)
        if required_encoder and required_encoder not in panel.detected_encoders:
            suffix = (
                "；實際加入時也會驗證來源音訊為 Opus"
                if selected_preset == "hevc10-nvenc-opus-copy"
                else ""
            )
            estimate.setText(
                f"請先偵測 FFmpeg 是否提供 {required_encoder}{suffix}。"
            )
            return
        if required_filter and required_filter not in panel.detected_filters:
            estimate.setText(
                f"請先偵測 FFmpeg 是否提供 {required_filter} filter。"
            )
            return
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError):
            output_sample.setEnabled(False)
            estimate.setText("選擇來源、輸出與有效設定後會顯示估算。")
        else:
            output_sample.setEnabled(
                len(panel.sources) == 1
                and service.is_enabled
                and not panel.auxiliary_busy
                and service.supports_output_sample(plan.request.preset)
            )
            estimate.setText(
                f"{plan.strategy}；預估輸出 {size_text(plan.estimated_bytes)}"
            )

    def sync_trim_state() -> None:
        with QSignalBlocker(ad_trim_enabled):
            ad_trim_enabled.setChecked(trim_enabled())
        available = any(
            status.provider_id == "media-ad-trim"
            and bool(getattr(status, "available", True))
            for status in context.features.statuses()
        )
        ad_trim_enabled.setEnabled(available)
        ad_trim_enabled.setToolTip(
            "僅處理本機檔案；不會略過或移除網站廣告。"
            if available
            else "此子 MOD 未載入，或尚未偵測到 FFmpeg。"
        )
        update_preview()

    def show_local_capabilities(
        generation: int,
        result: object,
        error: str,
    ) -> None:
        if panel.closing or generation != panel.capability_generation:
            return
        panel.capability_busy = False
        panel.capability_cancel_event = None
        refresh_capabilities.setEnabled(True)
        if error or not isinstance(result, ConversionCapabilities):
            panel.detected_encoders = frozenset()
            panel.detected_filters = frozenset()
            panel.gpu_available = False
            panel.hevc_nvenc_available = False
            capability_note.setText(
                "本機能力偵測失敗；硬體格式維持停用："
                + (error or "回傳資料無效")
            )
            update_preview()
            return
        panel.detected_encoders = result.encoders
        panel.detected_filters = result.filters
        panel.gpu_available = result.supports_h264_nvenc
        panel.hevc_nvenc_available = result.supports_hevc_nvenc
        version = result.ffmpeg_version or "FFmpeg 版本未知"
        hardware_encoders = tuple(
            encoder
            for encoder in (
                "h264_nvenc",
                "hevc_nvenc",
                "av1_nvenc",
                "h264_qsv",
                "hevc_qsv",
                "av1_qsv",
                "h264_amf",
                "hevc_amf",
                "av1_amf",
            )
            if encoder in result.encoders
        )
        detected = ", ".join(hardware_encoders) or "沒有可用硬體 encoder"
        warning = (
            f"；{len(result.errors)} 項探測失敗"
            if result.errors
            else ""
        )
        filter_detail = (
            "；loudnorm filter 可用"
            if "loudnorm" in result.filters
            else "；loudnorm filter 不可用"
        )
        capability_note.setText(
            f"{version}；FFmpeg build 包含：{detected}{filter_detail}{warning}。"
            "實際顯示卡與驅動會在工作執行時再次驗證。"
        )
        update_preview()

    def refresh_local_capabilities() -> None:
        if panel.capability_busy:
            return
        panel.capability_generation += 1
        generation = panel.capability_generation
        panel.capability_busy = True
        cancel_event = threading.Event()
        panel.capability_cancel_event = cancel_event
        refresh_capabilities.setEnabled(False)
        capability_note.setText("正在背景偵測本機 FFmpeg encoder…")

        def worker() -> None:
            try:
                capabilities = service.capabilities(
                    refresh=True,
                    cancel_event=cancel_event,
                )
            except (OSError, RuntimeError, ValueError) as caught:
                capability_bridge.finished.emit(generation, None, str(caught))
            else:
                capability_bridge.finished.emit(
                    generation, capabilities, ""
                )

        threading.Thread(
            target=worker,
            name="media-capability-probe",
            daemon=True,
        ).start()

    def toggle_trim(checked: bool) -> None:
        try:
            set_builtin_mod_enabled(context, "media-ad-trim", checked)
        except (KeyError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Local Ad Segment Trim", str(error))
        sync_trim_state()

    def select_sources() -> None:
        values, _ = QFileDialog.getOpenFileNames(
            panel, "選擇本機媒體", str(Path.home()), "所有媒體 (*)"
        )
        if values:
            set_sources(tuple(Path(value) for value in values))

    def set_sources(values: tuple[Path, ...]) -> None:
        panel.sources = list(values)
        panel.inspection_generation += 1
        panel.inspection_requested_source = None
        panel.inspection = None
        first = str(values[0])
        source_text.setText(
            first if len(values) == 1 else f"{first} 等 {len(values)} 個檔案"
        )
        update_preview()

    def apply_source_drop(intake: DropIntake) -> None:
        if panel.auxiliary_busy:
            estimate.setText("請先停止目前的試轉或健康檢查，再更換來源。")
            return
        try:
            sources = accepted_conversion_drop_sources(intake)
        except ValueError as error:
            estimate.setText(str(error))
            return
        set_sources(sources)
        rejected = issue_summary(intake)
        if rejected:
            estimate.setText(
                f"已拖入 {len(sources)} 個來源；未採用：{rejected}"
            )

    def select_output() -> None:
        track = selected_track()
        if str(preset.currentData()) == "stream-copy-matroska" and track is not None:
            suffix = ".mka" if track.codec_type == "audio" else ".mks"
            suggested = Path.home() / f"{panel.sources[0].stem}-track{suffix}"
            file_filter = (
                "Matroska 音訊 (*.mka)"
                if suffix == ".mka"
                else "Matroska 字幕 (*.mks)"
            )
        else:
            suggested = Path.home()
            file_filter = "媒體檔案 (*)"
        value, _ = QFileDialog.getSaveFileName(
            panel,
            "選擇輸出新檔（不覆寫原檔）",
            str(suggested),
            file_filter,
        )
        if value:
            output_text.setText(value)
            update_preview()

    def select_watermark() -> None:
        value, _ = QFileDialog.getOpenFileName(
            panel,
            "選擇本機浮水印影像",
            str(Path.home()),
            "影像 (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        )
        if value:
            panel.watermark = Path(value)
            watermark_text.setText(value)
            update_preview()

    def preview_first_cut() -> None:
        try:
            ranges = parse_removal_ranges(ad_ranges.text())
        except ValueError as error:
            QMessageBox.warning(panel, "切點預覽", str(error))
            return
        if len(panel.sources) != 1 or not ranges:
            QMessageBox.warning(panel, "切點預覽", "請選擇一個來源並輸入剪除區間")
            return
        if panel.preview_dialog is not None:
            panel.preview_dialog.close()
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget

        dialog = QDialog(panel)
        dialog.setWindowTitle("本機切點預覽")
        dialog.resize(720, 460)
        layout = QVBoxLayout(dialog)
        video = QVideoWidget(dialog)
        layout.addWidget(video, 1)
        note = QLabel(
            f"預覽第一個切點：{ranges[0][0]:.3f} 秒附近；10 秒後自動暫停。"
        )
        layout.addWidget(note)
        controls = QHBoxLayout()
        replay = QPushButton("重新播放")
        stop = QPushButton("停止")
        close = QPushButton("關閉")
        controls.addWidget(replay)
        controls.addStretch(1)
        controls.addWidget(stop)
        controls.addWidget(close)
        layout.addLayout(controls)
        player = QMediaPlayer(dialog)
        audio = QAudioOutput(dialog)
        player.setAudioOutput(audio)
        player.setVideoOutput(video)
        player.setSource(QUrl.fromLocalFile(str(panel.sources[0].resolve())))
        preview_start = max(0, int((ranges[0][0] - 5.0) * 1000))
        pause_timer = QTimer(dialog)
        pause_timer.setSingleShot(True)
        pause_timer.setProperty(PAUSE_IN_BACKGROUND_PROPERTY, True)

        def play() -> None:
            if is_background_idle(dialog):
                note.setText("背景待機中；還原視窗後可按「重新播放」。")
                return
            player.setPosition(preview_start)
            player.play()
            pause_timer.start(10_000)

        released = [False]

        def release_preview() -> None:
            if released[0]:
                return
            released[0] = True
            pause_timer.stop()
            player.stop()
            player.setSource(QUrl())
            player.setAudioOutput(None)
            player.setVideoOutput(None)
            player.deleteLater()
            audio.deleteLater()
            if panel.preview_dialog is dialog:
                panel.preview_dialog = None

        pause_timer.timeout.connect(player.pause)
        replay.clicked.connect(play)
        stop.clicked.connect(player.stop)
        close.clicked.connect(dialog.close)
        dialog.finished.connect(lambda _result: release_preview())
        dialog.show()
        panel.preview_dialog = dialog
        QTimer.singleShot(0, play)

    def discard_sample(path: Path | None) -> None:
        if path is None:
            return
        try:
            service.discard_output_sample(path)
        except (OSError, RuntimeError, TypeError, ValueError):
            pass

    def show_output_sample(path: Path) -> None:
        if panel.output_sample_dialog is not None:
            panel.output_sample_dialog.close()
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget

        dialog = QDialog(panel)
        dialog.setWindowTitle("格式工廠輸出試轉")
        dialog.resize(720, 460)
        layout = QVBoxLayout(dialog)
        video = QVideoWidget(dialog)
        layout.addWidget(video, 1)
        note = QLabel("正在載入試轉輸出；關閉此視窗後會清除暫存檔。")
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        replay = QPushButton("重新播放")
        stop = QPushButton("停止")
        close = QPushButton("關閉")
        controls.addWidget(replay)
        controls.addStretch(1)
        controls.addWidget(stop)
        controls.addWidget(close)
        layout.addLayout(controls)
        player = QMediaPlayer(dialog)
        audio = QAudioOutput(dialog)
        player.setAudioOutput(audio)
        player.setVideoOutput(video)
        player.setSource(QUrl.fromLocalFile(str(path)))

        def play() -> None:
            if is_background_idle(dialog):
                note.setText("背景待機中；還原視窗後可按「重新播放」。")
                return
            note.setText("播放實際試轉輸出；此檔案不會加入正式轉換紀錄。")
            player.setPosition(0)
            player.play()

        released = [False]

        def release_sample() -> None:
            if released[0]:
                return
            released[0] = True
            player.stop()
            player.setSource(QUrl())
            player.setAudioOutput(None)
            player.setVideoOutput(None)
            player.deleteLater()
            audio.deleteLater()
            discard_sample(path)
            if panel.output_sample_path == path:
                panel.output_sample_path = None
            if panel.output_sample_dialog is dialog:
                panel.output_sample_dialog = None

        player.errorOccurred.connect(
            lambda _error, message: note.setText(
                f"內建播放器無法播放此試轉檔：{message or '格式不受支援'}"
            )
        )
        replay.clicked.connect(play)
        stop.clicked.connect(player.stop)
        close.clicked.connect(dialog.close)
        dialog.finished.connect(lambda _result: release_sample())
        panel.output_sample_path = path
        panel.output_sample_dialog = dialog
        dialog.show()
        QTimer.singleShot(0, play)

    def finish_auxiliary(
        generation: int,
        operation: str,
        result: object,
        error: str,
    ) -> None:
        if panel.closing or generation != panel.auxiliary_generation:
            if isinstance(result, Path):
                discard_sample(result)
            return
        cancelled = bool(
            panel.auxiliary_cancel_event
            and panel.auxiliary_cancel_event.is_set()
        )
        panel.auxiliary_busy = False
        panel.auxiliary_cancel_event = None
        update_mode()
        if error:
            auxiliary_status.setText(
                "已停止試轉／檢查。"
                if cancelled
                else f"試轉／檢查失敗：{error}"
            )
            return
        if operation == "health" and isinstance(result, MediaHealthReport):
            stream_count = len(result.inspection.streams)
            if result.healthy:
                auxiliary_status.setText(
                    f"快速健康檢查通過：可讀取 {stream_count} 條媒體軌，"
                    f"已解碼開頭 {result.checked_seconds:.1f} 秒。"
                    "此結果不代表已掃描完整檔案。"
                )
            else:
                detail = (
                    result.diagnostic or "FFmpeg 回報解碼錯誤"
                ).replace("\r", " ").replace("\n", " ")[:300]
                auxiliary_status.setText(
                    f"快速健康檢查未通過：{detail}"
                )
            return
        if operation == "sample" and isinstance(result, Path):
            if is_background_idle(panel):
                discard_sample(result)
                auxiliary_status.setText(
                    "試轉已完成，但目前為背景待機；暫存檔已清除。"
                )
                return
            auxiliary_status.setText("輸出試轉完成，正在開啟本機預覽。")
            show_output_sample(result)
            return
        auxiliary_status.setText("試轉／檢查回傳資料無效。")

    def start_auxiliary(operation: str) -> None:
        if panel.auxiliary_busy:
            return
        if is_background_idle(panel):
            auxiliary_status.setText("背景待機中；還原視窗後再開始試轉或檢查。")
            return
        if len(panel.sources) != 1:
            auxiliary_status.setText("請先選擇一個本機媒體來源。")
            return
        try:
            request = current_request() if operation == "sample" else None
        except (OSError, TypeError, ValueError) as error:
            auxiliary_status.setText(str(error))
            return
        panel.auxiliary_generation += 1
        generation = panel.auxiliary_generation
        source = panel.sources[0]
        cancel_event = threading.Event()
        panel.auxiliary_cancel_event = cancel_event
        panel.auxiliary_busy = True
        auxiliary_status.setText(
            "正在產生 20 秒輸出試轉…"
            if operation == "sample"
            else "正在檢查媒體結構並解碼開頭 15 秒…"
        )
        update_mode()

        def worker() -> None:
            try:
                if operation == "sample":
                    assert request is not None
                    result = service.create_output_sample(
                        request,
                        duration_seconds=20.0,
                        cancel_event=cancel_event,
                    )
                else:
                    result = service.check_source_health(
                        source,
                        duration_seconds=15.0,
                        cancel_event=cancel_event,
                    )
            except (OSError, RuntimeError, TypeError, ValueError) as caught:
                auxiliary_bridge.finished.emit(
                    generation, operation, None, str(caught)
                )
            else:
                auxiliary_bridge.finished.emit(
                    generation, operation, result, ""
                )

        threading.Thread(
            target=worker,
            name=f"media-{operation}",
            daemon=True,
        ).start()

    def stop_auxiliary() -> None:
        cancel_event = panel.auxiliary_cancel_event
        if cancel_event is not None:
            cancel_event.set()
            auxiliary_status.setText("正在停止試轉／檢查…")

    def enqueue() -> None:
        try:
            plan = service.preview(current_request())
        except (OSError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
            return
        ranges = ""
        if plan.request.remove_ranges:
            ranges = "\n剪除：" + "; ".join(
                f"{start_value:.3f}-{end_value:.3f} 秒"
                for start_value, end_value in plan.request.remove_ranges
            )
        answer = QMessageBox.question(
            panel,
            "確認加入",
            f"{plan.strategy}\n預估：{size_text(plan.estimated_bytes)}"
            f"\n輸出：{plan.request.output}{ranges}\n\n原檔不會被覆寫，是否加入？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            service.submit(plan.request)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.warning(panel, "Media Convert", str(error))
        refresh()

    labels_by_state = {
        ConversionState.QUEUED: "排隊中",
        ConversionState.RUNNING: "處理中",
        ConversionState.COMPLETED: "完成",
        ConversionState.FAILED: "失敗",
        ConversionState.CANCELLED: "已取消",
    }

    def refresh() -> None:
        tasks = service.snapshots()
        rows = tuple(
            (
                task.task_id,
                task.state,
                task.request.sources,
                task.request.preset,
                task.output_path,
                task.request.output,
                task.error,
            )
            for task in tasks
        )
        interval = task_table_interval(
            active=any(
                task.state in {ConversionState.QUEUED, ConversionState.RUNNING}
                for task in tasks
            ),
            visible=panel.isVisible(),
        )
        if timer.interval() != interval:
            timer.setInterval(interval)
        signature = visible_rows_signature(rows)
        if signature == panel.render_signature:
            return
        panel.render_signature = signature
        table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            source = task.request.sources[0].name
            if len(task.request.sources) > 1:
                source += f" 等 {len(task.request.sources)} 個檔案"
            values = (
                labels_by_state[task.state],
                source,
                task.request.preset,
                task.output_path or str(task.request.output),
                task.error or "—",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, task.task_id)
                table.setItem(row, column, cell)

    def cancel_selected() -> None:
        cell = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
        if cell is not None:
            service.cancel(str(cell.data(Qt.ItemDataRole.UserRole)))
            refresh()

    def shutdown() -> None:
        timer.stop()
        panel.closing = True
        panel.capability_generation += 1
        if panel.capability_cancel_event is not None:
            panel.capability_cancel_event.set()
        panel.auxiliary_generation += 1
        if panel.auxiliary_cancel_event is not None:
            panel.auxiliary_cancel_event.set()
        panel.inspection_generation += 1
        if panel.preview_dialog is not None:
            panel.preview_dialog.close()
            panel.preview_dialog = None
        if panel.output_sample_dialog is not None:
            panel.output_sample_dialog.close()
            panel.output_sample_dialog = None
        elif panel.output_sample_path is not None:
            discard_sample(panel.output_sample_path)
            panel.output_sample_path = None

    choose_sources.clicked.connect(select_sources)
    choose_output.clicked.connect(select_output)
    choose_watermark.clicked.connect(select_watermark)
    preset.currentIndexChanged.connect(update_preview)
    track_select.currentIndexChanged.connect(update_preview)
    inspect_again.clicked.connect(
        lambda: begin_stream_inspection(force=True)
    )
    target_inspect_again.clicked.connect(
        lambda: begin_stream_inspection(force=True)
    )
    inspection_bridge.finished.connect(show_stream_inspection)
    auxiliary_bridge.finished.connect(finish_auxiliary)
    capability_bridge.finished.connect(show_local_capabilities)
    start.valueChanged.connect(update_preview)
    end.valueChanged.connect(update_preview)
    gpu.toggled.connect(update_preview)
    output_text.textChanged.connect(update_preview)
    target_size_mib.valueChanged.connect(update_preview)
    ad_ranges.textChanged.connect(update_preview)
    ad_trim_enabled.toggled.connect(toggle_trim)
    refresh_capabilities.clicked.connect(refresh_local_capabilities)
    preview_trim.clicked.connect(preview_first_cut)
    quick_health.clicked.connect(lambda: start_auxiliary("health"))
    output_sample.clicked.connect(lambda: start_auxiliary("sample"))
    cancel_auxiliary.clicked.connect(stop_auxiliary)
    submit.clicked.connect(enqueue)
    cancel.clicked.connect(cancel_selected)
    timer = QTimer(panel)
    timer.setInterval(1500)
    timer.timeout.connect(refresh)
    timer.start()
    panel.timer = timer
    panel.shutdown = shutdown
    panel.preset = preset
    panel.watermark = None
    panel.watermark_text = watermark_text
    panel.choose_watermark = choose_watermark
    panel.target_card = target_card
    panel.target_size_mib = target_size_mib
    panel.target_note = target_note
    panel.target_inspect_again = target_inspect_again
    panel.track_card = track_card
    panel.track_select = track_select
    panel.track_status = track_status
    panel.inspect_again = inspect_again
    panel.inspection_bridge = inspection_bridge
    panel.auxiliary_bridge = auxiliary_bridge
    panel.capability_bridge = capability_bridge
    panel.capability_note = capability_note
    panel.refresh_capabilities = refresh_capabilities
    panel.ad_trim_enabled = ad_trim_enabled
    panel.ad_ranges = ad_ranges
    panel.trim_card = trim_card
    panel.preview_trim = preview_trim
    panel.quick_health = quick_health
    panel.output_sample = output_sample
    panel.cancel_auxiliary = cancel_auxiliary
    panel.auxiliary_status = auxiliary_status
    panel.submit = submit
    panel.source_text = source_text
    panel.output_text = output_text
    panel.apply_drop_intake = apply_source_drop
    panel.drop_intake_filter = install_drop_intake(
        source_text,
        apply_source_drop,
        on_error=lambda message: estimate.setText(
            f"拖放內容無法使用：{message}"
        ),
    )
    sync_trim_state()
    refresh()
    return panel
