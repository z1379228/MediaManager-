"""Create and validate third-party MOD projects without loading their code."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.plugins.developer import (
    ModValidationReport,
    create_mod_template,
    validate_mod_manifest,
    validate_mod_package,
)


def _print_report(report: ModValidationReport) -> int:
    label = f" {report.plugin_id} {report.plugin_version}" if report.plugin_id else ""
    print(f"{'PASS' if report.valid else 'FAIL'}{label}")
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    return 0 if report.valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="MediaManager 3.0 MOD SDK")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create an unsigned schema-v2 template")
    create.add_argument("plugin_id")
    create.add_argument("target", type=Path)
    validate = commands.add_parser("validate", help="validate without installing")
    validate.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        print(create_mod_template(args.target, args.plugin_id))
        return 0
    report = (
        validate_mod_package(args.path)
        if args.path.suffix.lower() == ".modpkg"
        else validate_mod_manifest(args.path)
    )
    return _print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
