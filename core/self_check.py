"""Manual, read-only diagnostics for the trusted MediaManager shell."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Literal

from core.builtin_mod_catalog import (
    BUILTIN_MOD_CATALOG,
    OPTIONAL_WORKSPACE_IDS,
    builtin_mod_ids,
)
from core.mod_groups import SITE_MOD_PARENT
from core.security.safe_mode import SecurityMode
from core.version import BUILD_CHANNEL, CORE_VERSION


SelfCheckState = Literal["pass", "warning", "block"]


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
            "summary": {
                "pass": self.pass_count,
                "warning": self.warning_count,
                "block": self.block_count,
            },
            "items": [asdict(item) for item in self.items],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"


def _item(
    check_id: str,
    state: SelfCheckState,
    summary: str,
    detail: str,
    remediation_id: str = "",
) -> SelfCheckItem:
    return SelfCheckItem(check_id, state, summary, detail, remediation_id)


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
            str(error)[:240],
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


def run_self_check(context: object) -> SelfCheckReport:
    """Inspect warm in-memory state only; never refresh dependencies or start tools."""

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
            _registry_item("download", tuple(context.download_providers.statuses())),
            _registry_item("discovery", tuple(context.discovery.statuses())),
            _registry_item("feature", tuple(context.features.statuses())),
        )
    )

    parents = {
        item.provider_id: item.parent_provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id
    }
    routing_ok = parents == SITE_MOD_PARENT
    items.append(
        _item(
            "routing.parent_child",
            "pass" if routing_ok else "block",
            "主 MOD／子 MOD 路由一致" if routing_ok else "主 MOD／子 MOD 路由不一致",
            f"已核對 {len(parents)} 個子 MOD" if routing_ok else "編目與群組契約不同步",
            "routing.catalog.sync" if not routing_ok else "",
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
    return SelfCheckReport(1, CORE_VERSION, BUILD_CHANNEL, tuple(items))
