from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

from contracts.provider_failure_v1 import ProviderFailureCode
from core.downloads import subprocess_provider as subprocess_provider_module
from core.downloads.errors import DownloadCancelled, ProviderFailure
from core.downloads.models import DownloadRequest
from core.downloads.subprocess_provider import (
    ProviderProtocolError,
    SubprocessDownloadProvider,
)


def make_provider(tmp_path: Path, source: str, entry="provider.py") -> Path:
    root = tmp_path / "mod" / "test"
    root.mkdir(parents=True)
    (root / "provider.py").write_text(source, encoding="utf-8")
    (root / "provider.json").write_text(
        json.dumps(
            {
                "provider_id": "test",
                "display_name": "Test",
                "entry_point": entry,
                "url_hosts": ["example.com"],
                "permissions": [
                    "network.youtube",
                    "storage.downloads.write",
                    "storage.temp.write",
                    "process.ffmpeg",
                ],
            }
        ),
        encoding="utf-8",
    )
    return root


def test_rejects_provider_entry_path_escape(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "", "../outside.py")
    with pytest.raises(ProviderProtocolError, match="unsafe"):
        SubprocessDownloadProvider(root, application_root=tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="official Windows MEGAcmd uses batch clients")
def test_mega_provider_accepts_only_its_official_named_batch_client(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "mega"
    batch = tmp_path / "mega-get.bat"
    batch.write_text("@echo off\n", encoding="utf-8")

    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        external_tools={"mega-get": str(batch)},
    )

    assert provider.external_tools == {"mega-get": str(batch.resolve())}


@pytest.mark.skipif(os.name != "nt", reason="official Windows MEGAcmd uses batch clients")
def test_mega_provider_rejects_wrong_batch_client_name(tmp_path: Path) -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "mega"
    batch = tmp_path / "untrusted.bat"
    batch.write_text("@echo off\n", encoding="utf-8")

    with pytest.raises(ProviderProtocolError, match="executable is invalid"):
        SubprocessDownloadProvider(
            root,
            application_root=tmp_path,
            external_tools={"mega-get": str(batch)},
        )


def test_rejects_malformed_provider_output(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "print('not-json', flush=True)")
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    with pytest.raises(ProviderProtocolError, match="invalid JSON"):
        provider.analyze("https://example.com/video")


def test_provider_analyze_timeout_terminates_process(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "import time; time.sleep(10)")
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=0.1
    )
    with pytest.raises(TimeoutError):
        provider.analyze("https://example.com/video")


