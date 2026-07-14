"""Local whisper.cpp adapter with explicit, hash-verified model imports."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import Event, RLock, Thread
import time
import uuid

from core.transcription.models import (
    TranscriptionPlan,
    TranscriptionRequest,
    TranscriptionState,
    TranscriptionTask,
)
from core.storage.atomic import commit_file_without_overwrite

MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_MODEL_BYTES = 8 * 1024**3
FORMATS = frozenset({"txt", "srt", "vtt"})


@dataclass(frozen=True, slots=True)
class SpeechModel:
    model_id: str
    path: Path
    sha256: str
    size: int


class SpeechModelManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest = self.root / "models.json"
        self._lock = RLock()

    def import_model(self, source: Path, model_id: str, expected_sha256: str) -> SpeechModel:
        model_id = model_id.strip().casefold()
        digest = expected_sha256.strip().casefold()
        source = source.expanduser().resolve()
        if not MODEL_ID.fullmatch(model_id):
            raise ValueError("model id must use lowercase letters, numbers, dot, dash or underscore")
        if not SHA256.fullmatch(digest):
            raise ValueError("model SHA-256 must contain 64 hexadecimal characters")
        if source.is_symlink() or not source.is_file():
            raise ValueError("model source must be a regular file")
        size = source.stat().st_size
        if not 1 <= size <= MAX_MODEL_BYTES:
            raise ValueError("model file size is outside the allowed range")
        actual = self._hash(source)
        if actual != digest:
            raise ValueError("model SHA-256 mismatch")
        target = self.root / f"{model_id}.bin"
        with self._lock:
            if target.exists():
                existing = self.get(model_id)
                if existing.sha256 == digest:
                    return existing
                raise FileExistsError(target)
            temporary = self.root / f".{model_id}.{uuid.uuid4().hex}.tmp"
            try:
                shutil.copyfile(source, temporary)
                if self._hash(temporary) != digest:
                    raise ValueError("copied model SHA-256 mismatch")
                os.replace(temporary, target)
                document = self._document()
                document[model_id] = {"sha256": digest, "size": size}
                self._write(document)
            except Exception:
                temporary.unlink(missing_ok=True)
                if target.exists() and model_id not in self._document():
                    target.unlink(missing_ok=True)
                raise
        return SpeechModel(model_id, target, digest, size)

    def list_models(self) -> tuple[SpeechModel, ...]:
        with self._lock:
            document = self._document()
        models = []
        for model_id, metadata in sorted(document.items()):
            try:
                model = self.get(model_id, verify_hash=False)
            except (KeyError, OSError, ValueError):
                continue
            if model.sha256 == metadata.get("sha256"):
                models.append(model)
        return tuple(models)

    def get(self, model_id: str, *, verify_hash: bool = True) -> SpeechModel:
        document = self._document()
        metadata = document.get(model_id)
        path = self.root / f"{model_id}.bin"
        if not isinstance(metadata, dict) or path.is_symlink() or not path.is_file():
            raise KeyError(model_id)
        digest = str(metadata.get("sha256", ""))
        size = int(metadata.get("size", -1))
        if not SHA256.fullmatch(digest) or size != path.stat().st_size:
            raise ValueError("model metadata is invalid")
        if verify_hash and self._hash(path) != digest:
            raise ValueError("installed model SHA-256 mismatch")
        return SpeechModel(model_id, path, digest, size)

    def remove(self, model_id: str) -> None:
        with self._lock:
            document = self._document()
            if model_id not in document:
                raise KeyError(model_id)
            path = self.root / f"{model_id}.bin"
            if path.is_symlink():
                raise ValueError("refusing to remove a model symlink")
            path.unlink(missing_ok=True)
            document.pop(model_id)
            self._write(document)

    def _document(self) -> dict[str, dict[str, object]]:
        if not self.manifest.is_file():
            return {}
        try:
            document = json.loads(self.manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        models = document.get("models") if isinstance(document, dict) else None
        return dict(models) if isinstance(models, dict) else {}

    def _write(self, models: dict[str, dict[str, object]]) -> None:
        temporary = self.manifest.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"schema_version": 1, "models": models}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.manifest)

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


class TranscriptionService:
    provider_id = "speech-to-text"
    display_name = "Speech to Text"
    available = True

    def __init__(self, adapter: Path | str | None, models: SpeechModelManager, temp_root: Path) -> None:
        self.adapter = Path(adapter).resolve() if adapter is not None else None
        self.models = models
        self.temp_root = temp_root.resolve()
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self._enabled = False
        self._closed = False
        self._lock = RLock()
        self._tasks: dict[str, TranscriptionTask] = {}
        self._queue: list[str] = []
        self._worker: Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def ready(self) -> bool:
        return self.adapter is not None and self.adapter.is_file() and bool(self.models.list_models())

    def set_enabled(self, enabled: bool) -> int:
        with self._lock:
            self._enabled = enabled
        return 0 if enabled else self.cancel_all()

    def preview(self, request: TranscriptionRequest) -> TranscriptionPlan:
        if request.source.is_symlink() or not request.source.is_file():
            raise ValueError("transcription source must be a regular file")
        source = request.source.resolve()
        output_dir = request.output_dir.resolve()
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise ValueError("transcription output folder is invalid")
        formats = tuple(dict.fromkeys(value.casefold() for value in request.formats))
        if not formats or not set(formats).issubset(FORMATS):
            raise ValueError("transcription output formats are invalid")
        language = request.language.strip().casefold()
        if language != "auto" and (not language.isalpha() or len(language) > 12):
            raise ValueError("transcription language is invalid")
        model = self.models.get(request.model_id)
        outputs = tuple(output_dir / f"{source.stem}.{value}" for value in formats)
        if any(path.exists() for path in outputs):
            raise FileExistsError("a transcription output already exists")
        normalized = replace(
            request,
            source=source,
            output_dir=output_dir,
            formats=formats,
            language=language,
        )
        return TranscriptionPlan(
            normalized,
            outputs,
            model.size,
            max(512 * 1024**2, model.size * 2),
        )

    def submit(self, request: TranscriptionRequest) -> str:
        if not self.is_enabled:
            raise RuntimeError("Speech to Text MOD is disabled")
        if self.adapter is None or not self.adapter.is_file():
            raise RuntimeError("whisper.cpp whisper-cli is not installed")
        plan = self.preview(request)
        task_id = uuid.uuid4().hex
        with self._lock:
            task = TranscriptionTask(task_id, plan.request)
            self._tasks[task_id] = task
            self._queue.append(task_id)
            if self._worker is None or not self._worker.is_alive():
                self._worker = Thread(target=self._work, name="speech-to-text", daemon=True)
                self._worker.start()
        return task_id

    def snapshots(self) -> tuple[TranscriptionTask, ...]:
        with self._lock:
            return tuple(replace(task, cancel_event=Event()) for task in self._tasks.values())

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.state in {TranscriptionState.COMPLETED, TranscriptionState.FAILED, TranscriptionState.CANCELLED}:
                return False
            task.cancel_event.set()
            if task.state == TranscriptionState.QUEUED:
                task.state = TranscriptionState.CANCELLED
                if task_id in self._queue:
                    self._queue.remove(task_id)
            process = self._process if task.state == TranscriptionState.RUNNING else None
        if process is not None:
            process.terminate()
        return True

    def cancel_all(self) -> int:
        return sum(self.cancel(task.task_id) for task in self.snapshots())

    def close(self) -> None:
        self._closed = True
        self.cancel_all()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=3)

    def _work(self) -> None:
        while True:
            with self._lock:
                if not self._queue or self._closed:
                    return
                task = self._tasks[self._queue.pop(0)]
                task.state = TranscriptionState.RUNNING
            try:
                outputs = self._execute(task, self.preview(task.request))
            except Exception as error:
                task.state = TranscriptionState.CANCELLED if task.cancel_event.is_set() else TranscriptionState.FAILED
                task.error = "" if task.cancel_event.is_set() else str(error)
            else:
                task.state = TranscriptionState.COMPLETED
                task.outputs = tuple(str(path) for path in outputs)

    def _execute(self, task: TranscriptionTask, plan: TranscriptionPlan) -> tuple[Path, ...]:
        model = self.models.get(plan.request.model_id)
        job_root = self.temp_root / task.task_id
        prefix = job_root / plan.request.source.stem
        job_root.mkdir(parents=True, exist_ok=False)
        try:
            command = [
                str(self.adapter), "-m", str(model.path), "-f", str(plan.request.source),
                "-of", str(prefix),
            ]
            if plan.request.language != "auto":
                command.extend(("-l", plan.request.language))
            command.extend(f"-o{value}" for value in plan.request.formats)
            return_code = self._run(tuple(command), task.cancel_event)
            if task.cancel_event.is_set():
                raise RuntimeError("transcription cancelled")
            if return_code != 0:
                raise RuntimeError(f"whisper.cpp exited with code {return_code}")
            staged = tuple(prefix.with_suffix(f".{value}") for value in plan.request.formats)
            if not all(path.is_file() for path in staged):
                raise RuntimeError("whisper.cpp did not create all requested outputs")
            committed = []
            try:
                for source, target in zip(staged, plan.outputs, strict=True):
                    commit_file_without_overwrite(source, target)
                    committed.append(target)
            except Exception:
                for target in committed:
                    target.unlink(missing_ok=True)
                raise
            return tuple(committed)
        finally:
            shutil.rmtree(job_root, ignore_errors=True)

    def _run(self, command: tuple[str, ...], cancel_event: Event) -> int:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
