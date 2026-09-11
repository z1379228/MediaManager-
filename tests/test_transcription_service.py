from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Event
import time
from types import SimpleNamespace

import pytest

from core.transcription import (
    SpeechModelManager,
    TranscriptionCapabilities,
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


def test_cancelled_model_copy_leaves_no_partial_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = SpeechModelManager(tmp_path / "models")
    source = tmp_path / "model.bin"
    source.write_bytes(b"model")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    cancel = Event()
    cancel.set()
    monkeypatch.setattr(manager, "_hash", lambda *_args, **_kwargs: digest)

    with pytest.raises(InterruptedError, match="cancelled"):
        manager.import_model(
            source,
            "cancelled-model",
            digest,
            cancel_event=cancel,
        )

    assert manager.list_models() == ()
    assert not (manager.root / "cancelled-model.bin").exists()
    assert not tuple(manager.root.glob(".*.tmp"))


def test_vad_models_are_explicitly_classified_and_legacy_models_stay_speech(
    tmp_path: Path,
) -> None:
    manager, _ = imported_model(tmp_path)
    source = tmp_path / "vad.bin"
    source.write_bytes(b"vad-model")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    vad = manager.import_model(source, "silero-vad", digest, kind="vad")

    assert vad.kind == "vad"
    assert tuple(model.model_id for model in manager.list_models("speech")) == (
        "tiny-test",
    )
    assert tuple(model.model_id for model in manager.list_models("vad")) == (
        "silero-vad",
    )
    assert manager.get("tiny-test").kind == "speech"
    with pytest.raises(ValueError, match="kind"):
        manager.get("silero-vad", kind="speech")


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


def test_vad_preview_requires_explicit_vad_model(tmp_path: Path) -> None:
    manager, _ = imported_model(tmp_path)
    vad_source = tmp_path / "vad.bin"
    vad_source.write_bytes(b"vad-model")
    digest = hashlib.sha256(vad_source.read_bytes()).hexdigest()
    manager.import_model(vad_source, "silero-vad", digest, kind="vad")
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    service = TranscriptionService(None, manager, tmp_path / "temp")

    plan = service.preview(
        TranscriptionRequest(
            source,
            "tiny-test",
            tmp_path,
            vad_model_id="silero-vad",
        )
    )

    assert plan.request.vad_model_id == "silero-vad"
    with pytest.raises((KeyError, ValueError)):
        service.preview(
            TranscriptionRequest(
                source,
                "tiny-test",
                tmp_path,
                vad_model_id="tiny-test",
            )
        )


def test_adapter_capabilities_require_both_vad_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, _ = imported_model(tmp_path)
    adapter = tmp_path / "whisper-cli.exe"
    adapter.write_bytes(b"adapter")
    service = TranscriptionService(adapter, manager, tmp_path / "temp")
    monkeypatch.setattr(
        service,
        "_probe_adapter_help",
        lambda: ("usage: whisper-cli --vad --vad-model FILE", ""),
    )

    assert service.capabilities(refresh=True) == TranscriptionCapabilities(
        supports_vad=True,
        diagnostic="",
    )

    monkeypatch.setattr(
        service,
        "_probe_adapter_help",
        lambda: ("usage: whisper-cli --vad", ""),
    )
    assert not service.capabilities(refresh=True).supports_vad


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


def test_vad_execution_requires_capability_and_passes_verified_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, _ = imported_model(tmp_path)
    vad_source = tmp_path / "vad.bin"
    vad_source.write_bytes(b"vad-model")
    vad_digest = hashlib.sha256(vad_source.read_bytes()).hexdigest()
    vad = manager.import_model(
        vad_source,
        "silero-vad",
        vad_digest,
        kind="vad",
    )
    adapter = tmp_path / "whisper-cli.exe"
    adapter.write_bytes(b"adapter")
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    service = TranscriptionService(adapter, manager, tmp_path / "temp")
    request = TranscriptionRequest(
        source,
        "tiny-test",
        tmp_path,
        ("txt",),
        vad_model_id="silero-vad",
    )
    plan = service.preview(request)
    task = TranscriptionTask("vad", plan.request)
    monkeypatch.setattr(
        service,
        "capabilities",
        lambda **_kwargs: TranscriptionCapabilities(False, "unsupported"),
    )
    with pytest.raises(RuntimeError, match="VAD"):
        service._execute(task, plan)

    captured: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        service,
        "capabilities",
        lambda **_kwargs: TranscriptionCapabilities(True, ""),
    )

    def fake_run(command: tuple[str, ...], _cancel_event: Event) -> int:
        captured.append(command)
        prefix = Path(command[command.index("-of") + 1])
        prefix.with_suffix(".txt").write_text("text", encoding="utf-8")
        return 0

    monkeypatch.setattr(service, "_run", fake_run)
    assert service._execute(task, plan) == plan.outputs
    assert ("--vad", "--vad-model", str(vad.path)) == captured[0][
        captured[0].index("--vad") : captured[0].index("--vad") + 3
    ]


