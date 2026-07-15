"""MediaManager application entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core.bootstrap.bootstrap import Bootstrap
from core.version import display_version
from trusted_ui.main_window import run_main_window


_FROZEN_CLI_OUTPUT_FLAGS = frozenset({"--version", "--verify-only", "--headless"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="MediaManager")
    parser.add_argument(
        "--version", action="version", version=f"MediaManager {display_version()}"
    )
    parser.add_argument("--portable", action="store_true", help="store runtime data beside the application")
    parser.add_argument("--headless", action="store_true", help="do not start the graphical security UI")
    parser.add_argument("--verify-only", action="store_true", help="verify core integrity and exit")
    parser.add_argument("--provider-host", help=argparse.SUPPRESS)
    parser.add_argument("--provider-root", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-host", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-id", help=argparse.SUPPRESS)
    parser.add_argument("--plugin-root", help=argparse.SUPPRESS)
    parser.add_argument("--entry-point", help=argparse.SUPPRESS)
    parser.add_argument("--nonce", help=argparse.SUPPRESS)
    return parser


def _run(raw_argv: list[str]) -> int:
    args = build_parser().parse_args(raw_argv)
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
    bootstrap = Bootstrap(portable=args.portable)
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
        return run_main_window(context)
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




