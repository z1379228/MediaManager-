"""MediaManager application entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_FROZEN_CLI_OUTPUT_FLAGS = frozenset(
    {"--version", "--verify-only", "--headless", "--ui-runtime-check"}
)


def _create_bootstrap(*, portable: bool) -> object:
    from core.bootstrap.bootstrap import Bootstrap

    return Bootstrap(portable=portable)


def _run_graphical_shell(
    context: object,
    *,
    start_minimized: bool,
    initial_prefill: dict[str, str] | None,
) -> int:
    from trusted_ui.main_window import run_main_window

    return run_main_window(
        context,
        start_minimized=start_minimized,
        initial_prefill=initial_prefill,
    )


def _verify_ui_runtime() -> int:
    """Load Qt's widget and platform runtime without starting the full UI."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()
    created = application is None
    if application is None:
        application = QApplication([])
    QCoreApplication.processEvents()
    if created:
        application.quit()
    return 0


def build_parser() -> argparse.ArgumentParser:
    from core.version import display_version

    parser = argparse.ArgumentParser(prog="MediaManager")
    parser.add_argument(
        "--version", action="version", version=f"MediaManager {display_version()}"
    )
    parser.add_argument("--portable", action="store_true", help="store runtime data beside the application")
    parser.add_argument("--headless", action="store_true", help="do not start the graphical security UI")
    parser.add_argument(
        "--start-minimized",
        action="store_true",
        help="start in background idle mode when the system tray is available",
    )
    parser.add_argument(
        "--browser-handoff",
        metavar="URL_OR_URI",
        help=(
            "open a supported media URL in the trusted download setup; "
            "also accepts mediamanager://add handoff URIs"
        ),
    )
    parser.add_argument("--verify-only", action="store_true", help="verify core integrity and exit")
    parser.add_argument("--ui-runtime-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--provider-host", help=argparse.SUPPRESS)
    parser.add_argument("--provider-root", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-host", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-id", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-root", help=argparse.SUPPRESS)
    parser.add_argument("--entry-point", help=argparse.SUPPRESS)
    parser.add_argument("--nonce", help=argparse.SUPPRESS)
    return parser


def _run(raw_argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(raw_argv)
    if args.ui_runtime_check:
        return _verify_ui_runtime()
    initial_prefill: dict[str, str] | None = None
    if args.browser_handoff is not None:
        if args.headless or args.plugin_host or args.provider_host:
            parser.error("--browser-handoff requires the graphical application")
        from core.browser_handoff import parse_browser_handoff

        try:
            initial_prefill = parse_browser_handoff(
                args.browser_handoff
            ).to_payload()
        except ValueError as error:
            parser.error(str(error))
    if args.plugin_host:
        if args.provider_host or args.provider_root or not all(
            (args.plugin_id, args.plugin_root, args.entry_point, args.nonce)
        ):
            return 2
        from plugin_host.stdio import restore_frozen_host_stdio

        if not restore_frozen_host_stdio():
            return 2
        from plugin_host.main import run_plugin

        return run_plugin(
            args.plugin_id,
            args.plugin_root,
            args.entry_point,
            args.nonce,
        )
    if args.provider_host:
        if not args.provider_root:
            return 2
        from plugin_host.stdio import restore_frozen_host_stdio

        if not restore_frozen_host_stdio():
            return 2
        from plugin_host.external_provider import run_provider

        application_root = Path(
            sys.executable if getattr(sys, "frozen", False) else __file__
        ).resolve().parent
        return run_provider(
            Path(args.provider_host),
            application_root,
            provider_root=Path(args.provider_root),
        )
    bootstrap = _create_bootstrap(portable=args.portable)
    if args.verify_only:
        security = bootstrap.verify_only()
        print(f"MediaManager security mode: {security.mode}")
        if security.reason:
            print(security.reason)
        return 2 if security.mode == "BLOCKED" else 0
    context = bootstrap.initialize()
    try:
        if args.headless:
            print(f"MediaManager ready ({context.security.mode})")
            return 2 if context.security.mode == "BLOCKED" else 0
        return _run_graphical_shell(
            context,
            start_minimized=(args.start_minimized and initial_prefill is None),
            initial_prefill=initial_prefill,
        )
    finally:
        context.lifecycle.shutdown()


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    cli_output = bool(_FROZEN_CLI_OUTPUT_FLAGS.intersection(raw_argv))
    if not cli_output:
        return _run(raw_argv)
    from plugin_host.stdio import (
        close_frozen_cli_stdio,
        restore_frozen_cli_stdio,
    )

    restore_frozen_cli_stdio()
    try:
        return _run(raw_argv)
    finally:
        close_frozen_cli_stdio()


def _script_entry(argv: list[str] | None = None) -> None:
    """Exit the frozen windowed CLI path without interpreter shutdown stalls."""

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    frozen_cli = bool(
        getattr(sys, "frozen", False)
        and _FROZEN_CLI_OUTPUT_FLAGS.intersection(raw_argv)
    )
    try:
        exit_code = main(raw_argv)
    except SystemExit as exc:
        if not frozen_cli:
            raise
        exit_code = exc.code
    if not isinstance(exit_code, int):
        exit_code = 1 if exit_code else 0
    if frozen_cli:
        os._exit(exit_code)
        return
    raise SystemExit(exit_code)


if __name__ == "__main__":
    _script_entry()