def test_vad_ui_is_opt_in_and_capability_probe_does_not_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    manager, _ = imported_model(tmp_path)
    vad_source = tmp_path / "vad.bin"
    vad_source.write_bytes(b"vad-model")
    vad_digest = hashlib.sha256(vad_source.read_bytes()).hexdigest()
    manager.import_model(vad_source, "silero-vad", vad_digest, kind="vad")
    adapter = tmp_path / "whisper-cli.exe"
    adapter.write_bytes(b"adapter")
    service = TranscriptionService(adapter, manager, tmp_path / "temp")
    started = Event()
    release = Event()

    def capabilities(**_kwargs: object) -> TranscriptionCapabilities:
        started.set()
        release.wait(timeout=2)
        return TranscriptionCapabilities(True, "")

    monkeypatch.setattr(service, "capabilities", capabilities)
    from trusted_ui.transcription_panel import create_transcription_panel

    app = QApplication.instance() or QApplication([])
    panel = create_transcription_panel(SimpleNamespace(transcription=service))
    try:
        assert not panel.vad_enabled.isChecked()
        assert not panel.vad_enabled.isEnabled()
        started_at = time.monotonic()
        panel.detect_vad.click()
        app.processEvents()

        assert started.wait(timeout=1)
        assert time.monotonic() - started_at < 0.5
        assert "正在背景偵測" in panel.vad_status.text()

        release.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not panel.vad_enabled.isEnabled():
            app.processEvents()
            time.sleep(0.01)

        assert panel.vad_enabled.isEnabled()
        assert panel.vad_models.currentData() == "silero-vad"
        assert not panel.vad_enabled.isChecked()
        assert "預設關閉" in panel.vad_status.text()
    finally:
        release.set()
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_model_import_hashing_and_copy_run_off_gui_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QPushButton

    manager, _ = imported_model(tmp_path)
    service = TranscriptionService(None, manager, tmp_path / "temp")
    source = tmp_path / "large-model.bin"
    source.write_bytes(b"model")
    started = Event()
    release = Event()

    def import_model(*_args: object, **_kwargs: object) -> None:
        started.set()
        release.wait(timeout=2)

    monkeypatch.setattr(service.models, "import_model", import_model)
    monkeypatch.setattr(QMessageBox, "information", lambda *_args: None)
    from trusted_ui.transcription_panel import create_transcription_panel

    app = QApplication.instance() or QApplication([])
    panel = create_transcription_panel(SimpleNamespace(transcription=service))
    inputs = {
        line.placeholderText(): line for line in panel.findChildren(QLineEdit)
    }
    buttons = {
        button.text(): button for button in panel.findChildren(QPushButton)
    }
    inputs["選擇本機 whisper.cpp GGML/GGUF 模型"].setText(str(source))
    inputs["模型 ID，例如 base-zh"].setText("large-model")
    inputs["確認來源公布的 64 位 SHA-256"].setText("0" * 64)
    try:
        started_at = time.monotonic()
        buttons["驗證並匯入"].click()
        app.processEvents()

        assert started.wait(timeout=1)
        assert time.monotonic() - started_at < 0.5
        assert not buttons["驗證並匯入"].isEnabled()

        release.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not buttons["驗證並匯入"].isEnabled():
            app.processEvents()
            time.sleep(0.01)
        assert buttons["驗證並匯入"].isEnabled()
    finally:
        release.set()
        panel.shutdown()
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_no_model_is_bundled() -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "speech-to-text"
    assert {path.name for path in root.iterdir()} == {"adapter.json", "feature.json"}
