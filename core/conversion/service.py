"""Disabled-by-default FFmpeg conversion queue with atomic output handling."""

from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
from threading import Event, RLock, Thread
import time
import uuid

from core.conversion.models import (
    ConversionPlan,
    ConversionRequest,
    ConversionState,
    ConversionTask,
)
from core.storage.atomic import commit_file_without_overwrite

MAX_SOURCES = 100
MAX_SOURCE_BYTES = 4 * 1024**4
MAX_REMOVAL_RANGES = 50
MAX_MEDIA_SECONDS = 604_800.0


class ConversionService:
    provider_id = "media-convert"
    display_name = "Media Convert"

    def __init__(self, ffmpeg: Path | None, preset_path: Path, temp_root: Path) -> None:
        self.ffmpeg = Path(ffmpeg).resolve() if ffmpeg is not None else None
        self.preset_path = preset_path.resolve()
        self.temp_root = temp_root.resolve()
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self._presets = self._load_presets()
        self._enabled = False
        self._closed = False
        self._lock = RLock()
        self._tasks: dict[str, ConversionTask] = {}
        self._queue: list[str] = []
        self._worker: Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def available(self) -> bool:
        return self.ffmpeg is not None and self.ffmpeg.is_file()

    def set_enabled(self, enabled: bool) -> int:
        if enabled and not self.available:
            raise RuntimeError("FFmpeg is required before Media Convert can be enabled")
        with self._lock:
            self._enabled = enabled
        return 0 if enabled else self.cancel_all()

    def preset_ids(self) -> tuple[str, ...]:
        return tuple(self._presets)

    def preview(self, request: ConversionRequest) -> ConversionPlan:
        sources, output, preset, remove_ranges = self._validate(request)
        definition = self._presets[preset]
        ratio = float(definition["estimate_ratio"])
        estimated = max(1, int(sum(path.stat().st_size for path in sources) * ratio))
        ffmpeg = str(self.ffmpeg) if self.ffmpeg is not None else "ffmpeg"
        command = [ffmpeg, "-nostdin", "-hide_banner", "-n"]
        if preset == "join-copy":
            command.extend(("-f", "concat", "-safe", "1", "-i", "@CONCAT_LIST@"))
        else:
            if request.start_time is not None:
                command.extend(("-ss", self._time_value(request.start_time)))
            command.extend(("-i", str(sources[0])))
            if request.end_time is not None:
                command.extend(("-to", self._time_value(request.end_time)))
        replacements: dict[str, str] = {}
        if preset == "ad-trim-h264":
            selector = self._removal_selector(remove_ranges)
            replacements = {
                "@REMOVE_VIDEO_FILTER@": (
                    f"select={selector},setpts=N/FRAME_RATE/TB"
                ),
                "@REMOVE_AUDIO_FILTER@": (
                    f"aselect={selector},asetpts=N/SR/TB"
                ),
            }
        args = tuple(
            replacements.get(str(value), str(value))
            for value in definition["args"]
        )
        fallback = None
        if request.hardware_acceleration and definition.get("gpu_args"):
            gpu_command = tuple(command + [str(value) for value in definition["gpu_args"]] + ["@OUTPUT@"])
            fallback = tuple(command + list(args) + ["@OUTPUT@"])
            final_command = gpu_command
            strategy = f"{definition['strategy']}（GPU，失敗時回退 CPU）"
        else:
            final_command = tuple(command + list(args) + ["@OUTPUT@"])
            strategy = str(definition["strategy"])
        return ConversionPlan(
            replace(
                request,
                sources=sources,
                output=output,
                preset=preset,
                remove_ranges=remove_ranges,
            ),
            strategy,
            estimated,
            final_command,
            fallback,
        )

    def submit(self, request: ConversionRequest) -> str:
        if not self.is_enabled:
            raise RuntimeError("Media Convert MOD is disabled")
        plan = self.preview(request)
        task_id = uuid.uuid4().hex
        task = ConversionTask(task_id, plan.request)
        with self._lock:
            if self._closed:
                raise RuntimeError("conversion service is closed")
            self._tasks[task_id] = task
            self._queue.append(task_id)
            if self._worker is None or not self._worker.is_alive():
                self._worker = Thread(target=self._work, name="media-convert", daemon=True)
                self._worker.start()
        return task_id

    def snapshots(self) -> tuple[ConversionTask, ...]:
        with self._lock:
            return tuple(
                replace(task, cancel_event=Event()) for task in self._tasks.values()
            )

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.state in {
                ConversionState.COMPLETED,
                ConversionState.FAILED,
                ConversionState.CANCELLED,
            }:
                return False
            task.cancel_event.set()
            if task.state == ConversionState.QUEUED:
                task.state = ConversionState.CANCELLED
                if task_id in self._queue:
                    self._queue.remove(task_id)
            process = self._process if task.state == ConversionState.RUNNING else None
        if process is not None:
            process.terminate()
        return True

    def cancel_all(self) -> int:
        return sum(self.cancel(task.task_id) for task in self.snapshots())

    def cancel_preset(self, preset_id: str) -> int:
        """Cancel only work owned by one optional conversion capability."""

        selected = preset_id.strip().casefold()
        return sum(
            self.cancel(task.task_id)
            for task in self.snapshots()
            if task.request.preset == selected
        )

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.cancel_all()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=3)

    def _work(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    return
                task_id = self._queue.pop(0)
                task = self._tasks[task_id]
                if task.cancel_event.is_set():
                    task.state = ConversionState.CANCELLED
                    continue
                task.state = ConversionState.RUNNING
            try:
                output = self._execute(task, self.preview(task.request))
            except Exception as error:
                with self._lock:
                    task.state = (
                        ConversionState.CANCELLED
                        if task.cancel_event.is_set()
                        else ConversionState.FAILED
                    )
                    task.error = "" if task.cancel_event.is_set() else str(error)
            else:
                with self._lock:
                    task.state = ConversionState.COMPLETED
                    task.output_path = str(output)

    def _execute(self, task: ConversionTask, plan: ConversionPlan) -> Path:
        output = plan.request.output
        part = output.with_name(f".{output.stem}.{task.task_id}.part{output.suffix}")
        concat = self.temp_root / f"{task.task_id}.ffconcat"
        part.unlink(missing_ok=True)
        concat.unlink(missing_ok=True)
        try:
            command = self._materialize(plan.command, plan, part, concat)
            return_code = self._run(command, task.cancel_event)
            if (
                return_code != 0
                and not task.cancel_event.is_set()
                and plan.fallback_command is not None
            ):
                part.unlink(missing_ok=True)
                command = self._materialize(plan.fallback_command, plan, part, concat)
                return_code = self._run(command, task.cancel_event)
            if task.cancel_event.is_set():
                raise RuntimeError("conversion cancelled")
            if return_code != 0 or not part.is_file():
                raise RuntimeError(f"FFmpeg exited with code {return_code}")
            if output.exists():
                raise FileExistsError(output)
            commit_file_without_overwrite(part, output)
            return output
        finally:
            part.unlink(missing_ok=True)
            concat.unlink(missing_ok=True)

    def _run(self, command: tuple[str, ...], cancel_event: object) -> int:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._process = process
        try:
            while process.poll() is None:
                if cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                time.sleep(0.05)
            return int(process.returncode or 0)
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def _materialize(
        self,
        command: tuple[str, ...],
        plan: ConversionPlan,
        part: Path,
        concat: Path,
    ) -> tuple[str, ...]:
        if "@CONCAT_LIST@" in command:
            lines = ["ffconcat version 1.0"]
            for source in plan.request.sources:
                escaped = str(source).replace("'", "'\\''")
                lines.append(f"file '{escaped}'")
            concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return tuple(
            str(part) if value == "@OUTPUT@" else str(concat) if value == "@CONCAT_LIST@" else value
            for value in command
        )

    def _validate(
        self, request: ConversionRequest
    ) -> tuple[
        tuple[Path, ...],
        Path,
        str,
        tuple[tuple[float, float], ...],
    ]:
        if not isinstance(request, ConversionRequest):
            raise TypeError("invalid conversion request")
        preset = request.preset.strip().casefold()
        if preset not in self._presets:
            raise ValueError("unsupported conversion preset")
        if not 1 <= len(request.sources) <= MAX_SOURCES:
            raise ValueError("conversion needs 1 to 100 sources")
        sources = tuple(path.expanduser().resolve() for path in request.sources)
        total = 0
        for source in sources:
            if source.is_symlink() or not source.is_file():
                raise ValueError("conversion source must be a regular file")
            total += source.stat().st_size
        if total > MAX_SOURCE_BYTES:
            raise ValueError("conversion sources exceed the size limit")
        output = request.output.expanduser().resolve(strict=False)
        if not output.parent.is_dir() or output.parent.is_symlink():
            raise ValueError("conversion output folder is invalid")
        if output.exists():
            raise FileExistsError(output)
        if output in sources:
            raise ValueError("conversion output cannot replace a source")
        definition = self._presets[preset]
        extensions = {str(value).casefold() for value in definition["extensions"]}
        if output.suffix.casefold() not in extensions:
            raise ValueError("output extension does not match the selected preset")
        if preset == "join-copy":
            if len(sources) < 2 or len({path.suffix.casefold() for path in sources}) != 1:
                raise ValueError("join-copy requires at least two files of the same type")
            if output.suffix.casefold() != sources[0].suffix.casefold():
                raise ValueError("join-copy output must keep the source extension")
        elif len(sources) != 1:
            raise ValueError("the selected preset accepts one source")
        for name, value in (("start", request.start_time), ("end", request.end_time)):
            if value is not None and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"conversion {name} time is invalid")
        if request.end_time is not None and request.end_time <= (request.start_time or 0):
            raise ValueError("conversion end time must be after start")
        remove_ranges = self._validated_removal_ranges(request.remove_ranges)
        if preset == "ad-trim-h264":
            if request.start_time is not None or request.end_time is not None:
                raise ValueError(
                    "ad trim uses removal ranges instead of start/end clipping"
                )
            if not remove_ranges:
                raise ValueError("ad trim needs at least one removal range")
        elif remove_ranges:
            raise ValueError("removal ranges require the ad-trim-h264 preset")
        return sources, output, preset, remove_ranges

    def _load_presets(self) -> dict[str, dict[str, object]]:
        document = json.loads(self.preset_path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("schema_version") != 1:
            raise ValueError("media-convert preset schema is unsupported")
        raw = document.get("presets")
        if not isinstance(raw, dict) or not raw:
            raise ValueError("media-convert presets are missing")
        allowed = {"strategy", "extensions", "estimate_ratio", "args", "gpu_args"}
        presets: dict[str, dict[str, object]] = {}
        for preset_id, definition in raw.items():
            if (
                not isinstance(preset_id, str)
                or not preset_id
                or not isinstance(definition, dict)
                or not set(definition).issubset(allowed)
                or not {"strategy", "extensions", "estimate_ratio", "args"}.issubset(definition)
                or not isinstance(definition["extensions"], list)
                or not isinstance(definition["args"], list)
            ):
                raise ValueError("media-convert preset is invalid")
            presets[preset_id] = definition
        return presets

    @staticmethod
    def _time_value(value: float) -> str:
        return f"{float(value):.3f}"

    @staticmethod
    def _validated_removal_ranges(
        raw_ranges: object,
    ) -> tuple[tuple[float, float], ...]:
        if not isinstance(raw_ranges, tuple) or len(raw_ranges) > MAX_REMOVAL_RANGES:
            raise ValueError("ad trim removal ranges are invalid")
        result: list[tuple[float, float]] = []
        previous_end = -1.0
        for raw_range in raw_ranges:
            if not isinstance(raw_range, tuple) or len(raw_range) != 2:
                raise ValueError("ad trim removal ranges are invalid")
            start, end = raw_range
            if any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in (start, end)
            ):
                raise ValueError("ad trim removal ranges are invalid")
            normalized = (float(start), float(end))
            if (
                normalized[0] < 0
                or normalized[1] <= normalized[0]
                or normalized[1] > MAX_MEDIA_SECONDS
                or normalized[0] < previous_end
            ):
                raise ValueError(
                    "ad trim ranges must be ordered, separate and inside seven days"
                )
            result.append(normalized)
            previous_end = normalized[1]
        return tuple(result)

    @staticmethod
    def _removal_selector(ranges: tuple[tuple[float, float], ...]) -> str:
        expressions = "+".join(
            "between(t\\," + f"{start:.3f}\\,{end:.3f})"
            for start, end in ranges
        )
        return f"not({expressions})"
