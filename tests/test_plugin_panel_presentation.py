from __future__ import annotations

from types import SimpleNamespace

from core.security.safe_mode import SecurityMode
from trusted_ui.plugin_panel import (
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
