from __future__ import annotations

from types import SimpleNamespace

from core.security.safe_mode import SecurityMode
from trusted_ui.plugin_panel import (
    external_mod_health_detail,
    external_mod_health_state,
    external_mod_health_summary,
    external_mod_matches_health_filter,
    external_mod_record_status,
    external_mod_security_notice,
)


def test_external_mod_security_notice_distinguishes_safe_mode_from_builtin() -> None:
    assert external_mod_security_notice(SecurityMode.NORMAL) == ""
    notice = external_mod_security_notice(
        SecurityMode.SAFE_MODE,
        "development build has no signed release manifest",
    )
    assert "外部可執行 MOD" in notice
    assert "內建 MOD 不受此列限制" in notice
    assert "no signed release manifest" in notice


def test_external_mod_record_status_explains_why_it_is_not_enabled() -> None:
    record = SimpleNamespace(enabled=False, pending_action="NONE")
    assert external_mod_record_status(record, SecurityMode.SAFE_MODE) == (
        "安全模式限制（未啟用）"
    )
    assert external_mod_record_status(record, SecurityMode.NORMAL) == (
        "已停用（可啟用）"
    )
    record.pending_action = "REMOVE"
    assert external_mod_record_status(record, SecurityMode.NORMAL) == (
        "已移除（可還原）"
    )


def test_external_mod_health_uses_existing_failure_and_quarantine_state() -> None:
    healthy = SimpleNamespace(failure_count=0, quarantine_reason=None)
    warning = SimpleNamespace(failure_count=2, quarantine_reason=None)
    quarantined = SimpleNamespace(
        failure_count=3,
        quarantine_reason="初始化握手失敗",
    )

    assert external_mod_health_state(healthy) == "healthy"
    assert external_mod_health_state(warning) == "warning"
    assert external_mod_health_state(quarantined) == "quarantined"
    assert external_mod_health_detail(healthy) == "正常"
    assert "2 次" in external_mod_health_detail(warning)
    assert "初始化握手失敗" in external_mod_health_detail(quarantined)
    assert external_mod_health_summary((healthy, warning, quarantined)) == (
        "健康 1 · 需注意 1 · 已隔離 1"
    )
    assert external_mod_matches_health_filter(warning, "attention")
    assert external_mod_matches_health_filter(quarantined, "attention")
    assert not external_mod_matches_health_filter(healthy, "attention")
    assert external_mod_matches_health_filter(quarantined, "quarantined")
