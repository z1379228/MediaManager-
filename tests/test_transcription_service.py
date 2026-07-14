from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Event

import pytest

from core.transcription import (
    SpeechModelManager,
    TranscriptionRequest,
    TranscriptionService,
    TranscriptionTask,
)


def imported_model(tmp_path: Path) -> tuple[SpeechModelManager, str]:
    manager = SpeechModelManager(tmp_path / "models")
    source = tmp_path / "model.bin"
    source.write_bytes(b"test-model")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manager.import_model(source, "tiny-test", digest)
    return manager, digest


def test_model_import_requires_explicit_matching_sha256(tmp_path: Path) -> None:
    manager = SpeechModelManager(tmp_path / "models")
    source = tmp_path / "model.bin"
    source.write_bytes(b"model")
    with pytest.raises(ValueError, match="mismatch"):
        manager.import_model(source, "tiny", "0" * 64)
    assert manager.list_models() == ()

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    model = manager.import_model(source, "tiny", digest)
    assert model.path.read_bytes() == b"model"
    model.path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="metadata|mismatch"):
        manager.get("tiny")


def test_model_remove_is_explicit(tmp_path: Path) -> None:
    manager, _ = imported_model(tmp_path)
    manager.remove("tiny-test")
    assert manager.list_models() == ()
    with pytest.raises(KeyError):
        manager.get("tiny-test")


def test_preview_estimates_ram_and_refuses_existing_outputs(tmp_path: Path) -> None:
    manager, _ = imported_model(tmp_path)
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    service = TranscriptionService(None, manager, tmp_path / "temp")
    request = TranscriptionRequest(source, "tiny-test", tmp_path, ("txt", "srt"))
    plan = service.preview(request)
    assert plan.estimated_ram_bytes >= 512 * 1024**2
    assert plan.outputs == (tmp_path / "speech.txt", tmp_path / "speech.srt")
    (tmp_path / "speech.txt").write_text("exists", encoding="utf-8")
    with pytest.raises(FileExistsError):
        service.preview(request)


def test_submit_requires_adapter_but_enabling_does_not_download_anything(
    tmp_path: Path,
) -> None:
    manager, _ = imported_model(tmp_path)
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    service = TranscriptionService(None, manager, tmp_path / "temp")
    service.set_enabled(True)
    with pytest.raises(RuntimeError, match="whisper-cli"):
        service.submit(TranscriptionRequest(source, "tiny-test", tmp_path))


def test_adapter_outputs_commit_and_cancel_cleanup(
    tmp_path: Path, monkeypatch
) -> None:
    manager, _ = imported_model(tmp_path)
    adapter = tmp_path / "whisper-cli.exe"
    adapter.write_bytes(b"adapter")
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    service = TranscriptionService(adapter, manager, tmp_path / "temp")
    request = TranscriptionRequest(source, "tiny-test", tmp_path, ("txt", "vtt"))
    plan = service.preview(request)
    task = TranscriptionTask("success", plan.request)

    def fake_success(command, _cancel_event):
        prefix = Path(command[command.index("-of") + 1])
        prefix.with_suffix(".txt").write_text("text", encoding="utf-8")
        prefix.with_suffix(".vtt").write_text("WEBVTT", encoding="utf-8")
        return 0

    monkeypatch.setattr(service, "_run", fake_success)
    assert service._execute(task, plan) == plan.outputs
    assert (tmp_path / "speech.txt").read_text(encoding="utf-8") == "text"
    assert not (tmp_path / "temp" / "success").exists()

    other = tmp_path / "other.wav"
    other.write_bytes(b"audio")
    cancel_plan = service.preview(
        TranscriptionRequest(other, "tiny-test", tmp_path, ("txt",))
    )
    cancel_task = TranscriptionTask("cancel", cancel_plan.request)

    def fake_cancel(command, cancel_event: Event):
        prefix = Path(command[command.index("-of") + 1])
        prefix.with_suffix(".txt").write_text("partial", encoding="utf-8")
        cancel_event.set()
        return 1

    monkeypatch.setattr(service, "_run", fake_cancel)
    with pytest.raises(RuntimeError, match="cancelled"):
        service._execute(cancel_task, cancel_plan)
    assert not (tmp_path / "other.txt").exists()
    assert not (tmp_path / "temp" / "cancel").exists()


def test_no_model_is_bundled() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "speech-to-text"
    assert {path.name for path in root.iterdir()} == {"adapter.json", "feature.json"}
