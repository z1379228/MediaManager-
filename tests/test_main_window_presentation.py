from __future__ import annotations

from trusted_ui.main_window import security_presentation


def test_security_presentation_is_explicit_and_fail_closed() -> None:
    assert security_presentation("NORMAL", None) == (
        "已驗證",
        "normal",
        "核心與發布檔案驗證通過",
    )
    assert security_presentation("SAFE_MODE", "NotSigned") == (
        "安全模式",
        "safe",
        "NotSigned",
    )
    assert security_presentation("BLOCKED", "tampered") == (
        "已封鎖",
        "blocked",
        "tampered",
    )
    assert security_presentation("unexpected", None)[1] == "unknown"
