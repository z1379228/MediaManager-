"""Local dependency health checks without downloads or installation."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from core.runtime_policy import DENO_EXECUTABLE_SHA256, FFMPEG_PORTABLE_SHA256


CORE_DEPENDENCY_IDS = frozenset(
    {"yt-dlp", "yt-dlp-ejs", "ffmpeg", "javascript-runtime"}
)


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    dependency_id: str
    label: str
    available: bool
    version: str
    path: str
    detail: str


@dataclass(frozen=True, slots=True)
class DependencyReport:
    statuses: tuple[DependencyStatus, ...]

    @property
    def ready_count(self) -> int:
        return sum(status.available for status in self.statuses)

    @property
    def total_count(self) -> int:
        return len(self.statuses)

    @property
    def issue_count(self) -> int:
        return self.total_count - self.ready_count

    @property
    def core_statuses(self) -> tuple[DependencyStatus, ...]:
        return tuple(
            status
            for status in self.statuses
            if status.dependency_id in CORE_DEPENDENCY_IDS
        )

    @property
    def optional_statuses(self) -> tuple[DependencyStatus, ...]:
        return tuple(
            status
            for status in self.statuses
            if status.dependency_id not in CORE_DEPENDENCY_IDS
        )

    @property
    def core_ready_count(self) -> int:
        return sum(status.available for status in self.core_statuses)

    @property
    def optional_ready_count(self) -> int:
        return sum(status.available for status in self.optional_statuses)

    @property
    def youtube_ready(self) -> bool:
        statuses = {status.dependency_id: status for status in self.statuses}
        return all(
            dependency_id in statuses and statuses[dependency_id].available
            for dependency_id in CORE_DEPENDENCY_IDS
        )


Runner = Callable[[Sequence[str]], tuple[int, str]]

JAVASCRIPT_RUNTIME_SPECS = (
    ("deno", ("--version",), (2, 3, 0), "deno", "Deno"),
    ("node", ("--version",), (22, 0, 0), "node", "Node.js"),
    ("qjs", ("--version",), (2023, 12, 9), "quickjs", "QuickJS"),
)
YTDLP_MINIMUM = (2026, 7, 4)
EJS_MINIMUM = (0, 8, 0)
FFMPEG_MINIMUM = (6, 0, 0)


def find_executable(application_root: Path, name: str) -> str | None:
    suffix = ".exe" if os.name == "nt" else ""
    executable = name if name.lower().endswith(suffix) else f"{name}{suffix}"
    candidates = [
        application_root / "tools" / executable,
        application_root / executable,
    ]
    if os.name == "nt" and name in {"mega-get", "mega-speedlimit"}:
        batch_name = f"{name}.bat"
        candidates.extend(
            (
                application_root / "tools" / batch_name,
                application_root / batch_name,
            )
        )
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(Path(local_app_data) / "MEGAcmd" / batch_name)
    for candidate in candidates:
        if candidate.is_file():
            if candidate.parent == application_root / "tools":
                expected = {
                    "deno": DENO_EXECUTABLE_SHA256,
                    "ffmpeg": FFMPEG_PORTABLE_SHA256["ffmpeg.exe"],
                    "ffprobe": FFMPEG_PORTABLE_SHA256["ffprobe.exe"],
                }.get(name)
                if (
                    expected is not None
                    and hashlib.sha256(candidate.read_bytes()).hexdigest() != expected
                ):
                    return None
            return str(candidate.resolve())
    return shutil.which(name)


def _run_version(command: Sequence[str]) -> tuple[int, str]:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            check=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    output = (result.stdout or result.stderr).strip()
    return result.returncode, output.splitlines()[0] if output else ""


def _numbers(value: str) -> tuple[int, ...]:
    match = re.search(r"(?<!\d)(\d{1,4}(?:[.-]\d+){1,3})", value)
    if not match:
        return ()
    return tuple(int(part) for part in re.split(r"[.-]", match.group(1)))


def _at_least(value: str, minimum: tuple[int, ...]) -> bool:
    found = _numbers(value)
    if not found:
        return False
    size = max(len(found), len(minimum))
    return found + (0,) * (size - len(found)) >= minimum + (0,) * (
        size - len(minimum)
    )


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        if distribution == "yt-dlp":
            from yt_dlp.version import __version__

            return __version__
        if distribution == "yt-dlp-ejs":
            from yt_dlp_ejs import version

            return version
    except ImportError:
        pass
    return ""


def _ejs_solver_ready() -> bool:
    try:
        root = importlib.resources.files("yt_dlp_ejs.yt.solver")
        return all(
            (root / name).is_file() and bool((root / name).read_bytes())
            for name in ("core.min.js", "lib.min.js")
        )
    except (ImportError, OSError, TypeError):
        return False


def _executable_status(
    application_root: Path,
    *,
    name: str,
    args: tuple[str, ...],
    minimum: tuple[int, ...] | None,
    runner: Runner,
) -> tuple[bool, str, str]:
    path = find_executable(application_root, name)
    if not path:
        return False, "", ""
    returncode, output = runner((path, *args))
    if returncode != 0:
        return False, output, path
    if minimum is not None and not _at_least(output, minimum):
        return False, output, path
    return True, output, path


def find_javascript_runtime(
    application_root: Path,
    *,
    runner: Runner = _run_version,
) -> tuple[str, str] | None:
    for name, args, minimum, runtime_key, _label in JAVASCRIPT_RUNTIME_SPECS:
        available, _version, path = _executable_status(
            application_root.resolve(),
            name=name,
            args=args,
            minimum=minimum,
            runner=runner,
        )
        if available:
            return runtime_key, path
    return None


def check_dependencies(
    application_root: Path,
    *,
    data_root: Path | None = None,
    runner: Runner = _run_version,
) -> DependencyReport:
    application_root = application_root.resolve()

    ytdlp_version = _package_version("yt-dlp")
    ytdlp_ready = bool(ytdlp_version) and _at_least(
        ytdlp_version, YTDLP_MINIMUM
    )
    ytdlp = DependencyStatus(
        "yt-dlp",
        "yt-dlp",
        ytdlp_ready,
        ytdlp_version,
        "",
        (
            "YouTube 解析與下載可用"
            if ytdlp_ready
            else "缺少或版本過舊的 yt-dlp，YouTube 搜尋與下載無法執行"
        ),
    )

    ejs_version = _package_version("yt-dlp-ejs")
    ejs_ready = (
        bool(ejs_version)
        and _at_least(ejs_version, EJS_MINIMUM)
        and _ejs_solver_ready()
    )
    ejs = DependencyStatus(
        "yt-dlp-ejs",
        "yt-dlp EJS",
        ejs_ready,
        ejs_version,
        "",
        (
            "YouTube JavaScript challenge 元件可用"
            if ejs_ready
            else "缺少、過舊或不完整的 EJS challenge 元件，完整 YouTube 支援會受限"
        ),
    )

    ffmpeg_ok, ffmpeg_version, ffmpeg_path = _executable_status(
        application_root,
        name="ffmpeg",
        args=("-version",),
        minimum=FFMPEG_MINIMUM,
        runner=runner,
    )
    ffprobe_ok, _, ffprobe_path = _executable_status(
        application_root,
        name="ffprobe",
        args=("-version",),
        minimum=FFMPEG_MINIMUM,
        runner=runner,
    )
    media_tools_ok = ffmpeg_ok and ffprobe_ok
    media_tools_path = "; ".join(
        value for value in (ffmpeg_path, ffprobe_path) if value
    )
    media_tools = DependencyStatus(
        "ffmpeg",
        "FFmpeg / ffprobe",
        media_tools_ok,
        ffmpeg_version,
        media_tools_path,
        (
            "合併、轉檔、音訊切割與預覽可用"
            if media_tools_ok
            else "缺少 FFmpeg 或 ffprobe，合併、分段與音訊處理不可用"
        ),
    )

    runtime_status: tuple[bool, str, str, str] | None = None
    for name, args, minimum, _runtime_key, label in JAVASCRIPT_RUNTIME_SPECS:
        available, version, path = _executable_status(
            application_root,
            name=name,
            args=args,
            minimum=minimum,
            runner=runner,
        )
        if path and runtime_status is None:
            runtime_status = (available, version, path, label)
        if available:
            runtime_status = (True, version, path, label)
            break
    if runtime_status is None:
        runtime_status = (False, "", "", "")
    runtime_ok, runtime_version, runtime_path, runtime_label = runtime_status
    runtime = DependencyStatus(
        "javascript-runtime",
        "JavaScript runtime",
        runtime_ok,
        runtime_version,
        runtime_path,
        (
            f"{runtime_label} 可用，完整 YouTube 解析支援已具備"
            if runtime_ok
            else "需要 Deno 2.3+、Node.js 22+ 或 QuickJS；建議優先使用 Deno"
        ),
    )
    mega_get_path = find_executable(application_root, "mega-get") or ""
    mega_get = DependencyStatus(
        "mega-get",
        "MEGAcmd mega-get",
        bool(mega_get_path),
        "",
        mega_get_path,
        (
            "MEGA 公開檔案下載可用"
            if mega_get_path
            else "未偵測到官方 mega-get；MEGA 網址仍可辨識但無法下載"
        ),
    )
    whisper_path = find_executable(application_root, "whisper-cli") or ""
    whisper = DependencyStatus(
        "whisper-cli",
        "whisper-cli",
        bool(whisper_path),
        "",
        whisper_path,
        (
            "本機語音轉文字執行器可用"
            if whisper_path
            else "未偵測到 whisper-cli；Speech to Text 無法執行"
        ),
    )
    model_root = (
        data_root.resolve() / "models" / "speech-to-text"
        if data_root is not None
        else None
    )
    model_files: tuple[Path, ...] = ()
    if model_root is not None and model_root.is_dir() and not model_root.is_symlink():
        try:
            model_files = tuple(
                path
                for path in model_root.iterdir()
                if path.is_file() and not path.is_symlink() and path.stat().st_size > 0
            )[:64]
        except OSError:
            model_files = ()
    speech_model = DependencyStatus(
        "speech-model",
        "Speech model",
        bool(model_files),
        f"{len(model_files)} 個模型" if model_files else "",
        str(model_root) if model_root is not None else "",
        (
            "至少一個本機語音模型可用"
            if model_files
            else "尚未匯入本機語音模型；Speech to Text 無法開始轉錄"
        ),
    )
    return DependencyReport(
        (ytdlp, ejs, media_tools, runtime, mega_get, whisper, speech_model)
    )
