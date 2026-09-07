"""Disabled-by-default FFmpeg conversion queue with atomic output handling."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import Event, RLock, Thread
import time
import uuid

from core.conversion.models import (
    ConversionCapabilities,
    ConversionPlan,
    ConversionRequest,
    ConversionState,
    ConversionTask,
)
from core.logging.redaction import bounded_redacted_text
from core.storage.atomic import commit_file_without_overwrite

MAX_SOURCES = 100
MAX_SOURCE_BYTES = 4 * 1024**4
WATERMARK_IMAGE_EXTENSIONS = frozenset(
    {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
)
MAX_REMOVAL_RANGES = 50
MAX_MEDIA_SECONDS = 604_800.0
MAX_FFMPEG_DIAGNOSTIC_BYTES = 64 * 1024
MAX_CAPABILITY_OUTPUT_BYTES = 512 * 1024
MAX_FFPROBE_OUTPUT_BYTES = 256 * 1024
MAX_STREAM_HASH_OUTPUT_BYTES = 256
STDERR_READER_JOIN_SECONDS = 2.0
TOOL_PROBE_TIMEOUT_SECONDS = 8.0
FFPROBE_TIMEOUT_SECONDS = 20.0
STREAM_HASH_TIMEOUT_SECONDS = 300.0
DEFAULT_CONVERSION_FREE_SPACE_RESERVE = 256 * 1024 * 1024
LOCAL_PROTOCOL_WHITELIST = "file,pipe"
SUBPROCESS_CREATION_FLAGS = (
    getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
)


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


class ConversionService:
    provider_id = "media-convert"
    display_name = "Media Convert"

    def __init__(
        self,
        ffmpeg: Path | None,
        preset_path: Path,
        temp_root: Path,
        *,
        ffprobe: Path | None = None,
    ) -> None:
        self.ffmpeg = Path(ffmpeg).resolve() if ffmpeg is not None else None
        self.ffprobe = Path(ffprobe).resolve() if ffprobe is not None else None
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
        self._capabilities: ConversionCapabilities | None = None

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def available(self) -> bool:
        return (
            self.ffmpeg is not None
            and self.ffmpeg.is_file()
            and self.ffprobe is not None
            and self.ffprobe.is_file()
        )

    def capabilities(self, *, refresh: bool = False) -> ConversionCapabilities:
        """Return cached, observed local FFmpeg capabilities without guessing."""

        with self._lock:
            cached = self._capabilities
        if cached is not None and not refresh:
            return cached

        outputs: dict[str, str] = {}
        errors: list[str] = []
        for flag in (
            "-version",
            "-buildconf",
            "-formats",
            "-encoders",
            "-filters",
            "-hwaccels",
        ):
            text, error = self._probe_text(flag)
            outputs[flag] = text
            if error:
                errors.append(f"{flag}: {error}")

        version = next(
            (
                line.strip()
                for line in outputs["-version"].splitlines()
                if line.strip().casefold().startswith("ffmpeg version ")
            ),
            "",
        )
        build_configuration = "\n".join(
            line.strip()
            for line in outputs["-buildconf"].splitlines()
            if line.strip().startswith("--")
        )
        result = ConversionCapabilities(
            ffmpeg_version=version,
            build_configuration=build_configuration,
            formats=self._parse_capability_table(
                outputs["-formats"], flag_widths={1, 2}, split_commas=True
            ),
            encoders=self._parse_capability_table(
                outputs["-encoders"], flag_widths={6}
            ),
            filters=self._parse_capability_table(
                outputs["-filters"], flag_widths={2, 3}
            ),
            hwaccels=frozenset(
                line.strip().casefold()
                for line in outputs["-hwaccels"].splitlines()
                if re.fullmatch(r"[a-z0-9_]+", line.strip().casefold())
                and line.strip().casefold() not in {"hardware", "acceleration", "methods"}
            ),
            errors=tuple(errors),
        )
        with self._lock:
            self._capabilities = result
        return result

    def set_enabled(self, enabled: bool) -> int:
        if enabled and not self.available:
            raise RuntimeError(
                "FFmpeg and ffprobe are required before Media Convert can be enabled"
            )
        with self._lock:
            self._enabled = enabled
        return 0 if enabled else self.cancel_all()

    def preset_ids(self) -> tuple[str, ...]:
        return tuple(self._presets)

    def preview(self, request: ConversionRequest) -> ConversionPlan:
        sources, output, preset, remove_ranges, watermark = self._validate(request)
        definition = self._presets[preset]
        ratio = float(definition["estimate_ratio"])
        estimated = max(1, int(sum(path.stat().st_size for path in sources) * ratio))
        ffmpeg = str(self.ffmpeg) if self.ffmpeg is not None else "ffmpeg"
        command = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-protocol_whitelist",
            LOCAL_PROTOCOL_WHITELIST,
            "-n",
        ]
        if preset == "join-copy":
            command.extend(("-f", "concat", "-safe", "1", "-i", "@CONCAT_LIST@"))
        else:
            if request.start_time is not None:
                command.extend(("-ss", self._time_value(request.start_time)))
            command.extend(("-i", str(sources[0])))
            if watermark is not None:
                command.extend(("-i", str(watermark)))
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
                watermark=watermark,
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
        self._validate_runtime_requirements(plan)
        self._preflight_output(plan)
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
            return_code, diagnostic = self._run(command, task.cancel_event)
            if (
                return_code != 0
                and not task.cancel_event.is_set()
                and plan.fallback_command is not None
            ):
                part.unlink(missing_ok=True)
                command = self._materialize(plan.fallback_command, plan, part, concat)
                return_code, diagnostic = self._run(command, task.cancel_event)
            if task.cancel_event.is_set():
                raise RuntimeError("conversion cancelled")
            if return_code != 0 or not part.is_file():
                message = f"FFmpeg exited with code {return_code}"
                if diagnostic:
                    message = f"{message}: {diagnostic}"
                raise RuntimeError(message)
            self._verify_output(
                part,
                plan=plan,
                cancel_event=task.cancel_event,
            )
            if output.exists():
                raise FileExistsError(output)
            commit_file_without_overwrite(part, output)
            return output
        finally:
            part.unlink(missing_ok=True)
            concat.unlink(missing_ok=True)

    def _run(
        self, command: tuple[str, ...], cancel_event: object
    ) -> tuple[int, str]:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=SUBPROCESS_CREATION_FLAGS,
        )
        stderr_tail = bytearray()
        stderr_truncated = False

        def read_stderr() -> None:
            nonlocal stderr_truncated
            assert process.stderr is not None
            while True:
                try:
                    chunk = process.stderr.read(4096)
                except (OSError, ValueError):
                    return
                if not chunk:
                    return
                stderr_tail.extend(chunk)
                if len(stderr_tail) > MAX_FFMPEG_DIAGNOSTIC_BYTES:
                    del stderr_tail[
                        : len(stderr_tail) - MAX_FFMPEG_DIAGNOSTIC_BYTES
                    ]
                    stderr_truncated = True

        stderr_thread = Thread(
            target=read_stderr,
            name="media-convert-stderr",
            daemon=True,
        )
        with self._lock:
            self._process = process
        stderr_thread.start()
        try:
            while process.poll() is None:
                if cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                time.sleep(0.05)
            stderr_thread.join(timeout=STDERR_READER_JOIN_SECONDS)
            stderr_reader_incomplete = stderr_thread.is_alive()
            raw_diagnostic = bytes(stderr_tail)
            if stderr_truncated:
                first_line_break = raw_diagnostic.find(b"\n")
                raw_diagnostic = (
                    raw_diagnostic[first_line_break + 1 :]
                    if first_line_break >= 0
                    else b""
                )
            diagnostic = raw_diagnostic.decode(
                "utf-8", errors="replace"
            ).strip()
            markers = []
            if stderr_truncated:
                markers.append("[FFmpeg stderr truncated]")
            if stderr_reader_incomplete:
                markers.append("[FFmpeg stderr reader incomplete]")
            if markers:
                marker = " ".join(markers)
                marker_size = len(("\n" + marker).encode("utf-8"))
                diagnostic = bounded_redacted_text(
                    diagnostic,
                    max_utf8_bytes=max(
                        1, MAX_FFMPEG_DIAGNOSTIC_BYTES - marker_size
                    ),
                )
                diagnostic = f"{diagnostic}\n{marker}" if diagnostic else marker
            else:
                diagnostic = bounded_redacted_text(
                    diagnostic,
                    max_utf8_bytes=MAX_FFMPEG_DIAGNOSTIC_BYTES,
                )
            return int(process.returncode or 0), diagnostic
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def _preflight_output(self, plan: ConversionPlan) -> None:
        required = plan.estimated_bytes + DEFAULT_CONVERSION_FREE_SPACE_RESERVE
        free = shutil.disk_usage(plan.request.output.parent).free
        if free < required:
            raise RuntimeError(
                "insufficient conversion disk space: "
                f"requires {required // (1024 * 1024)} MiB including reserve, "
                f"available {free // (1024 * 1024)} MiB"
            )

    def _validate_runtime_requirements(self, plan: ConversionPlan) -> None:
        """Validate local encoder and input-codec requirements before queuing."""

        definition = self._presets[plan.request.preset]
        required_encoder = definition.get("required_encoder")
        if isinstance(required_encoder, str):
            capabilities = self.capabilities()
            if required_encoder not in capabilities.encoders:
                raise RuntimeError(
                    f"required FFmpeg encoder is unavailable: {required_encoder}"
                )

        required_audio_codec = definition.get("required_input_audio_codec")
        if not isinstance(required_audio_codec, str):
            return
        required_audio_codec = required_audio_codec.casefold()
        return_code, raw_document, diagnostic = self._run_ffprobe(
            plan.request.sources[0]
        )
        if return_code != 0:
            message = "ffprobe source validation failed"
            if diagnostic:
                message = f"{message}: {diagnostic}"
            raise RuntimeError(message)
        try:
            document = json.loads(raw_document.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "ffprobe source validation failed: invalid JSON"
            ) from error
        if not isinstance(document, dict):
            raise RuntimeError("ffprobe source validation failed: invalid document")
        streams = document.get("streams")
        if not isinstance(streams, list):
            raise RuntimeError("ffprobe source validation failed: streams are missing")
        audio_codecs = tuple(
            str(stream.get("codec_name", "")).casefold()
            for stream in streams
            if isinstance(stream, dict)
            and str(stream.get("codec_type", "")).casefold() == "audio"
            and isinstance(stream.get("codec_name"), str)
        )
        if not audio_codecs or audio_codecs[0] != required_audio_codec:
            detected = audio_codecs[0] if audio_codecs else "none"
            display_codec = (
                "Opus" if required_audio_codec == "opus" else required_audio_codec
            )
            raise RuntimeError(
                f"this preset requires {display_codec} source audio for passthrough; "
                f"detected: {detected}"
            )

    def _probe_text(self, flag: str) -> tuple[str, str]:
        if self.ffmpeg is None or not self.ffmpeg.is_file():
            return "", "FFmpeg is unavailable"
        command = [str(self.ffmpeg), "-nostdin", "-hide_banner", flag]
        return_code, raw, _stderr, truncated, _ = self._run_bounded_capture(
            command,
            timeout=TOOL_PROBE_TIMEOUT_SECONDS,
            stdout_limit=MAX_CAPABILITY_OUTPUT_BYTES,
            stderr_limit=0,
            combine_stderr=True,
        )
        text = bounded_redacted_text(
            raw.decode("utf-8", errors="replace"),
            max_utf8_bytes=MAX_CAPABILITY_OUTPUT_BYTES,
        ).strip()
        if return_code == -1:
            return "", text or "probe timed out"
        if return_code == -2:
            return "", text or "probe could not be started"
        if return_code != 0:
            return "", text or f"probe exited with code {return_code}"
        if truncated:
            return "", "probe output exceeded the size limit"
        return text, ""

    @staticmethod
    def _parse_capability_table(
        text: str,
        *,
        flag_widths: set[int],
        split_commas: bool = False,
    ) -> frozenset[str]:
        names: set[str] = set()
        for line in text.splitlines():
            tokens = line.split()
            if len(tokens) < 2:
                continue
            flags, raw_name = tokens[0], tokens[1]
            if len(flags) not in flag_widths or any(
                not (character == "." or character.isupper())
                for character in flags
            ):
                continue
            values = raw_name.split(",") if split_commas else (raw_name,)
            names.update(
                value.casefold()
                for value in values
                if re.fullmatch(r"[A-Za-z0-9_]+", value)
            )
        return frozenset(names)

    def _run_ffprobe(
        self,
        output: Path,
        *,
        cancel_event: object | None = None,
    ) -> tuple[int, bytes, str]:
        if self.ffprobe is None or not self.ffprobe.is_file():
            return 1, b"", "ffprobe is unavailable"
        command = [
            str(self.ffprobe),
            "-v",
            "error",
            "-protocol_whitelist",
            LOCAL_PROTOCOL_WHITELIST,
            "-show_entries",
            (
                "stream=index,codec_type,codec_name,profile,pix_fmt,width,height,"
                "r_frame_rate,avg_frame_rate:format=format_name,duration,size"
            ),
            "-of",
            "json",
            str(output),
        ]
        return_code, stdout, stderr, stdout_truncated, stderr_truncated = (
            self._run_bounded_capture(
                command,
                timeout=FFPROBE_TIMEOUT_SECONDS,
                stdout_limit=MAX_FFPROBE_OUTPUT_BYTES,
                stderr_limit=MAX_FFMPEG_DIAGNOSTIC_BYTES,
                cancel_event=cancel_event,
            )
        )
        if return_code == -1:
            return 1, b"", "ffprobe timed out"
        if return_code == -2:
            diagnostic = bounded_redacted_text(
                stderr.decode("utf-8", errors="replace"),
                max_utf8_bytes=MAX_FFMPEG_DIAGNOSTIC_BYTES,
            )
            return 1, b"", diagnostic or "ffprobe could not be started"
        if stdout_truncated:
            return 1, b"", "ffprobe output exceeded the size limit"
        diagnostic = bounded_redacted_text(
            stderr.decode("utf-8", errors="replace"),
            max_utf8_bytes=MAX_FFMPEG_DIAGNOSTIC_BYTES,
        )
        if stderr_truncated:
            diagnostic = (
                f"{diagnostic}\n[ffprobe stderr truncated]"
                if diagnostic
                else "[ffprobe stderr truncated]"
            )
        return return_code, stdout, diagnostic

    @staticmethod
    def _run_bounded_capture(
        command: list[str],
        *,
        timeout: float,
        stdout_limit: int,
        stderr_limit: int,
        combine_stderr: bool = False,
        cancel_event: object | None = None,
    ) -> tuple[int, bytes, bytes, bool, bool]:
        """Drain child output while retaining no more than the stated limits."""

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if combine_stderr else subprocess.PIPE,
                creationflags=SUBPROCESS_CREATION_FLAGS,
            )
        except OSError as error:
            message = str(error).encode("utf-8", errors="replace")[:4096]
            return -2, message, message, False, False

        buffers = [bytearray(), bytearray()]
        truncated = [False, False]

        def drain(stream: object, index: int, limit: int) -> None:
            if stream is None:
                return
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                remaining = max(0, limit - len(buffers[index]))
                buffers[index].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[index] = True

        readers = [
            Thread(target=drain, args=(process.stdout, 0, stdout_limit), daemon=True)
        ]
        if not combine_stderr:
            readers.append(
                Thread(target=drain, args=(process.stderr, 1, stderr_limit), daemon=True)
            )
        for reader in readers:
            reader.start()
        deadline = time.monotonic() + timeout
        while True:
            observed_return_code = process.poll()
            if observed_return_code is not None:
                return_code = int(observed_return_code)
                break
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return_code = -3
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                return_code = -1
                break
            try:
                process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
        for reader in readers:
            reader.join(timeout=STDERR_READER_JOIN_SECONDS)
        return (
            return_code,
            bytes(buffers[0]),
            bytes(buffers[1]),
            truncated[0],
            truncated[1],
        )

    def _verify_output(
        self,
        output: Path,
        *,
        plan: ConversionPlan | None = None,
        cancel_event: object | None = None,
    ) -> None:
        if not output.is_file() or output.stat().st_size <= 0:
            raise RuntimeError("ffprobe validation failed: output is empty")
        document = self._probe_document(
            output,
            "ffprobe validation failed",
            cancel_event=cancel_event,
        )
        if plan is not None:
            self._verify_output_contract(
                plan,
                document,
                output,
                cancel_event=cancel_event,
            )

    def _probe_document(
        self,
        path: Path,
        failure_prefix: str,
        *,
        cancel_event: object | None = None,
    ) -> dict[str, object]:
        return_code, raw_document, diagnostic = self._run_ffprobe(
            path,
            cancel_event=cancel_event,
        )
        if return_code == -3:
            raise RuntimeError("conversion cancelled")
        if return_code != 0:
            message = failure_prefix
            if diagnostic:
                message = f"{message}: {diagnostic}"
            raise RuntimeError(message)
        try:
            document = json.loads(raw_document.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"{failure_prefix}: invalid JSON") from error
        if not isinstance(document, dict):
            raise RuntimeError(f"{failure_prefix}: invalid document")
        streams = document.get("streams")
        if (
            not isinstance(streams, list)
            or not streams
            or any(not isinstance(stream, dict) for stream in streams)
        ):
            raise RuntimeError(f"{failure_prefix}: no readable media stream")
        return document

    def _verify_output_contract(
        self,
        plan: ConversionPlan,
        output_document: dict[str, object],
        output: Path,
        *,
        cancel_event: object | None = None,
    ) -> None:
        definition = self._presets[plan.request.preset]
        contract = definition.get("output_contract")
        if not isinstance(contract, dict):
            return

        output_video = self._first_stream(output_document, "video")
        output_audio = self._first_stream(output_document, "audio")
        format_document = output_document.get("format")
        if not isinstance(format_document, dict):
            format_document = {}

        allowed_formats = self._normalized_values(contract.get("format_names"))
        if allowed_formats:
            detected_formats = {
                value.strip().casefold()
                for value in str(format_document.get("format_name", "")).split(",")
                if value.strip()
            }
            if detected_formats.isdisjoint(allowed_formats):
                self._raise_output_contract("container format does not match preset")

        expected_video_codec = self._normalized_text(contract.get("video_codec"))
        if expected_video_codec and (
            output_video is None
            or self._normalized_text(output_video.get("codec_name"))
            != expected_video_codec
        ):
            self._raise_output_contract("video codec does not match preset")

        allowed_profiles = self._normalized_values(contract.get("video_profiles"))
        if allowed_profiles and (
            output_video is None
            or self._normalized_text(output_video.get("profile"))
            not in allowed_profiles
        ):
            self._raise_output_contract("video profile does not match preset")

        allowed_pixel_formats = self._normalized_values(
            contract.get("video_pixel_formats")
        )
        if allowed_pixel_formats and (
            output_video is None
            or self._normalized_text(output_video.get("pix_fmt"))
            not in allowed_pixel_formats
        ):
            self._raise_output_contract("video pixel format is not 10-bit")

        expected_audio_codec = self._normalized_text(contract.get("audio_codec"))
        if expected_audio_codec and (
            output_audio is None
            or self._normalized_text(output_audio.get("codec_name"))
            != expected_audio_codec
        ):
            self._raise_output_contract("audio codec does not match passthrough source")

        preserve_dimensions = contract.get("preserve_dimensions") is True
        preserve_frame_rate = contract.get("preserve_frame_rate") is True
        if preserve_dimensions or preserve_frame_rate:
            source_document = self._probe_document(
                plan.request.sources[0],
                "output contract failed: source probe",
                cancel_event=cancel_event,
            )
            source_video = self._first_stream(source_document, "video")
            if source_video is None or output_video is None:
                self._raise_output_contract("source or output video stream is missing")

            if preserve_dimensions:
                source_dimensions = (
                    self._positive_integer(source_video.get("width")),
                    self._positive_integer(source_video.get("height")),
                )
                output_dimensions = (
                    self._positive_integer(output_video.get("width")),
                    self._positive_integer(output_video.get("height")),
                )
                if (
                    None in source_dimensions
                    or None in output_dimensions
                    or output_dimensions != source_dimensions
                ):
                    self._raise_output_contract("video dimensions changed")

            if preserve_frame_rate:
                source_rates = self._frame_rates(source_video)
                output_rates = self._frame_rates(output_video)
                if None in source_rates or None in output_rates:
                    self._raise_output_contract("frame rate metadata is missing")
                if source_rates[0] == source_rates[1] and any(
                    rate != source_rates[0] for rate in output_rates
                ):
                    self._raise_output_contract("constant frame rate changed")

        if contract.get("preserve_audio_packets") is True:
            source_digest = self._stream_digest(
                plan.request.sources[0],
                cancel_event=cancel_event,
            )
            output_digest = self._stream_digest(
                output,
                cancel_event=cancel_event,
            )
            if source_digest != output_digest:
                self._raise_output_contract("audio packet digest changed")

    @staticmethod
    def _first_stream(
        document: dict[str, object],
        codec_type: str,
    ) -> dict[str, object] | None:
        streams = document.get("streams")
        if not isinstance(streams, list):
            return None
        expected = codec_type.casefold()
        return next(
            (
                stream
                for stream in streams
                if isinstance(stream, dict)
                and str(stream.get("codec_type", "")).casefold() == expected
            ),
            None,
        )

    @staticmethod
    def _normalized_text(value: object) -> str:
        return value.strip().casefold() if isinstance(value, str) else ""

    @classmethod
    def _normalized_values(cls, value: object) -> frozenset[str]:
        if not isinstance(value, list):
            return frozenset()
        return frozenset(
            normalized
            for item in value
            if (normalized := cls._normalized_text(item))
        )

    @staticmethod
    def _positive_integer(value: object) -> int | None:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        return None

    @staticmethod
    def _frame_rate(value: object) -> Fraction | None:
        if not isinstance(value, str):
            return None
        try:
            rate = Fraction(value)
        except (ValueError, ZeroDivisionError):
            return None
        return rate if rate > 0 else None

    @classmethod
    def _frame_rates(
        cls,
        stream: dict[str, object],
    ) -> tuple[Fraction | None, Fraction | None]:
        return (
            cls._frame_rate(stream.get("r_frame_rate")),
            cls._frame_rate(stream.get("avg_frame_rate")),
        )

    def _stream_digest(
        self,
        path: Path,
        *,
        cancel_event: object | None = None,
    ) -> str:
        if self.ffmpeg is None or not self.ffmpeg.is_file():
            self._raise_output_contract("FFmpeg is unavailable for audio validation")
        command = [
            str(self.ffmpeg),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-protocol_whitelist",
            LOCAL_PROTOCOL_WHITELIST,
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-c",
            "copy",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "pipe:1",
        ]
        return_code, stdout, stderr, stdout_truncated, stderr_truncated = (
            self._run_bounded_capture(
                command,
                timeout=STREAM_HASH_TIMEOUT_SECONDS,
                stdout_limit=MAX_STREAM_HASH_OUTPUT_BYTES,
                stderr_limit=MAX_FFMPEG_DIAGNOSTIC_BYTES,
                cancel_event=cancel_event,
            )
        )
        if return_code == -3:
            raise RuntimeError("conversion cancelled")
        if return_code != 0 or stdout_truncated or stderr_truncated:
            diagnostic = bounded_redacted_text(
                stderr.decode("utf-8", errors="replace"),
                max_utf8_bytes=MAX_FFMPEG_DIAGNOSTIC_BYTES,
            ).strip()
            detail = "audio packet hash could not be calculated"
            if diagnostic:
                detail = f"{detail}: {diagnostic}"
            self._raise_output_contract(detail)
        match = re.fullmatch(rb"SHA256=([0-9a-fA-F]{64})\r?\n?", stdout)
        if match is None:
            self._raise_output_contract("audio packet hash response is invalid")
        return match.group(1).decode("ascii").casefold()

    @staticmethod
    def _raise_output_contract(detail: str) -> None:
        raise RuntimeError(f"output contract failed: {detail}")

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
        Path | None,
    ]:
        if not isinstance(request, ConversionRequest):
            raise TypeError("invalid conversion request")
        preset = request.preset.strip().casefold()
        if preset not in self._presets:
            raise ValueError("unsupported conversion preset")
        if not 1 <= len(request.sources) <= MAX_SOURCES:
            raise ValueError("conversion needs 1 to 100 sources")
        expanded_sources = tuple(path.expanduser() for path in request.sources)
        if any(_is_linklike(path) for path in expanded_sources):
            raise ValueError("conversion source must be a regular file")
        sources = tuple(path.resolve() for path in expanded_sources)
        total = 0
        for source in sources:
            if not source.is_file():
                raise ValueError("conversion source must be a regular file")
            total += source.stat().st_size
        watermark: Path | None = None
        if request.watermark is not None:
            if not isinstance(request.watermark, Path):
                raise ValueError("watermark must be a local image file")
            expanded_watermark = request.watermark.expanduser()
            if _is_linklike(expanded_watermark):
                raise ValueError("watermark must be a regular local image file")
            watermark = expanded_watermark.resolve()
            if not watermark.is_file():
                raise ValueError("watermark must be a regular local image file")
            total += watermark.stat().st_size
        if total > MAX_SOURCE_BYTES:
            raise ValueError("conversion sources exceed the size limit")
        expanded_output = request.output.expanduser()
        if _is_linklike(expanded_output) or _is_linklike(expanded_output.parent):
            raise ValueError("conversion output folder is invalid")
        output = expanded_output.resolve(strict=False)
        if not output.parent.is_dir():
            raise ValueError("conversion output folder is invalid")
        if output.exists():
            raise FileExistsError(output)
        if output in sources or output == watermark:
            raise ValueError("conversion output cannot replace a source")
        definition = self._presets[preset]
        source_extensions = {
            str(value).casefold()
            for value in definition.get("source_extensions", ())
        }
        if source_extensions and sources[0].suffix.casefold() not in source_extensions:
            raise ValueError("source extension does not match the selected preset")
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
        if preset == "watermark-h264":
            if watermark is None:
                raise ValueError("watermark-h264 needs one watermark image")
            if watermark.suffix.casefold() not in WATERMARK_IMAGE_EXTENSIONS:
                raise ValueError("watermark image extension is unsupported")
        elif watermark is not None:
            raise ValueError("watermark image requires the watermark-h264 preset")
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
        return sources, output, preset, remove_ranges, watermark

    def _load_presets(self) -> dict[str, dict[str, object]]:
        document = json.loads(self.preset_path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("schema_version") != 1:
            raise ValueError("media-convert preset schema is unsupported")
        raw = document.get("presets")
        if not isinstance(raw, dict) or not raw:
            raise ValueError("media-convert presets are missing")
        allowed = {
            "strategy",
            "source_extensions",
            "extensions",
            "estimate_ratio",
            "args",
            "gpu_args",
            "required_encoder",
            "required_input_audio_codec",
            "output_contract",
        }
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
                or (
                    "source_extensions" in definition
                    and not isinstance(definition["source_extensions"], list)
                )
                or any(
                    requirement in definition
                    and (
                        not isinstance(definition[requirement], str)
                        or not re.fullmatch(
                            r"[a-z0-9_]+",
                            str(definition[requirement]).casefold(),
                        )
                    )
                    for requirement in (
                        "required_encoder",
                        "required_input_audio_codec",
                    )
                )
                or (
                    "output_contract" in definition
                    and not self._valid_output_contract(
                        definition["output_contract"]
                    )
                )
            ):
                raise ValueError("media-convert preset is invalid")
            presets[preset_id] = definition
        return presets

    @classmethod
    def _valid_output_contract(cls, value: object) -> bool:
        if not isinstance(value, dict) or not value:
            return False
        allowed = {
            "format_names",
            "video_codec",
            "video_profiles",
            "video_pixel_formats",
            "audio_codec",
            "preserve_dimensions",
            "preserve_frame_rate",
            "preserve_audio_packets",
        }
        if not set(value).issubset(allowed):
            return False
        for key in ("video_codec", "audio_codec"):
            if key in value and (
                not isinstance(value[key], str)
                or not re.fullmatch(r"[A-Za-z0-9_]+", value[key])
            ):
                return False
        for key in ("format_names", "video_profiles", "video_pixel_formats"):
            if key not in value:
                continue
            items = value[key]
            if (
                not isinstance(items, list)
                or not 1 <= len(items) <= 16
                or any(
                    not isinstance(item, str)
                    or not item.strip()
                    or len(item) > 64
                    or not item.isprintable()
                    for item in items
                )
            ):
                return False
        for key in (
            "preserve_dimensions",
            "preserve_frame_rate",
            "preserve_audio_packets",
        ):
            if key in value and not isinstance(value[key], bool):
                return False
        return True

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