def test_provider_drains_large_stderr_before_result(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "sys.stderr.write('x' * (1024 * 1024))\n"
        "sys.stderr.flush()\n"
        "print(json.dumps({'type':'result','value':{}}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    assert provider.analyze("https://example.com/video") == {}


def test_provider_bounds_stderr_in_protocol_error(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "sys.stderr.write('x' * (1024 * 1024))\n"
        "sys.stderr.flush()\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderProtocolError) as captured:
        provider.analyze("https://example.com/video")

    assert len(str(captured.value)) < 66_000
    assert str(captured.value).endswith("[provider stderr truncated]")


def test_provider_redacts_stderr_before_exposing_protocol_error(tmp_path: Path) -> None:
    diagnostic = (
        "Authorization: Bearer provider-secret-value\n"
        "Cookie: session=provider-cookie-value\n"
        r"C:\Users\Alice\Private\media.mp4"
    )
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        f"sys.stderr.write({diagnostic!r})\n"
        "sys.stderr.flush()\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderProtocolError) as captured:
        provider.analyze("https://example.com/video")

    detail = str(captured.value)
    assert "[REDACTED]" in detail
    assert "provider-secret-value" not in detail
    assert "provider-cookie-value" not in detail
    assert "Alice" not in detail
    assert "Private" not in detail
    assert "media.mp4" not in detail


def test_provider_redacts_structured_failure_without_changing_classification(
    tmp_path: Path,
) -> None:
    diagnostic = (
        "Authorization: Bearer provider-secret-value\n"
        "Cookie: session=provider-cookie-value\n"
        r"C:\Users\Alice\Private\media.mp4"
        "\nhttps://user:password@example.test/video"
    )
    failure_payload = {
        "code": "RATE_LIMITED",
        "message": diagnostic,
        "retryable": True,
        "details": {"retry_after_seconds": 30},
    }
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        f"print(json.dumps({{'type': 'error', 'error': {failure_payload!r}}}), "
        "flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderFailure) as captured:
        provider.analyze("https://example.com/video")

    failure = captured.value.failure
    assert failure.code is ProviderFailureCode.RATE_LIMITED
    assert failure.retryable is True
    for secret in (
        "provider-secret-value",
        "provider-cookie-value",
        "Alice",
        "Private",
        "media.mp4",
        "user",
        "password",
    ):
        assert secret not in failure.message
        assert secret not in str(captured.value)


def test_provider_redaction_keeps_failure_valid_when_message_becomes_empty(
    tmp_path: Path,
) -> None:
    failure_payload = {
        "code": "TEMPORARY",
        "message": "\u202e",
        "retryable": True,
    }
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        f"print(json.dumps({{'type': 'error', 'error': {failure_payload!r}}}), "
        "flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderFailure) as captured:
        provider.analyze("https://example.com/video")

    failure = captured.value.failure
    assert failure.code is ProviderFailureCode.TEMPORARY
    assert failure.message == "provider failed"
    assert failure.retryable is True


def test_provider_no_result_error_exposes_only_bounded_exit_metadata(
    tmp_path: Path,
) -> None:
    source = (
        "import json, os, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "os._exit(23)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderProtocolError) as captured:
        provider.analyze("https://example.com/video?token=request-secret")

    error = captured.value
    assert error.phase == "stdout_eof"
    assert error.exit_code == 23
    assert error.stdout_reader_complete is True
    assert "request-secret" not in str(error)


def test_provider_drains_stderr_after_stdout_eof(tmp_path: Path) -> None:
    source = (
        "import json, sys, time\n"
        "json.loads(sys.stdin.readline())\n"
        "sys.stdout.close()\n"
        # Remain within the public operation timeout while exceeding the former
        # private one-second stderr drain cap that made this load-dependent.
        "time.sleep(1.25)\n"
        "sys.stderr.write('late provider error')\n"
        "sys.stderr.flush()\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderProtocolError, match="late provider error"):
        provider.analyze("https://example.com/video")


def test_provider_accepts_result_enqueued_after_process_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "print(json.dumps({'type':'result','value':{}}), flush=True)\n"
    )
    original_put = subprocess_provider_module.queue.Queue.put

    def delayed_put(self, item, block=True, timeout=None):
        if isinstance(item, str):
            # Keep the result behind process exit without consuming most of the
            # public three-second operation budget on a loaded Windows runner.
            time.sleep(0.25)
        return original_put(self, item, block=block, timeout=timeout)

    monkeypatch.setattr(subprocess_provider_module.queue.Queue, "put", delayed_put)
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    assert provider.analyze("https://example.com/video") == {}


def test_provider_rejects_oversized_stdout_message(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "sys.stdout.write('x' * (1024 * 1024 + 1))\n"
        "sys.stdout.flush()\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(
        root, application_root=tmp_path, analyze_timeout=3
    )

    with pytest.raises(ProviderProtocolError, match="exceeds size limit"):
        provider.analyze("https://example.com/video")


def test_cancelled_download_terminates_provider(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "import time; time.sleep(10)")
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    cancelled = threading.Event()
    cancelled.set()
    request = DownloadRequest("https://example.com/video", tmp_path / "out")
    with pytest.raises(DownloadCancelled):
        provider.download(request, lambda _: None, cancelled)


def test_download_idle_timeout_terminates_silent_provider(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "import time; time.sleep(10)")
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        download_timeout=10,
        idle_timeout=0.1,
    )
    request = DownloadRequest("https://example.com/video", tmp_path / "out")
    with pytest.raises(TimeoutError, match="stopped reporting"):
        provider.download(request, lambda _: None, threading.Event())


def test_download_accepts_nonempty_file_inside_output_directory(
    tmp_path: Path,
) -> None:
    source = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "path=Path(raw['output_dir'])/'result.mp4'\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_bytes(b'media')\n"
        "print(json.dumps({'type':'result','value':str(path)}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    request = DownloadRequest("https://example.com/video", tmp_path / "out")

    result = provider.download(request, lambda _: None, threading.Event())

    assert Path(result).read_bytes() == b"media"


def test_mega_download_accepts_only_explicit_folder_result(
    tmp_path: Path, monkeypatch
) -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "mega"
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    output = tmp_path / "out"
    folder = output / "shared-folder"
    folder.mkdir(parents=True)
    (folder / "media.bin").write_bytes(b"data")
    monkeypatch.setattr(provider, "_execute", lambda *_args, **_kwargs: str(folder))
    request = DownloadRequest(
        "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop",
        output,
        source_category="mega-folder",
    )

    result = provider.download(request, lambda _: None, threading.Event())

    assert Path(result) == folder.resolve()


def test_mega_folder_result_requires_folder_category(
    tmp_path: Path, monkeypatch
) -> None:
    root = Path(__file__).parents[1] / "mod" / "builtin" / "mega"
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    output = tmp_path / "out"
    folder = output / "shared-folder"
    folder.mkdir(parents=True)
    monkeypatch.setattr(provider, "_execute", lambda *_args, **_kwargs: str(folder))
    request = DownloadRequest(
        "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop", output
    )

    with pytest.raises(ProviderProtocolError, match="missing or outside"):
        provider.download(request, lambda _: None, threading.Event())


def test_download_forwards_media_and_bounded_provider_options(
    tmp_path: Path,
) -> None:
    source = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "path=Path(raw['output_dir'])/'result.mp4'\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_text(json.dumps({"
        "'timed_comment_mode':raw['timed_comment_mode'],"
        "'container_preset':raw['container_preset'],"
        "'provider_options':raw['provider_options']}), encoding='utf-8')\n"
        "print(json.dumps({'type':'result','value':str(path)}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    request = DownloadRequest(
        "https://example.com/video",
        tmp_path / "out",
        timed_comment_mode="ass",
        container_preset="mkv",
        provider_options=(("download_connections", "4"),),
    )

    result = provider.download(request, lambda _: None, threading.Event())

    assert json.loads(Path(result).read_text(encoding="utf-8")) == {
        "timed_comment_mode": "ass",
        "container_preset": "mkv",
        "provider_options": {"download_connections": "4"},
    }


