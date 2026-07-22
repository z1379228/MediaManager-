"""Manual, read-only diagnostics for the trusted MediaManager shell."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Literal
from uuid import uuid4

from contracts.diagnostic_evidence_v1 import DiagnosticEvidenceV1
from contracts.provider_capability_v1 import BUILTIN_PROVIDER_CAPABILITY_IDS
from core.builtin_mod_catalog import (
    BUILTIN_MOD_CHILDREN,
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_PARENT,
    OPTIONAL_WORKSPACE_IDS,
    builtin_mod_ids,
)
from core.builtin_mod_snapshot import snapshot_for_context
from core.downloads.capabilities import builtin_provider_capability
from core.downloads.direct_http_policy import direct_http_url_candidate
from core.downloads.site_quality import audit_builtin_site_quality
from core.localization import SUPPORTED_LOCALE_CODES, normalized_core_locale
from core.logging.redaction import bounded_redacted_text
from core.mod_groups import (
    SITE_MOD_CHILDREN,
    SITE_MOD_PARENT,
    load_builtin_mod_groups,
)
from core.security.safe_mode import SecurityMode
from core.site_routing import SiteRoute, classify_site_url
from core.transfers import (
    default_gopeed_bridge_config,
    default_p2p_transfer_policy,
    validate_gopeed_bridge_config,
    validate_p2p_transfer_policy,
)
from core.version import BUILD_CHANNEL, CORE_VERSION


SelfCheckState = Literal["pass", "warning", "block"]
_MAX_SELF_CHECK_EXPORT_BYTES = 1024 * 1024
_MAX_DIAGNOSTIC_EVIDENCE = 16


def _safe_error_detail(error: BaseException, limit: int = 240) -> str:
    """Keep diagnostics useful without copying secrets into exported reports."""

    return bounded_redacted_text(
        f"{type(error).__name__}: {error}", max_utf8_bytes=limit
    )


@dataclass(frozen=True, slots=True)
class SelfCheckItem:
    check_id: str
    state: SelfCheckState
    summary: str
    detail: str
    remediation_id: str


@dataclass(frozen=True, slots=True)
class SelfCheckReport:
    schema_version: int
    core_version: str
    build_channel: str
    items: tuple[SelfCheckItem, ...]
    generated_at: str = ""
    run_id: str = ""
    diagnostic_evidence: tuple[DiagnosticEvidenceV1, ...] = ()

    def __post_init__(self) -> None:
        if type(self.diagnostic_evidence) is not tuple:
            raise TypeError("diagnostic_evidence must be a tuple")
        if any(
            type(item) is not DiagnosticEvidenceV1
            for item in self.diagnostic_evidence
        ):
            raise TypeError(
                "diagnostic evidence items must be DiagnosticEvidenceV1"
            )
        if len(self.diagnostic_evidence) > _MAX_DIAGNOSTIC_EVIDENCE:
            raise ValueError("diagnostic evidence exceeds the item limit")
        if any(item.run_id != self.run_id for item in self.diagnostic_evidence):
            raise ValueError("diagnostic evidence run_id does not match the report")

    @property
    def pass_count(self) -> int:
        return sum(item.state == "pass" for item in self.items)

    @property
    def warning_count(self) -> int:
        return sum(item.state == "warning" for item in self.items)

    @property
    def block_count(self) -> int:
        return sum(item.state == "block" for item in self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "core_version": self.core_version,
            "build_channel": self.build_channel,
            "generated_at": self.generated_at,
            "run_id": self.run_id,
            "summary": {
                "pass": self.pass_count,
                "warning": self.warning_count,
                "block": self.block_count,
            },
            "items": [
                {
                    "check_id": bounded_redacted_text(
                        item.check_id, max_utf8_bytes=128
                    ),
                    "state": item.state,
                    "summary": bounded_redacted_text(
                        item.summary, max_utf8_bytes=512
                    ),
                    "detail": bounded_redacted_text(
                        item.detail, max_utf8_bytes=4096
                    ),
                    "remediation_id": bounded_redacted_text(
                        item.remediation_id, max_utf8_bytes=256
                    ),
                }
                for item in self.items
            ],
            "diagnostic_evidence": [
                item.to_dict() for item in self.diagnostic_evidence
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"

    def with_diagnostic_evidence(
        self, *items: DiagnosticEvidenceV1
    ) -> SelfCheckReport:
        return replace(self, diagnostic_evidence=items)


def write_self_check_report(destination: Path, report: SelfCheckReport) -> None:
    """Write one bounded report atomically using only an owned sibling temp file."""

    destination = Path(destination)
    payload = report.to_json().encode("utf-8")
    if len(payload) > _MAX_SELF_CHECK_EXPORT_BYTES:
        raise ValueError("self-check export exceeds size limit")
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(raw_temporary)
    descriptor_open = True
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor_open = False
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        if descriptor_open:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise


def _item(
    check_id: str,
    state: SelfCheckState,
    summary: str,
    detail: str,
    remediation_id: str = "",
) -> SelfCheckItem:
    return SelfCheckItem(check_id, state, summary, detail, remediation_id)


def _deidentified_item(item: SelfCheckItem) -> SelfCheckItem:
    return SelfCheckItem(
        bounded_redacted_text(item.check_id, max_utf8_bytes=128),
        item.state,
        bounded_redacted_text(item.summary, max_utf8_bytes=512),
        bounded_redacted_text(item.detail, max_utf8_bytes=4096),
        bounded_redacted_text(item.remediation_id, max_utf8_bytes=256),
    )


def _normalized_aware_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC).isoformat()


def _registry_item(
    kind: str,
    statuses: tuple[object, ...],
) -> SelfCheckItem:
    expected = builtin_mod_ids(kind)  # type: ignore[arg-type]
    actual = frozenset(str(status.provider_id) for status in statuses)
    missing = tuple(sorted(expected - actual))
    extras = tuple(sorted(actual - expected))
    unavailable = tuple(
        sorted(
            str(status.provider_id)
            for status in statuses
            if not bool(getattr(status, "available", True))
        )
    )
    if missing or unavailable:
        detail = "; ".join(
            part
            for part in (
                f"缺少：{', '.join(missing)}" if missing else "",
                f"不可用：{', '.join(unavailable)}" if unavailable else "",
            )
            if part
        )
        return _item(
            f"registry.{kind}",
            "block",
            f"{kind} MOD registry 不完整",
            detail,
            f"registry.{kind}.repair",
        )
    if extras:
        return _item(
            f"registry.{kind}",
            "warning",
            f"{kind} MOD registry 含未編目項目",
            f"未編目：{', '.join(extras)}",
            f"catalog.{kind}.review",
        )
    return _item(
        f"registry.{kind}",
        "pass",
        f"{kind} MOD registry 完整",
        f"已核對 {len(actual)} 個項目",
    )


def _release_item(application_root: Path) -> SelfCheckItem:
    path = application_root / "release-info.json"
    if not path.is_file():
        state: SelfCheckState = (
            "warning" if BUILD_CHANNEL in {"development", "testing"} else "block"
        )
        return _item(
            "release.metadata",
            state,
            "來源樹未附發行資訊" if state == "warning" else "正式版缺少發行資訊",
            "開發／測試來源樹可略過；打包附件必須包含 release-info.json。",
            "release.stage" if state == "warning" else "release.metadata.restore",
        )
    try:
        if path.stat().st_size > 64_000:
            raise ValueError("release metadata exceeds size limit")
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        return _item(
            "release.metadata",
            "block",
            "發行資訊無法驗證",
            _safe_error_detail(error),
            "release.metadata.rebuild",
        )
    if not isinstance(document, dict):
        return _item(
            "release.metadata",
            "block",
            "發行資訊格式錯誤",
            "release-info.json 必須是物件",
            "release.metadata.rebuild",
        )
    mismatch = []
    if document.get("core_version") != CORE_VERSION:
        mismatch.append("core_version")
    if document.get("build_channel") != BUILD_CHANNEL:
        mismatch.append("build_channel")
    if mismatch:
        return _item(
            "release.metadata",
            "block",
            "發行資訊與目前程式不一致",
            f"不一致欄位：{', '.join(mismatch)}",
            "release.metadata.rebuild",
        )
    return _item(
        "release.metadata",
        "pass",
        "發行資訊與目前程式一致",
        f"schema {document.get('schema_version', 'unknown')}",
    )


def _provider_capability_item(statuses: tuple[object, ...]) -> SelfCheckItem:
    """Validate declarative provider capabilities without refreshing providers."""

    provider_ids = {
        str(status.provider_id)
        for status in statuses
        if str(status.provider_id) in BUILTIN_PROVIDER_CAPABILITY_IDS
    }
    missing = sorted(BUILTIN_PROVIDER_CAPABILITY_IDS - provider_ids)
    if missing:
        return _item(
            "provider.capability_contract",
            "block",
            "下載 Provider 能力契約缺少項目",
            f"缺少：{', '.join(missing)}",
            "provider.capability_contract.repair",
        )
    try:
        for provider_id in sorted(provider_ids):
            builtin_provider_capability(provider_id)
    except (KeyError, ValueError, TypeError) as error:
        return _item(
            "provider.capability_contract",
            "block",
            "下載 Provider 能力契約無效",
            _safe_error_detail(error),
            "provider.capability_contract.repair",
        )
    return _item(
        "provider.capability_contract",
        "pass",
        "下載 Provider 能力契約一致",
        f"已核對 {len(provider_ids)} 個下載 Provider",
    )


def _parent_child_state_item(context: object) -> SelfCheckItem:
    snapshot = snapshot_for_context(context)
    states: dict[str, bool] = {}
    for statuses in (snapshot.download, snapshot.discovery, snapshot.feature):
        states.update(
            (str(status.provider_id), bool(status.enabled)) for status in statuses
        )
    violations = tuple(
        child_id
        for parent_id, child_ids in BUILTIN_MOD_CHILDREN.items()
        if parent_id in states and not states[parent_id]
        for child_id in child_ids
        if states.get(child_id, False)
    )
    return _item(
        "state.parent_child",
        "block" if violations else "pass",
        "停用主 MOD 仍有啟用子 MOD" if violations else "主 MOD／子 MOD 狀態一致",
        (
            f"異常子 MOD：{', '.join(violations)}"
            if violations
            else f"已核對 {len(BUILTIN_MOD_PARENT)} 個子 MOD 的啟用狀態"
        ),
        "state.parent_child.reconcile" if violations else "",
    )


def _locale_item(context: object) -> SelfCheckItem:
    raw_locale = getattr(getattr(context, "settings", None), "language", None)
    selected_locale = normalized_core_locale(raw_locale)
    plugin_locale = getattr(getattr(context, "plugin_ui", None), "locale", None)
    problems: list[str] = []
    if raw_locale not in SUPPORTED_LOCALE_CODES:
        problems.append("核心語言設定不存在或不受支援")
    if plugin_locale != selected_locale:
        problems.append("外部 MOD 宣告式 UI 語言未跟隨核心")
    try:
        groups = load_builtin_mod_groups(selected_locale)
    except (OSError, ValueError) as error:
        problems.append(
            bounded_redacted_text(
                f"網站 MOD 語言資源無法讀取：{error}", max_utf8_bytes=512
            )
        )
        groups = ()
    if groups and (
        {group.group_id for group in groups} != set(SITE_MOD_CHILDREN)
        or any(group.locale != selected_locale for group in groups)
    ):
        problems.append("網站 MOD 語言資源與核心選擇不一致")
    return _item(
        "localization.binding",
        "block" if problems else "pass",
        "核心與 MOD 語言綁定異常" if problems else "核心與 MOD 語言綁定正常",
        "; ".join(problems)
        if problems
        else f"{selected_locale} 已套用至 {len(groups)} 個網站父 MOD",
        "localization.binding.repair" if problems else "",
    )


def _site_routing_item() -> SelfCheckItem:
    matrix = (
        (
            "https://music.youtube.com/watch?v=example&list=PL_example",
            SiteRoute("youtube", "playlist-context", "youtube", "youtube-search"),
        ),
        (
            "https://www.bilibili.com/video/BV1example",
            SiteRoute("bilibili", "video", "bilibili", "bilibili-search"),
        ),
        (
            "https://search.bilibili.com/all?keyword=example",
            SiteRoute("bilibili", "search-page", None, "bilibili-search"),
        ),
        (
            "https://www.facebook.com/reel/123456",
            SiteRoute("facebook", "video-page", "facebook", None),
        ),
        (
            "https://mega.nz/folder/AbCdEf12#abcdefghijklmnop",
            SiteRoute("mega", "public-folder", "mega", None),
        ),
    )
    failures = [
        expected.site_family
        for url, expected in matrix
        if classify_site_url(url) != expected
    ]
    catalog_ids = {item.provider_id for item in BUILTIN_MOD_CATALOG}
    for _, expected in matrix:
        for provider_id in (
            expected.download_provider_id,
            expected.search_provider_id,
        ):
            if provider_id and provider_id not in catalog_ids:
                failures.append(provider_id)
    if classify_site_url("https://music.youtube.com.evil.test/watch?v=example"):
        failures.append("spoofed-youtube")
    if not direct_http_url_candidate("https://downloads.example.test/archive.zip"):
        failures.append("direct-http-positive")
    if direct_http_url_candidate("https://www.youtube.com/archive.zip"):
        failures.append("direct-http-site-takeover")
    unique_failures = tuple(dict.fromkeys(failures))
    return _item(
        "routing.site_matrix",
        "block" if unique_failures else "pass",
        "網站網址路由契約異常" if unique_failures else "網站網址路由契約正常",
        (
            f"失敗項目：{', '.join(unique_failures)}"
            if unique_failures
            else f"已核對 {len(matrix)} 條網域路由與 Direct HTTP 隔離"
        ),
        "routing.site_matrix.repair" if unique_failures else "",
    )


def _site_quality_item(application_root: Path) -> SelfCheckItem:
    root = application_root.resolve()
    if not (root / "mod" / "builtin").is_dir():
        root = Path(__file__).resolve().parents[1]
    report = audit_builtin_site_quality(root)
    return _item(
        "site.capability_matrix",
        "pass" if report.valid else "block",
        "網站工作流能力矩陣正常" if report.valid else "網站工作流能力矩陣異常",
        (
            f"已核對 {report.checked_sites} 個網站、{report.checked_features} 項功能與 "
            f"{report.checked_workflows} 個工作流階段"
            if report.valid
            else "; ".join(report.errors[:12])
        ),
        "site.capability_matrix.repair" if not report.valid else "",
    )


def _transport_boundary_item() -> SelfCheckItem:
    """Verify optional transfer defaults without contacting external tools."""

    try:
        gopeed = default_gopeed_bridge_config()
        p2p = default_p2p_transfer_policy()
        validate_gopeed_bridge_config(
            {
                "enabled": gopeed.enabled,
                "endpoint": gopeed.endpoint,
                "token": None,
                "request_timeout_seconds": gopeed.request_timeout_seconds,
                "max_tasks": gopeed.max_tasks,
                "auto_start": gopeed.auto_start,
                "allow_remote": gopeed.allow_remote,
            }
        )
        validate_p2p_transfer_policy(
            {
                "enabled": p2p.enabled,
                "storage_root": None,
                "max_storage_bytes": p2p.max_storage_bytes,
                "max_download_bps": p2p.max_download_bps,
                "max_upload_bps": p2p.max_upload_bps,
                "legal_use_confirmed": p2p.legal_use_confirmed,
                "upload_enabled": p2p.upload_enabled,
                "seeding_enabled": p2p.seeding_enabled,
                "search_enabled": p2p.search_enabled,
                "auto_port_forward": p2p.auto_port_forward,
                "listen_port": p2p.listen_port,
            }
        )
    except (TypeError, ValueError, RuntimeError) as error:
        return _item(
            "transport.boundary",
            "block",
            "選用傳輸安全基線異常",
            _safe_error_detail(error),
            "transport.boundary.repair",
        )
    return _item(
        "transport.boundary",
        "pass",
        "選用傳輸維持未配置",
        "Gopeed／P2P MOD 可在全新 profile 啟用，但 Bridge 與傳輸政策預設未配置；"
        "自檢未連線、未啟動程序、未開啟埠或保存 token。",
    )


def _download_queue_item(context: object) -> SelfCheckItem:
    """Report the warm queue surface without starting or mutating work."""

    queue = getattr(context, "download_queue", None)
    snapshots = getattr(queue, "snapshots", None)
    if queue is None or not callable(snapshots):
        return _item(
            "downloads.queue",
            "warning",
            "下載佇列尚未附加至目前工作階段",
            "自檢只檢查已建立的佇列；不會啟動背景工作或重新讀取網路任務",
            "downloads.queue.attach",
        )
    try:
        state_counts = getattr(queue, "state_counts", None)
        if callable(state_counts):
            counts = state_counts()
            if not isinstance(counts, dict) or any(
                not isinstance(key, str)
                or not isinstance(value, int)
                or value < 0
                for key, value in counts.items()
            ):
                raise ValueError("download queue state counts are invalid")
            tasks = ()
        else:
            tasks = tuple(snapshots())
    except Exception as error:
        return _item(
            "downloads.queue",
            "block",
            "下載佇列狀態無法讀取",
            _safe_error_detail(error),
            "downloads.queue.repair",
        )
    if tasks:
        counts = {}
        for task in tasks:
            raw_state = getattr(task, "state", None)
            state = str(getattr(raw_state, "value", raw_state or "unknown"))
            counts[state] = counts.get(state, 0) + 1
    detail = ", ".join(f"{name}={counts[name]}" for name in sorted(counts)) or "empty"
    total = sum(counts.values())
    return _item(
        "downloads.queue",
        "pass",
        "下載佇列可讀取且維持手動控制",
        f"目前 {total} 項（{detail}）；重啟後工作仍需使用者明確恢復",
    )


def load_provider_smoke_report(path: Path) -> SelfCheckItem:
    """Load one bounded manual smoke report without contacting any provider."""

    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 512_000:
            raise ValueError("smoke report is missing or unsafe")
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        return _item(
            "smoke.latest",
            "block",
            "手動 smoke 報告無法讀取",
            _safe_error_detail(error),
            "smoke.report.replace",
        )
    if not isinstance(document, dict):
        return _item(
            "smoke.latest",
            "block",
            "手動 smoke 報告格式錯誤",
            "報告根節點必須是 JSON 物件",
            "smoke.report.replace",
        )
    summary = document.get("summary")
    cases = document.get("cases")
    generated_at = document.get("generated_at")
    normalized_generated_at = _normalized_aware_timestamp(generated_at)
    valid_shape = (
        document.get("schema_version") == 2
        and document.get("mode") == "live-public-content"
        and document.get("status") in {"PASS", "FAIL"}
        and isinstance(summary, dict)
        and set(summary) == {"passed", "failed", "temporary_upstream"}
        and all(type(summary[key]) is int and 0 <= summary[key] <= 100 for key in summary)
        and isinstance(cases, list)
        and len(cases) <= 100
        and normalized_generated_at is not None
    )
    if not valid_shape:
        return _item(
            "smoke.latest",
            "block",
            "手動 smoke 報告格式錯誤",
            "只接受 provider smoke matrix schema 2 的有界報告",
            "smoke.report.replace",
        )
    passed = summary["passed"]
    failed = summary["failed"]
    temporary = summary["temporary_upstream"]
    if passed + failed != len(cases) or temporary > failed:
        return _item(
            "smoke.latest",
            "block",
            "手動 smoke 報告計數不一致",
            "summary 與 cases 數量不一致",
            "smoke.report.replace",
        )
    successful = document["status"] == "PASS" and failed == 0
    return _item(
        "smoke.latest",
        "pass" if successful else "warning",
        "最近一次手動 provider smoke 通過" if successful else "最近一次手動 provider smoke 未全綠",
        f"{normalized_generated_at}：通過 {passed}、失敗 {failed}、暫時上游 {temporary}",
        "provider.smoke.review" if not successful else "",
    )


def run_self_check(
    context: object,
    *,
    ui_items: tuple[SelfCheckItem, ...] = (),
    smoke_item: SelfCheckItem | None = None,
) -> SelfCheckReport:
    """Inspect warm in-memory state only; never refresh dependencies or start tools."""

    snapshot = snapshot_for_context(context)
    items: list[SelfCheckItem] = []
    catalog_ids = tuple(item.provider_id for item in BUILTIN_MOD_CATALOG)
    catalog_ok = len(catalog_ids) == len(set(catalog_ids)) and all(
        item.kind in {"download", "discovery", "feature"}
        for item in BUILTIN_MOD_CATALOG
    )
    items.append(
        _item(
            "catalog.identity",
            "pass" if catalog_ok else "block",
            "內建 MOD 編目有效" if catalog_ok else "內建 MOD 編目無效",
            f"已核對 {len(catalog_ids)} 個唯一 ID" if catalog_ok else "ID 重複或類型無效",
            "catalog.repair" if not catalog_ok else "",
        )
    )

    items.extend(
        (
            _registry_item("download", snapshot.download),
            _registry_item("discovery", snapshot.discovery),
            _registry_item("feature", snapshot.feature),
        )
    )
    items.append(_provider_capability_item(snapshot.download))
    items.append(_parent_child_state_item(context))

    parents = {
        item.provider_id: item.parent_provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id
    }
    site_parents = {
        child_id: parent_id
        for child_id, parent_id in parents.items()
        if parent_id in SITE_MOD_CHILDREN
    }
    routing_ok = (
        parents == BUILTIN_MOD_PARENT and site_parents == SITE_MOD_PARENT
    )
    items.append(
        _item(
            "routing.parent_child",
            "pass" if routing_ok else "block",
            "主 MOD／子 MOD 路由一致" if routing_ok else "主 MOD／子 MOD 路由不一致",
            f"已核對 {len(parents)} 個子 MOD" if routing_ok else "編目與群組契約不同步",
            "routing.catalog.sync" if not routing_ok else "",
        )
    )
    items.append(_locale_item(context))
    items.append(_site_routing_item())
    items.append(_site_quality_item(Path(context.paths.application)))
    items.append(_transport_boundary_item())
    items.append(_download_queue_item(context))
    items.append(
        smoke_item
        or _item(
            "smoke.latest",
            "warning",
            "尚未匯入最近一次手動 provider smoke",
            "自檢不會連網；可在自檢頁匯入 tools.provider_smoke_matrix 產生的 JSON。",
            "provider.smoke.import",
        )
    )

    workspace_ok = OPTIONAL_WORKSPACE_IDS == frozenset(
        item.provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.optional_workspace == item.provider_id
        and item.kind in {"download", "feature"}
    )
    items.append(
        _item(
            "ui.optional_workspaces",
            "pass" if workspace_ok else "block",
            "選用工作區編目一致" if workspace_ok else "選用工作區編目不一致",
            f"已核對 {len(OPTIONAL_WORKSPACE_IDS)} 個工作區",
            "ui.optional_workspaces.repair" if not workspace_ok else "",
        )
    )

    errors = getattr(context, "builtin_mod_errors", {})
    if errors:
        ids = ", ".join(sorted(str(key) for key in errors)[:16])
        items.append(
            _item(
                "builtin.initialization",
                "block",
                "內建 MOD 初始化有錯誤",
                f"失敗項目：{ids}",
                "builtin.integrity.repair",
            )
        )
    else:
        items.append(
            _item(
                "builtin.initialization",
                "pass",
                "內建 MOD 初始化正常",
                "未記錄初始化錯誤",
            )
        )

    snapshot = context.dependencies.peek()
    if snapshot is None:
        items.append(
            _item(
                "dependencies.snapshot",
                "warning",
                "尚未建立依賴快照",
                "請在環境檢查視窗手動重新檢查；自檢不會啟動外部工具。",
                "dependencies.refresh",
            )
        )
    else:
        missing = tuple(item.provider_id for item in snapshot.readiness if not item.ready)
        items.append(
            _item(
                "dependencies.snapshot",
                "warning" if missing else "pass",
                "部分 MOD 依賴尚未就緒" if missing else "依賴快照顯示全部就緒",
                f"未就緒 MOD：{', '.join(missing)}" if missing else "已使用現有快照核對",
                "dependencies.review" if missing else "",
            )
        )

    mode = context.security.mode
    if mode is SecurityMode.BLOCKED:
        items.append(
            _item(
                "security.mode",
                "block",
                "安全狀態已阻擋",
                "啟動安全驗證未通過",
                "security.integrity.repair",
            )
        )
    elif mode is SecurityMode.SAFE_MODE:
        items.append(
            _item(
                "security.mode",
                "warning",
                "目前為 SAFE_MODE 測試／開發版",
                "外部可執行 MOD 不會啟動；這不是正式簽署發行版。",
                "release.signing.required",
            )
        )
    else:
        items.append(
            _item("security.mode", "pass", "安全狀態正常", "正式安全驗證已通過")
        )

    items.append(_release_item(Path(context.paths.application)))
    if len(ui_items) > 16 or len({item.check_id for item in ui_items}) != len(ui_items):
        items.append(
            _item(
                "ui.probe",
                "block",
                "可信 UI 自檢輸入無效",
                "UI 檢查項目重複或超出上限",
                "ui.probe.repair",
            )
        )
    else:
        items.extend(_deidentified_item(item) for item in ui_items)
    return SelfCheckReport(
        1,
        CORE_VERSION,
        BUILD_CHANNEL,
        tuple(items),
        datetime.now(UTC).isoformat(),
        uuid4().hex,
    )
