"""Minimal security UI with a no-dependency fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.bootstrap.bootstrap import AppContext


def run_security_ui(context: "AppContext") -> int:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    except ImportError:
        print(f"MediaManager ready ({context.security.mode})")
        if context.security.reason:
            print(f"Security notice: {context.security.reason}")
        print("Install the 'ui' optional dependency to enable the graphical interface.")
        return 2 if context.security.mode == "BLOCKED" else 0
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.setWindowTitle("MediaManager — Trusted Security UI")
    message = f"Security mode: {context.security.mode}"
    if context.security.reason:
        message += f"\n\n{context.security.reason}"
    window.setCentralWidget(QLabel(message))
    window.resize(560, 220)
    window.show()
    return app.exec()