@pytest.mark.parametrize(
    ("result_source", "create_result"),
    [
        ("str(Path(raw['output_dir'])/'missing.mp4')", False),
        ("str(Path(raw['output_dir']).parent/'outside.mp4')", True),
    ],
)
def test_download_rejects_missing_or_outside_result(
    tmp_path: Path, result_source: str, create_result: bool
) -> None:
    create_source = "Path(path).write_bytes(b'media')\n" if create_result else ""
    source = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw=json.loads(sys.stdin.readline())\n"
        f"path={result_source}\n"
        f"{create_source}"
        "print(json.dumps({'type':'result','value':path}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    request = DownloadRequest("https://example.com/video", tmp_path / "out")

    with pytest.raises(ProviderProtocolError, match="missing or outside"):
        provider.download(request, lambda _: None, threading.Event())


def test_rejects_unapproved_provider_permission(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "")
    manifest = json.loads((root / "provider.json").read_text(encoding="utf-8"))
    manifest["permissions"] = ["process.unrestricted"]
    (root / "provider.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ProviderProtocolError, match="permissions"):
        SubprocessDownloadProvider(root, application_root=tmp_path)


def test_rejects_malformed_provider_manifest_identity(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "")
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entry_point"] = ["provider.py"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ProviderProtocolError, match="identity"):
        SubprocessDownloadProvider(root, application_root=tmp_path)


def test_search_capability_is_loaded_from_provider_manifest(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "")
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["search_capability"] = {
        "provider_id": "test",
        "sites": ["example"],
        "content_types": ["all", "video"],
        "max_page_size": 15,
        "pagination": "none",
        "audio_preview": False,
        "video_preview": True,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    assert provider.search_capability is not None
    assert provider.search_capability.sites == ("example",)
    assert provider.search_capability.max_page_size == 15


def test_search_capability_provider_must_match_manifest(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "")
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["search_capability"] = {
        "provider_id": "other",
        "sites": ["example"],
        "content_types": ["all"],
        "max_page_size": 10,
        "pagination": "none",
        "audio_preview": False,
        "video_preview": False,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ProviderProtocolError, match="provider mismatch"):
        SubprocessDownloadProvider(root, application_root=tmp_path)


def test_operation_rejects_missing_required_permission(tmp_path: Path) -> None:
    root = make_provider(tmp_path, "")
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"] = ["storage.downloads.write"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    with pytest.raises(ProviderProtocolError, match="network.youtube"):
        provider.download(
            DownloadRequest("https://example.com/video", tmp_path / "out"),
            lambda _: None,
            threading.Event(),
        )


def test_generic_provider_uses_separate_network_permission(tmp_path: Path) -> None:
    root = make_provider(
        tmp_path,
        "import json, sys; json.loads(sys.stdin.readline()); "
        'print(json.dumps({"type":"result","value":{}}), flush=True)',
    )
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "provider_id": "generic-ytdlp",
            "permissions": ["network.generic"],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    assert provider.analyze("https://example.com/video") == {}


def test_expected_hash_is_rechecked_before_each_execution(tmp_path: Path) -> None:
    import hashlib

    root = make_provider(
        tmp_path,
        "import json, sys; json.loads(sys.stdin.readline()); "
        'print(json.dumps({"type":"result","value":{}}), flush=True)',
    )
    digest = hashlib.sha256((root / "provider.py").read_bytes()).hexdigest()
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        expected_hashes={"provider.py": digest},
    )
    (root / "provider.py").write_text("print('tampered')", encoding="utf-8")
    with pytest.raises(ProviderProtocolError, match="integrity mismatch"):
        provider.analyze("https://example.com/video")


def test_minimal_environment_does_not_forward_secrets(monkeypatch) -> None:
    monkeypatch.setenv("MEDIA_MANAGER_TEST_SECRET", "do-not-forward")
    environment = SubprocessDownloadProvider._minimal_environment()
    assert "MEDIA_MANAGER_TEST_SECRET" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_minimal_environment_isolates_provider_home_and_cache(tmp_path: Path) -> None:
    runtime_home = tmp_path / "provider-runtime" / "generic-ytdlp"

    environment = SubprocessDownloadProvider._minimal_environment(runtime_home)

    assert environment["HOME"] == str(runtime_home.resolve())
    assert environment["USERPROFILE"] == str(runtime_home.resolve())
    assert environment["XDG_CACHE_HOME"] == str((runtime_home / "cache").resolve())
    assert runtime_home.is_dir()
    assert (runtime_home / "cache").is_dir()


def test_frozen_provider_command_passes_verified_builtin_root(
    tmp_path: Path, monkeypatch
) -> None:
    root = make_provider(tmp_path, "print('unused')")
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "MediaManager.exe"))

    assert provider._command() == [
        str(tmp_path / "MediaManager.exe"),
        "--provider-host",
        str((root / "provider.py").resolve()),
        "--provider-root",
        str(root.parent.resolve()),
    ]


