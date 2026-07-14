"""Launch one isolated plugin host process per executable MOD."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from core.downloads.windows_job import ProviderJob


_MAX_HANDSHAKE_CHARS = 64 * 1024
_MAX_STDERR_CHARS = 64 * 1024


@dataclass(slots=True)
class PluginProcess:
    plugin_id: str
    process: subprocess.Popen[str]
    job: ProviderJob


class HostLauncher:
    def __init__(self, *, handshake_timeout: float = 5.0) -> None:
        self.handshake_timeout = max(0.1, handshake_timeout)

    @staticmethod
    def _command(
        plugin_id: str, plugin_root: Path, entry_point: str, nonce: str
    ) -> list[str]:
        arguments = [
            "--plugin-id",
            plugin_id,
            "--plugin-root",
            str(plugin_root),
            "--entry-point",
            entry_point,
            "--nonce",
            nonce,
        ]
        if getattr(sys, "frozen", False):
            return [sys.executable, "--plugin-host", *arguments]
        return [sys.executable, "-I", "-m", "plugin_host.main", *arguments]

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        allowed = ("PATH", "SYSTEMROOT", "TEMP", "TMP")
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        environment["PYTHONNOUSERSITE"] = "1"
        return environment

    def launch(
        self, plugin_id: str, plugin_root: Path, entry_point: str, nonce: str
    ) -> PluginProcess:
        root = plugin_root.resolve()
        entry = (root / entry_point).resolve()
        if (
            not entry.is_relative_to(root)
            or not entry.is_file()
            or entry.is_symlink()
        ):
            raise ValueError("plugin entry point escaped its root or is missing")
        job = ProviderJob()
        process = None
        try:
            process = subprocess.Popen(
                self._command(plugin_id, root, entry_point, nonce),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                cwd=Path(__file__).resolve().parents[2],
                env=self._minimal_environment(),
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )
            job.assign(int(getattr(process, "_handle", 0)))
        except Exception:
            if process is not None and process.poll() is None:
                process.terminate()
            job.close()
            raise
        plugin = PluginProcess(plugin_id, process, job)
        stderr_parts: list[str] = []
        stderr_size = 0
        stderr_lock = threading.Lock()

        def drain_stderr() -> None:
            nonlocal stderr_size
            assert process.stderr is not None
            try:
                while True:
                    chunk = process.stderr.read(4096)
                    if not chunk:
                        return
                    with stderr_lock:
                        remaining = _MAX_STDERR_CHARS - stderr_size
                        if remaining > 0:
                            retained = chunk[:remaining]
                            stderr_parts.append(retained)
                            stderr_size += len(retained)
            except (OSError, ValueError):
                return

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()
        handshake: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

        def read_handshake() -> None:
            try:
                assert process.stdout is not None
                handshake.put(process.stdout.readline(_MAX_HANDSHAKE_CHARS + 1))
            except BaseException as error:
                handshake.put(error)

        threading.Thread(target=read_handshake, daemon=True).start()
        try:
            raw = handshake.get(timeout=self.handshake_timeout)
        except queue.Empty as error:
            self.stop(plugin)
            raise TimeoutError("plugin host handshake timed out") from error
        if isinstance(raw, BaseException):
            self.stop(plugin)
            raise RuntimeError(f"plugin host handshake failed: {raw}") from raw
        if not raw:
            self.stop(plugin)
            stderr_thread.join(timeout=0.2)
            with stderr_lock:
                stderr_text = "".join(stderr_parts).strip()
            detail = f": {stderr_text}" if stderr_text else ""
            raise RuntimeError(f"plugin host rejected startup{detail}")
        if len(raw) > _MAX_HANDSHAKE_CHARS:
            self.stop(plugin)
            raise RuntimeError("plugin host handshake exceeded size limit")
        try:
            message = json.loads(raw)
        except ValueError as error:
            self.stop(plugin)
            raise RuntimeError("plugin host emitted an invalid handshake") from error
        expected = {
            "protocol_version": "1.0",
            "plugin_id": plugin_id,
            "runtime_nonce": nonce,
        }
        if message != expected or process.poll() is not None:
            with stderr_lock:
                stderr_text = "".join(stderr_parts).strip()
            self.stop(plugin)
            detail = f": {stderr_text}" if stderr_text else ""
            raise RuntimeError(f"plugin host rejected startup{detail}")
        return plugin

    @staticmethod
    def initialize(
        plugin: PluginProcess,
        *,
        capability_token: str,
        capabilities: tuple[str, ...],
        protocol_version: str,
    ) -> None:
        stream = plugin.process.stdin
        if stream is None or plugin.process.poll() is not None:
            raise RuntimeError("plugin host is not available for initialization")
        if not capability_token or protocol_version != "1.0":
            raise ValueError("plugin runtime initialization is invalid")
        stream.write(
            json.dumps(
                {
                    "type": "runtime.init",
                    "protocol_version": protocol_version,
                    "capability_token": capability_token,
                    "capabilities": list(capabilities),
                },
                separators=(",", ":"),
            )
            + "\n"
        )
        stream.flush()

    def stop(self, plugin: PluginProcess, timeout: float = 5.0) -> None:
        if plugin.process.poll() is None:
            plugin.process.terminate()
        plugin.job.close()
        if plugin.process.poll() is None:
            try:
                plugin.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                plugin.process.kill()
                plugin.process.wait(timeout=timeout)
        for stream in (
            plugin.process.stdin,
            plugin.process.stdout,
            plugin.process.stderr,
        ):
            if stream is not None:
                stream.close()
