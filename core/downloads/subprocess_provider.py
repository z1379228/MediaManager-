"""Core-side client for a download MOD running in a separate process."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, replace
import queue
import subprocess
import sys
import threading
import time
import shutil
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.downloads.models import DownloadRequest
from core.downloads.direct_http_policy import direct_http_url_candidate
from core.downloads.windows_job import ProviderJob
from contracts.discovery_v1 import DiscoveryItemV1
from contracts.history_v1 import HistoryEventV1, HistoryPreferencesV1
from contracts.media_analysis_v1 import parse_media_formats, parse_media_languages
from contracts.playlist_v1 import MAX_PLAYLIST_ENTRIES_V1, PlaylistEntryV1
from contracts.recovery_v1 import RecoveryCandidateV1, RecoveryPlanV1
from contracts.search_v2 import (
    SearchCapabilityV2,
    SearchContractV2Error,
    SearchPageV2,
    SearchQueryV2,
)
from contracts.similar_v1 import SimilarPlanV1, SimilarSelectionV1
from contracts.split_plan_v1 import SplitPlanV1
from core.downloads.errors import (
    DownloadCancelled,
    ProviderFailure,
    classify_provider_failure,
)
from core.logging.redaction import bounded_redacted_text


_MAX_PROVIDER_MESSAGE_CHARS = 1024 * 1024
_MAX_PROVIDER_STDERR_CHARS = 64 * 1024
_PROVIDER_MESSAGE_BACKLOG = 128


class ProviderProtocolError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        phase: str = "",
        exit_code: int | None = None,
        stdout_reader_complete: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.exit_code = exit_code
        self.stdout_reader_complete = stdout_reader_complete


class SubprocessDownloadProvider:
    def __init__(
        self,
        root: Path,
        *,
        application_root: Path,
        ffmpeg_location: str | None = None,
        js_runtime: tuple[str, str] | None = None,
        external_tools: dict[str, str] | None = None,
        analyze_timeout: float = 45.0,
        download_timeout: float = 900.0,
        idle_timeout: float = 90.0,
        expected_hashes: dict[str, str] | None = None,
        history_state_path: Path | None = None,
        analysis_root: Path | None = None,
        preview_root: Path | None = None,
        runtime_home: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self.application_root = application_root.resolve()
        self.ffmpeg_location = ffmpeg_location
        self.analyze_timeout = max(0.1, analyze_timeout)
        self.download_timeout = max(1.0, download_timeout)
        self.idle_timeout = max(0.1, idle_timeout)
        self.expected_hashes = dict(expected_hashes or {})
        self.history_state_path = (
            history_state_path.resolve() if history_state_path else None
        )
        self.analysis_root = analysis_root.resolve() if analysis_root else None
        self.preview_root = preview_root.resolve() if preview_root else None
        self.runtime_home = runtime_home.resolve() if runtime_home else None
        self._processes: set[subprocess.Popen[str]] = set()
        self._lock = threading.RLock()
        (
            self.provider_id,
            self.display_name,
            self.entry_point,
            self.hosts,
            self.permissions,
            self.search_capability,
        ) = self._load_manifest()
        self.js_runtime: tuple[str, str] | None = None
        if js_runtime is not None:
            name, raw_path = js_runtime
            runtime_path = Path(raw_path).resolve()
            if (
                name not in {"deno", "node", "quickjs"}
                or "process.javascript" not in self.permissions
                or not runtime_path.is_file()
            ):
                raise ProviderProtocolError(
                    "JavaScript runtime configuration is invalid"
                )
            self.js_runtime = (name, str(runtime_path))
        allowed_tool_names = {
            "mega": frozenset({"mega-get", "mega-speedlimit"}),
        }.get(self.provider_id, frozenset())
        raw_tools = dict(external_tools or {})
        if set(raw_tools) - allowed_tool_names:
            raise ProviderProtocolError("external tool configuration is not allowed")
        self.external_tools: dict[str, str] = {}
        for tool_name, raw_path in raw_tools.items():
            tool_path = Path(raw_path).resolve()
            expected_names = {tool_name.casefold(), f"{tool_name.casefold()}.exe"}
            if self.provider_id == "mega" and os.name == "nt":
                expected_names.add(f"{tool_name.casefold()}.bat")
            if (
                not tool_path.is_file()
                or tool_path.name.casefold() not in expected_names
            ):
                raise ProviderProtocolError("external tool executable is invalid")
            self.external_tools[tool_name] = str(tool_path)
        if self.external_tools and "process.megacmd" not in self.permissions:
            raise ProviderProtocolError("external tool permission is missing")
        self._verify_expected_files()

    def _load_manifest(
        self,
    ) -> tuple[
        str,
        str,
        Path,
        frozenset[str],
        tuple[str, ...],
        SearchCapabilityV2 | None,
    ]:
        try:
            raw = json.loads(
                (self.root / "provider.json").read_text(encoding="utf-8-sig")
            )
        except (OSError, ValueError) as error:
            raise ProviderProtocolError(
                f"cannot read provider manifest: {error}"
            ) from error
        required = {
            "provider_id",
            "display_name",
            "entry_point",
            "url_hosts",
            "permissions",
        }
        if (
            not isinstance(raw, dict)
            or not required <= set(raw)
            or set(raw) - required - {"search_capability"}
        ):
            raise ProviderProtocolError("provider manifest fields invalid")
        provider_id = raw["provider_id"]
        display_name = raw["display_name"]
        entry_name = raw["entry_point"]
        if (
            not isinstance(provider_id, str)
            or not provider_id
            or len(provider_id) > 64
            or not isinstance(display_name, str)
            or not 1 <= len(display_name) <= 100
            or not isinstance(entry_name, str)
            or not entry_name
        ):
            raise ProviderProtocolError("provider manifest identity is invalid")
        entry = (self.root / entry_name).resolve()
        if (
            not entry.is_relative_to(self.root)
            or not entry.is_file()
            or entry.is_symlink()
        ):
            raise ProviderProtocolError("provider entry point is unsafe")
        hosts = raw["url_hosts"]
        if (
            not isinstance(hosts, list)
            or not hosts
            or len(hosts) > 32
            or len(hosts) != len(set(hosts))
            or not all(
                isinstance(host, str)
                and 1 <= len(host) <= 253
                and host == host.casefold().strip()
                and "/" not in host
                and "\\" not in host
                for host in hosts
            )
        ):
            raise ProviderProtocolError("provider URL hosts are invalid")
        permissions = raw["permissions"]
        allowed_by_provider = {
            "youtube": {
                "network.youtube",
                "storage.downloads.write",
                "storage.temp.write",
                "process.ffmpeg",
                "process.javascript",
            },
            "youtube-search": {"network.youtube", "process.javascript"},
            "bilibili-search": {"network.bilibili"},
            "ani-gamer-search": {"network.ani-gamer"},
            "ani-gamer-episodes": {"network.ani-gamer"},
            "youtube-player": {
                "network.youtube",
                "storage.temp.write",
                "process.ffmpeg",
                "process.javascript",
            },
            "youtube-history": {"storage.history.write"},
            "youtube-recovery": set(),
            "youtube-similar": set(),
            "youtube-auto-split": {"process.ffmpeg", "storage.temp.read"},
            "generic-ytdlp": {
                "network.generic",
                "storage.downloads.write",
                "process.ffmpeg",
                "process.javascript",
            },
            "bilibili": {
                "network.bilibili",
                "storage.downloads.write",
                "process.ffmpeg",
                "process.javascript",
            },
            "facebook": {
                "network.facebook",
                "storage.downloads.write",
                "process.ffmpeg",
                "process.javascript",
            },
            "mega": {
                "network.mega",
                "storage.downloads.write",
                "process.megacmd",
            },
            "direct-http": {
                "network.direct-http",
                "storage.downloads.write",
            },
            "test": {
                "network.youtube",
                "storage.downloads.write",
                "storage.temp.write",
                "process.ffmpeg",
            },
        }
        allowed = allowed_by_provider.get(provider_id)
        if (
            allowed is None
            or not isinstance(permissions, list)
            or len(permissions) != len(set(permissions))
            or not all(
                isinstance(item, str) and item in allowed for item in permissions
            )
        ):
            raise ProviderProtocolError(
                "provider permissions are invalid or not allowed"
            )
        search_capability = None
        if "search_capability" in raw:
            try:
                search_capability = SearchCapabilityV2.from_dict(
                    raw["search_capability"]
                )
            except SearchContractV2Error as error:
                raise ProviderProtocolError(
                    f"search capability is invalid: {error}"
                ) from error
            if search_capability.provider_id != provider_id:
                raise ProviderProtocolError("search capability provider mismatch")
        return (
            provider_id,
            display_name,
            entry,
            frozenset(host.casefold() for host in hosts),
            tuple(permissions),
            search_capability,
        )

    def _verify_expected_files(self) -> None:
        for relative, expected in self.expected_hashes.items():
            path = (self.root / relative).resolve()
            if (
                not path.is_relative_to(self.root)
                or not path.is_file()
                or path.is_symlink()
            ):
                raise ProviderProtocolError(f"provider file is unsafe: {relative}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                raise ProviderProtocolError(f"provider integrity mismatch: {relative}")

    @staticmethod
    def _minimal_environment(runtime_home: Path | None = None) -> dict[str, str]:
        allowed = ("PATH", "SYSTEMROOT", "TEMP", "TMP")
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        environment["PYTHONNOUSERSITE"] = "1"
        if runtime_home is not None:
            runtime_home.mkdir(parents=True, exist_ok=True)
            cache_home = runtime_home / "cache"
            cache_home.mkdir(parents=True, exist_ok=True)
            environment.update(
                {
                    "HOME": str(runtime_home),
                    "USERPROFILE": str(runtime_home),
                    "XDG_CACHE_HOME": str(cache_home),
                }
            )
        return environment

    def supports(self, url: str) -> bool:
        if self.provider_id == "direct-http":
            return direct_http_url_candidate(url)
        try:
            parsed = urlparse(url)
            parsed.port
        except ValueError:
            return False
        return (
            parsed.scheme.casefold() in {"http", "https"}
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and (parsed.hostname or "").casefold() in self.hosts
        )

    def _require_permissions(self, *required: str) -> None:
        missing = sorted(set(required) - set(self.permissions))
        if missing:
            raise ProviderProtocolError(
                f"provider lacks required permissions: {', '.join(missing)}"
            )

    def _require_download_network(self) -> None:
        permission = {
            "generic-ytdlp": "network.generic",
            "bilibili": "network.bilibili",
            "facebook": "network.facebook",
            "mega": "network.mega",
            "direct-http": "network.direct-http",
        }.get(self.provider_id, "network.youtube")
        self._require_permissions(permission)

    def _require_search_network(self) -> None:
        permission = {
            "youtube-search": "network.youtube",
            "bilibili-search": "network.bilibili",
            "ani-gamer-search": "network.ani-gamer",
            "ani-gamer-episodes": "network.ani-gamer",
            "test": "network.youtube",
        }.get(self.provider_id)
        if permission is None:
            raise ProviderProtocolError(
                "search provider has no explicit network permission mapping"
            )
        self._require_permissions(permission)

    def analyze(self, url: str) -> dict[str, Any]:
        self._require_download_network()
        if not self.supports(url):
            raise ValueError("URL is not supported by this MOD")
        result = self._execute(
            {"operation": "analyze", "url": url},
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("provider analyze result is invalid")
        try:
            parse_media_formats(result.get("formats", []))
            parse_media_languages(result.get("audio_languages", []))
            parse_media_languages(result.get("subtitle_languages", []))
        except ValueError as error:
            raise ProviderProtocolError(
                f"provider media formats are invalid: {error}"
            ) from error
        return result

    def playlist(
        self, url: str, *, limit: int = MAX_PLAYLIST_ENTRIES_V1
    ) -> tuple[PlaylistEntryV1, ...]:
        self._require_download_network()
        if not self.supports(url):
            raise ValueError("URL is not supported by this MOD")
        bounded_limit = max(1, min(int(limit), MAX_PLAYLIST_ENTRIES_V1))
        result = self._execute(
            {"operation": "playlist", "url": url, "limit": bounded_limit},
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, list) or len(result) > bounded_limit:
            raise ProviderProtocolError("provider playlist result is invalid")
        entries = tuple(PlaylistEntryV1.from_dict(item) for item in result)
        if len({entry.position for entry in entries}) != len(entries):
            raise ProviderProtocolError("provider playlist positions are duplicated")
        return entries

    def search(
        self,
        query: str,
        *,
        limit: int = 12,
        content_type: str = "all",
    ) -> tuple[DiscoveryItemV1, ...]:
        capability = self.search_capability or SearchCapabilityV2(
            self.provider_id,
            (self.provider_id,),
            ("all", "music", "video"),
            20,
            "none",
            False,
            False,
        )
        normalized = SearchQueryV2(query, content_type, limit).normalized(capability)
        return self.search_page(normalized).items

    def search_page(self, query: SearchQueryV2) -> SearchPageV2:
        self._require_search_network()
        capability = self.search_capability or SearchCapabilityV2(
            self.provider_id,
            (self.provider_id,),
            ("all", "music", "video"),
            20,
            "none",
            False,
            False,
        )
        normalized = query.normalized(capability)
        result = self._execute(
            {
                "operation": "search",
                "query": normalized.query,
                "limit": normalized.page_size,
                "content_type": normalized.content_type,
                "cursor": normalized.cursor,
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if isinstance(result, list) and capability.pagination == "none":
            result = {"items": result, "next_cursor": ""}
        if not isinstance(result, dict) or set(result) != {"items", "next_cursor"}:
            raise ProviderProtocolError("provider search page is invalid")
        items = result["items"]
        if not isinstance(items, list) or len(items) > normalized.page_size:
            raise ProviderProtocolError("provider search result is invalid")
        try:
            return SearchPageV2(
                self.provider_id,
                tuple(DiscoveryItemV1.from_dict(item) for item in items),
                result["next_cursor"],
            )
        except (TypeError, ValueError) as error:
            raise ProviderProtocolError(
                f"provider search page is invalid: {error}"
            ) from error

    def similar_plan(
        self,
        item: DiscoveryItemV1,
        preferences: HistoryPreferencesV1,
    ) -> SimilarPlanV1:
        result = self._execute(
            {
                "operation": "similar_plan",
                "item": asdict(item),
                "preferences": asdict(preferences),
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("similar plan result is invalid")
        return SimilarPlanV1.from_dict(result)

    def select_similar(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
        preferences: HistoryPreferencesV1,
    ) -> SimilarSelectionV1 | None:
        result = self._execute(
            {
                "operation": "similar_select",
                "item": asdict(original),
                "candidates": [asdict(item) for item in candidates],
                "preferences": asdict(preferences),
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if result is None:
            return None
        if not isinstance(result, dict):
            raise ProviderProtocolError("similar selection result is invalid")
        return SimilarSelectionV1.from_dict(result)

    def rank_similar(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
        preferences: HistoryPreferencesV1,
        *,
        limit: int = 12,
    ) -> tuple[SimilarSelectionV1, ...]:
        bounded_limit = max(1, min(int(limit), 50))
        result = self._execute(
            {
                "operation": "similar_rank",
                "item": asdict(original),
                "candidates": [asdict(item) for item in candidates[:120]],
                "preferences": asdict(preferences),
                "limit": bounded_limit,
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, list) or len(result) > bounded_limit:
            raise ProviderProtocolError("similar ranked result is invalid")
        selections = tuple(SimilarSelectionV1.from_dict(item) for item in result)
        if len({selection.item.video_id for selection in selections}) != len(selections):
            raise ProviderProtocolError("similar ranked results are duplicated")
        return selections

    def recovery_plan(self, item: DiscoveryItemV1) -> RecoveryPlanV1:
        result = self._execute(
            {"operation": "recovery_plan", "item": asdict(item)},
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("recovery plan result is invalid")
        return RecoveryPlanV1.from_dict(result)

    def split_filename(
        self,
        *,
        source_title: str,
        index: int,
        track_title: str,
        start: float,
        duration: float,
        extension: str,
    ) -> str:
        result = self._execute(
            {
                "operation": "split_filename",
                "source_title": source_title,
                "index": index,
                "track_title": track_title,
                "start": start,
                "duration": duration,
                "extension": extension,
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, str) or not result or len(result) > 180:
            raise ProviderProtocolError("split filename result is invalid")
        return result

    def split_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        chapters: list[dict[str, Any]],
        description: str,
    ) -> SplitPlanV1:
        if not self.supports(source_url):
            raise ValueError("URL is not supported by this MOD")
        result = self._execute(
            {
                "operation": "split_plan",
                "source_url": source_url,
                "source_title": source_title,
                "duration": duration,
                "chapters": chapters[:200],
                "description": description[:20_000],
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("split plan result is invalid")
        return SplitPlanV1.from_dict(result)

    def prepare_audio_preview(
        self,
        url: str,
        *,
        duration: float,
        preview_length: float | None = None,
        progress=None,
    ) -> Path:
        self._require_permissions(
            "network.youtube", "storage.temp.write", "process.ffmpeg"
        )
        if not self.supports(url) or self.provider_id != "youtube":
            raise ValueError("URL is not supported by the preview MOD")
        if (
            self.preview_root is None
            or "storage.temp.write" not in self.permissions
            or "process.ffmpeg" not in self.permissions
            or not Path(self.ffmpeg_location or "").is_file()
            or not 0 < duration <= 86400
            or (preview_length is not None and not 0 < preview_length <= 120)
        ):
            raise ProviderProtocolError("audio preview configuration is invalid")
        self.preview_root.mkdir(parents=True, exist_ok=True)
        session = (self.preview_root / uuid.uuid4().hex).resolve()
        if not session.is_relative_to(self.preview_root):
            raise ProviderProtocolError("audio preview session path is unsafe")
        session.mkdir()
        try:
            result = self._execute(
                {
                    "operation": "prepare_preview",
                    "url": url,
                    "duration": duration,
                    "preview_length": preview_length,
                    "output_dir": str(session),
                    "ffmpeg_location": self.ffmpeg_location,
                },
                progress,
                threading.Event(),
                timeout=self.download_timeout,
                idle_timeout=self.idle_timeout,
            )
            path = Path(result).resolve() if isinstance(result, str) else Path()
            if (
                not path.is_relative_to(session)
                or not path.is_file()
                or path.is_symlink()
                or path.stat().st_size == 0
            ):
                raise ProviderProtocolError("audio preview result is invalid")
            return path
        except Exception:
            shutil.rmtree(session, ignore_errors=True)
            raise

    def cleanup_audio_preview(self, preview_path: Path) -> bool:
        if self.preview_root is None:
            return False
        path = preview_path.resolve()
        session = path.parent
        if (
            not path.is_relative_to(self.preview_root)
            or session.parent != self.preview_root
            or len(session.name) != 32
            or any(character not in "0123456789abcdef" for character in session.name)
            or not session.is_dir()
            or session.is_symlink()
        ):
            return False
        try:
            shutil.rmtree(session)
        except OSError:
            return False
        return not session.exists()

    def prepare_video_preview(
        self,
        url: str,
        *,
        duration: float,
        preview_length: float = 60,
        progress=None,
    ) -> Path:
        self._require_permissions(
            "network.youtube", "storage.temp.write", "process.ffmpeg"
        )
        if not self.supports(url) or self.provider_id != "youtube-player":
            raise ValueError("URL is not supported by the video player MOD")
        if (
            self.preview_root is None
            or "storage.temp.write" not in self.permissions
            or "process.ffmpeg" not in self.permissions
            or not Path(self.ffmpeg_location or "").is_file()
            or not 0 < duration <= 86400
            or not 0 < preview_length <= 120
        ):
            raise ProviderProtocolError("video preview configuration is invalid")
        self.preview_root.mkdir(parents=True, exist_ok=True)
        session = (self.preview_root / uuid.uuid4().hex).resolve()
        if not session.is_relative_to(self.preview_root):
            raise ProviderProtocolError("video preview session path is unsafe")
        session.mkdir()
        try:
            result = self._execute(
                {
                    "operation": "prepare_video_preview",
                    "url": url,
                    "duration": duration,
                    "preview_length": preview_length,
                    "output_dir": str(session),
                    "ffmpeg_location": self.ffmpeg_location,
                },
                progress,
                threading.Event(),
                timeout=self.download_timeout,
                idle_timeout=self.idle_timeout,
            )
            path = Path(result).resolve() if isinstance(result, str) else Path()
            if (
                not path.is_relative_to(session)
                or not path.is_file()
                or path.is_symlink()
                or path.stat().st_size == 0
            ):
                raise ProviderProtocolError("video preview result is invalid")
            return path
        except Exception:
            shutil.rmtree(session, ignore_errors=True)
            raise

    def cleanup_video_preview(self, preview_path: Path) -> bool:
        return self.cleanup_audio_preview(preview_path)

    def split_audio_plan(
        self,
        *,
        source_url: str,
        source_title: str,
        duration: float,
        input_path: Path,
        threshold_db: float = -35.0,
        min_silence: float = 1.2,
    ) -> SplitPlanV1:
        self._require_permissions("process.ffmpeg", "storage.temp.read")
        if not self.supports(source_url):
            raise ValueError("URL is not supported by this MOD")
        resolved_input = input_path.resolve()
        if (
            self.provider_id != "youtube-auto-split"
            or self.analysis_root is None
            or not resolved_input.is_relative_to(self.analysis_root)
            or not resolved_input.is_file()
            or resolved_input.is_symlink()
        ):
            raise ProviderProtocolError(
                "audio analysis input is outside the temporary root"
            )
        ffmpeg = Path(self.ffmpeg_location or "").resolve()
        if not ffmpeg.is_file() or "process.ffmpeg" not in self.permissions:
            raise ProviderProtocolError("FFmpeg configuration is invalid")
        result = self._execute(
            {
                "operation": "split_audio_plan",
                "source_url": source_url,
                "source_title": source_title,
                "duration": duration,
                "input_path": str(resolved_input),
                "ffmpeg_location": str(ffmpeg),
                "threshold_db": threshold_db,
                "min_silence": min_silence,
            },
            None,
            threading.Event(),
            timeout=max(self.analyze_timeout, 75.0),
            idle_timeout=max(self.analyze_timeout, 75.0),
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("audio split plan result is invalid")
        return SplitPlanV1.from_dict(result)

    def rank_recovery(
        self,
        original: DiscoveryItemV1,
        candidates: tuple[DiscoveryItemV1, ...],
    ) -> tuple[RecoveryCandidateV1, ...]:
        result = self._execute(
            {
                "operation": "recovery_rank",
                "item": asdict(original),
                "candidates": [asdict(item) for item in candidates[:50]],
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, list) or len(result) > len(candidates):
            raise ProviderProtocolError("recovery ranking result is invalid")
        return tuple(RecoveryCandidateV1.from_dict(item) for item in result)

    def _history_payload(self) -> dict[str, str]:
        self._require_permissions("storage.history.write")
        if self.provider_id != "youtube-history" or self.history_state_path is None:
            raise ProviderProtocolError("history state is unavailable")
        return {"state_path": str(self.history_state_path)}

    def record_history(
        self, event_type: str, query: str, item: DiscoveryItemV1 | None = None
    ) -> None:
        event = {
            "event_type": event_type,
            "query": " ".join(query.split()),
            "item": asdict(item) if item is not None else None,
        }
        result = self._execute(
            {"operation": "history_record", "event": event, **self._history_payload()},
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if result is not True:
            raise ProviderProtocolError("history record result is invalid")

    def recent_history(self, *, limit: int = 20) -> tuple[HistoryEventV1, ...]:
        bounded_limit = max(1, min(int(limit), 100))
        result = self._execute(
            {
                "operation": "history_recent",
                "limit": bounded_limit,
                **self._history_payload(),
            },
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, list) or len(result) > bounded_limit:
            raise ProviderProtocolError("history recent result is invalid")
        return tuple(HistoryEventV1.from_dict(event) for event in result)

    def history_preferences(self) -> HistoryPreferencesV1:
        result = self._execute(
            {"operation": "history_preferences", **self._history_payload()},
            None,
            threading.Event(),
            timeout=self.analyze_timeout,
            idle_timeout=self.analyze_timeout,
        )
        if not isinstance(result, dict):
            raise ProviderProtocolError("history preferences result is invalid")
        return HistoryPreferencesV1.from_dict(result)

    def download(
        self, request: DownloadRequest, progress, cancel_event: threading.Event
    ) -> str:
        self._require_download_network()
        self._require_permissions("storage.downloads.write")
        if not self.supports(request.url):
            raise ValueError("URL is not supported by this MOD")
        payload = {
            "operation": "download",
            "url": request.url,
            "output_dir": str(request.output_dir.resolve()),
            "start_time": request.start_time,
            "end_time": request.end_time,
            "ffmpeg_location": self.ffmpeg_location,
            "output_filename": request.output_filename,
            "audio_only": request.audio_only,
            "format_preset": request.format_preset,
            "subtitle_mode": request.subtitle_mode,
            "subtitle_languages": list(request.subtitle_languages),
            "timed_comment_mode": request.timed_comment_mode,
            "container_preset": request.container_preset,
            "provider_options": dict(request.provider_options),
        }
        result = self._execute(
            payload,
            progress,
            cancel_event,
            timeout=self.download_timeout,
            idle_timeout=self.idle_timeout,
        )
        if not isinstance(result, str) or not result:
            raise ProviderProtocolError("provider download result is invalid")
        output_root = request.output_dir.resolve()
        output_path = Path(result).resolve()
        valid_file = output_path.is_file() and output_path.stat().st_size > 0
        valid_mega_folder = (
            self.provider_id == "mega"
            and request.source_category == "mega-folder"
            and output_path.is_dir()
        )
        if (
            not output_path.is_relative_to(output_root)
            or not (valid_file or valid_mega_folder)
            or output_path.is_symlink()
        ):
            raise ProviderProtocolError(
                "provider download result is missing or outside the output directory"
            )
        return str(output_path)

    def _command(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [
                sys.executable,
                "--provider-host",
                str(self.entry_point),
                "--provider-root",
                str(self.root.parent),
            ]
        return [sys.executable, "-I", str(self.entry_point)]

    def _execute(
        self,
        payload,
        progress,
        cancel_event,
        *,
        timeout: float,
        idle_timeout: float,
    ):
        self._verify_expected_files()
        payload = dict(payload)
        if self.js_runtime is not None:
            runtime_name, runtime_path = self.js_runtime
            payload["js_runtime"] = {
                "name": runtime_name,
                "path": runtime_path,
            }
        if self.provider_id == "mega":
            payload["external_tools"] = dict(self.external_tools)
        job = ProviderJob()
        try:
            process = subprocess.Popen(
                self._command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                cwd=self.root,
                env=self._minimal_environment(self.runtime_home),
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            job.assign(int(getattr(process, "_handle", 0)))
        except Exception:
            job.close()
            raise
        with self._lock:
            self._processes.add(process)
        messages: queue.Queue[str | None | ProviderProtocolError] = queue.Queue(
            maxsize=_PROVIDER_MESSAGE_BACKLOG
        )
        reader_stopping = threading.Event()
        stderr_parts: list[str] = []
        stderr_size = 0
        stderr_truncated = False
        stderr_lock = threading.Lock()

        def stop_process_tree(*, force: bool = False) -> None:
            # On Windows, closing the kill-on-close Job Object is what stops
            # yt-dlp's FFmpeg and JavaScript-runtime children as well as the
            # provider host. Terminating only the host can leave those child
            # processes downloading after the UI says the task has stopped.
            if os.name == "nt":
                job.close()
            if process.poll() is None:
                try:
                    if force:
                        process.kill()
                    else:
                        process.terminate()
                except OSError:
                    pass

        def post_message(message: str | None | ProviderProtocolError) -> bool:
            while not reader_stopping.is_set():
                try:
                    messages.put(message, timeout=0.1)
                    return True
                except queue.Full:
                    continue
            return False

        def read_stdout() -> None:
            assert process.stdout is not None
            while not reader_stopping.is_set():
                line = process.stdout.readline(_MAX_PROVIDER_MESSAGE_CHARS + 1)
                if not line:
                    post_message(None)
                    return
                if len(line) > _MAX_PROVIDER_MESSAGE_CHARS:
                    post_message(
                        ProviderProtocolError("provider message exceeds size limit")
                    )
                    return
                if not post_message(line):
                    return

        def read_stderr() -> None:
            nonlocal stderr_size, stderr_truncated
            assert process.stderr is not None
            while True:
                chunk = process.stderr.read(4096)
                if not chunk:
                    return
                with stderr_lock:
                    remaining = _MAX_PROVIDER_STDERR_CHARS - stderr_size
                    if remaining > 0:
                        retained = chunk[:remaining]
                        stderr_parts.append(retained)
                        stderr_size += len(retained)
                    if len(chunk) > remaining:
                        stderr_truncated = True

        def stderr_text() -> str:
            with stderr_lock:
                value = "".join(stderr_parts).strip()
                truncated = stderr_truncated
            if truncated:
                suffix = "[provider stderr truncated]"
                suffix_bytes = len(f"\n{suffix}".encode("utf-8"))
                retained = bounded_redacted_text(
                    value,
                    max_utf8_bytes=max(
                        1, _MAX_PROVIDER_STDERR_CHARS - suffix_bytes
                    ),
                )
                return f"{retained}\n{suffix}" if retained else suffix
            return bounded_redacted_text(
                value, max_utf8_bytes=_MAX_PROVIDER_STDERR_CHARS
            )

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        try:
            assert process.stdin is not None
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.close()
            deadline = time.monotonic() + timeout
            last_activity = time.monotonic()
            no_result_phase = "stdout_eof"
            while True:
                if cancel_event.is_set():
                    stop_process_tree()
                    raise DownloadCancelled("download cancelled")
                if time.monotonic() - last_activity > idle_timeout:
                    stop_process_tree(force=True)
                    raise TimeoutError("provider stopped reporting progress")
                if time.monotonic() > deadline:
                    stop_process_tree(force=True)
                    raise TimeoutError("provider operation timed out")
                try:
                    line = messages.get(timeout=0.1)
                except queue.Empty:
                    if process.poll() is not None:
                        # The process can exit after writing a valid result but
                        # before the stdout reader gets scheduled to enqueue it.
                        # Wait for its next message within the existing operation
                        # bounds instead of imposing a second scheduling deadline.
                        now = time.monotonic()
                        result_wait_deadline = min(
                            deadline,
                            last_activity + idle_timeout,
                        )
                        remaining = max(0.0, result_wait_deadline - now)
                        if remaining <= 0:
                            line = None
                            no_result_phase = "handoff_deadline"
                        else:
                            try:
                                line = messages.get(timeout=remaining)
                            except queue.Empty:
                                line = None
                                no_result_phase = "handoff_deadline"
                    else:
                        continue
                if line is None:
                    # stdout can close just before the process reports a useful
                    # bounded error on stderr. Drain within the existing operation
                    # and idle deadlines; a shorter private deadline makes the
                    # result depend on reader-thread scheduling under load.
                    now = time.monotonic()
                    drain_deadline = min(
                        deadline,
                        last_activity + idle_timeout,
                    )
                    remaining = max(0.0, drain_deadline - now)
                    if process.poll() is None and remaining > 0:
                        try:
                            process.wait(timeout=remaining)
                        except subprocess.TimeoutExpired:
                            pass
                    remaining = max(0.0, drain_deadline - time.monotonic())
                    if remaining > 0:
                        stderr_thread.join(timeout=remaining)
                        stdout_thread.join(timeout=remaining)
                    error = stderr_text()
                    raise ProviderProtocolError(
                        error or "provider exited without a result",
                        phase=no_result_phase,
                        exit_code=process.poll(),
                        stdout_reader_complete=not stdout_thread.is_alive(),
                    )
                if isinstance(line, ProviderProtocolError):
                    raise line
                last_activity = time.monotonic()
                try:
                    message = json.loads(line)
                except ValueError as error:
                    raise ProviderProtocolError(
                        "provider emitted invalid JSON"
                    ) from error
                if not isinstance(message, dict) or message.get("type") not in {
                    "progress",
                    "result",
                    "error",
                }:
                    raise ProviderProtocolError("provider message is invalid")
                if message["type"] == "progress":
                    if progress:
                        progress(
                            {
                                "downloaded_bytes": message.get("downloaded_bytes"),
                                "total_bytes": message.get("total_bytes"),
                                "total_bytes_estimate": message.get(
                                    "total_bytes_estimate"
                                ),
                                "_speed_str": message.get("speed", ""),
                                "_eta_str": message.get("eta", ""),
                                "info_dict": {"title": message.get("title", "")},
                            }
                        )
                    continue
                if message["type"] == "error":
                    failure = classify_provider_failure(message.get("error"))
                    safe_message = bounded_redacted_text(
                        failure.message,
                        max_utf8_bytes=1000,
                    )
                    raise ProviderFailure(
                        replace(
                            failure,
                            message=safe_message or "provider failed",
                        )
                    )
                return message.get("value")
        finally:
            reader_stopping.set()
            stop_process_tree()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                stop_process_tree(force=True)
                process.wait(timeout=3)
            stdout_thread.join(timeout=0.5)
            stderr_thread.join(timeout=0.5)
            with self._lock:
                self._processes.discard(process)
            job.close()

    def close(self) -> None:
        with self._lock:
            processes = tuple(self._processes)
        for process in processes:
            if process.poll() is None:
                process.terminate()