def test_youtube_provider_receives_validated_javascript_runtime(
    tmp_path: Path,
) -> None:
    source = (
        "import json, sys\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "print(json.dumps({'type':'result','value':raw['js_runtime']}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "provider_id": "youtube",
            "url_hosts": ["youtube.com"],
            "permissions": ["network.youtube", "process.javascript"],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    runtime = tmp_path / "deno.exe"
    runtime.write_bytes(b"runtime")
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        js_runtime=("deno", str(runtime)),
    )

    result = provider.analyze("https://youtube.com/watch?v=example")

    assert result == {"name": "deno", "path": str(runtime.resolve())}


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows Job Object test")
def test_cancel_kills_provider_child_process_tree(tmp_path: Path) -> None:
    import ctypes
    import queue
    import time
    from ctypes import wintypes

    source = (
        "import json, subprocess, sys, time\n"
        "json.loads(sys.stdin.readline())\n"
        "child=subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])\n"
        "print(json.dumps({'type':'progress','title':str(child.pid)}), flush=True)\n"
        "time.sleep(30)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    cancelled = threading.Event()
    child_pids: queue.Queue[int] = queue.Queue()
    result: list[BaseException] = []

    def run() -> None:
        try:
            provider.download(
                DownloadRequest("https://example.com/video", tmp_path / "out"),
                lambda status: child_pids.put(int(status["info_dict"]["title"])),
                cancelled,
            )
        except BaseException as error:
            result.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    child_pid = child_pids.get(timeout=5)
    cancelled.set()
    thread.join(timeout=5)
    assert result and isinstance(result[0], DownloadCancelled)

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        handle = kernel32.OpenProcess(0x1000, False, child_pid)
        if not handle:
            break
        kernel32.CloseHandle(handle)
        time.sleep(0.05)
    else:
        pytest.fail("provider child process survived Job Object close")


def test_subprocess_search_validates_discovery_results(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "assert raw['content_type'] == 'music'\n"
        "item={'video_id':'abc','url':'https://www.youtube.com/watch?v=abc',"
        "'title':'Example','artist':'Artist','duration':60,'language':'',"
        "'category':'video','thumbnail_url':''}\n"
        "print(json.dumps({'type':'result','value':[item]}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)
    assert provider.search("example", limit=1, content_type="music")[0].video_id == "abc"


def test_subprocess_analysis_rejects_invalid_media_formats(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "value={'formats':[{'format_id':'x'}]}\n"
        "print(json.dumps({'type':'result','value':value}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    with pytest.raises(ProviderProtocolError, match="media formats"):
        provider.analyze("https://example.com/video")


def test_subprocess_playlist_validates_bounded_entries(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "assert raw['operation'] == 'playlist' and raw['limit'] == 2\n"
        "item={'entry_id':'abc','url':'https://example.com/watch?v=abc',"
        "'title':'Example','artist':'Artist','duration':60,'position':1,"
        "'available':True,'unavailable_reason':''}\n"
        "print(json.dumps({'type':'result','value':[item]}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    result = provider.playlist("https://example.com/list", limit=2)

    assert result[0].entry_id == "abc"


def test_subprocess_playlist_rejects_duplicate_positions(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "json.loads(sys.stdin.readline())\n"
        "base={'url':'https://example.com/watch','title':'Example','artist':'',"
        "'duration':None,'position':1,'available':True,'unavailable_reason':''}\n"
        "items=[dict(base,entry_id='one'),dict(base,entry_id='two')]\n"
        "print(json.dumps({'type':'result','value':items}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    provider = SubprocessDownloadProvider(root, application_root=tmp_path)

    with pytest.raises(ProviderProtocolError, match="positions"):
        provider.playlist("https://example.com/list")


def test_audio_preview_is_confined_to_session_and_cleaned(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "assert raw['preview_length'] == 30\n"
        "path=Path(raw['output_dir'])/'preview.mp3'\n"
        "path.write_bytes(b'preview')\n"
        "print(json.dumps({'type':'result','value':str(path)}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "provider_id": "youtube",
            "url_hosts": ["youtube.com"],
            "permissions": [
                "network.youtube",
                "storage.temp.write",
                "process.ffmpeg",
            ],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"ffmpeg")
    preview_root = tmp_path / "previews"
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        ffmpeg_location=str(ffmpeg),
        preview_root=preview_root,
    )
    path = provider.prepare_audio_preview(
        "https://youtube.com/watch?v=example",
        duration=60,
        preview_length=30,
    )
    assert path.read_bytes() == b"preview"
    assert path.is_relative_to(preview_root)
    assert provider.cleanup_audio_preview(path)
    assert not path.parent.exists()
    assert not provider.cleanup_audio_preview(tmp_path / "outside.mp3")
    with pytest.raises(ProviderProtocolError, match="configuration"):
        provider.prepare_audio_preview(
            "https://youtube.com/watch?v=example",
            duration=60,
            preview_length=121,
        )
    provider.close()


def test_audio_preview_cleanup_returns_false_when_file_is_locked(
    tmp_path: Path, monkeypatch
) -> None:
    preview_root = tmp_path / "previews"
    session = preview_root / ("a" * 32)
    session.mkdir(parents=True)
    path = session / "preview.mp3"
    path.write_bytes(b"preview")
    root = make_provider(tmp_path, "")
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        preview_root=preview_root,
    )

    def locked(_path) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr("core.downloads.subprocess_provider.shutil.rmtree", locked)

    assert not provider.cleanup_audio_preview(path)
    assert path.is_file()
    provider.close()


def test_video_preview_is_confined_to_session_and_cleaned(tmp_path: Path) -> None:
    source = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw=json.loads(sys.stdin.readline())\n"
        "assert raw['operation'] == 'prepare_video_preview'\n"
        "assert raw['preview_length'] == 60\n"
        "path=Path(raw['output_dir'])/'preview.mp4'\n"
        "path.write_bytes(b'video-preview')\n"
        "print(json.dumps({'type':'result','value':str(path)}), flush=True)\n"
    )
    root = make_provider(tmp_path, source)
    manifest_path = root / "provider.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "provider_id": "youtube-player",
            "url_hosts": ["youtube.com"],
            "permissions": [
                "network.youtube",
                "storage.temp.write",
                "process.ffmpeg",
            ],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"ffmpeg")
    preview_root = tmp_path / "video-previews"
    provider = SubprocessDownloadProvider(
        root,
        application_root=tmp_path,
        ffmpeg_location=str(ffmpeg),
        preview_root=preview_root,
    )
    path = provider.prepare_video_preview(
        "https://youtube.com/watch?v=example",
        duration=180,
    )
    assert path.read_bytes() == b"video-preview"
    assert path.is_relative_to(preview_root)
    assert provider.cleanup_video_preview(path)
    assert not path.parent.exists()
    provider.close()
