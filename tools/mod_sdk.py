"""Create and validate third-party MOD projects without loading their code."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.plugins.developer import (
    ModValidationReport,
    create_mod_template,
    create_site_mod_template,
    validate_mod_manifest,
    validate_mod_package,
    validate_site_mod_project,
)
from core.version import CORE_VERSION


def _print_report(report: ModValidationReport) -> int:
    label = f" {report.plugin_id} {report.plugin_version}" if report.plugin_id else ""
    print(f"{'PASS' if report.valid else 'FAIL'}{label}")
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    return 0 if report.valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=f"MediaManager {CORE_VERSION} MOD SDK")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create an unsigned schema-v2 template")
    create.add_argument("plugin_id")
    create.add_argument("target", type=Path)
    create_site = commands.add_parser(
        "create-site", help="create a parent/child website MOD family"
    )
    create_site.add_argument("parent_id")
    create_site.add_argument("target", type=Path)
    create_site.add_argument(
        "--host",
        action="append",
        default=[],
        help="canonical DNS host owned by this site family (repeatable)",
    )
    validate = commands.add_parser("validate", help="validate without installing")
    validate.add_argument("path", type=Path)
    validate_site = commands.add_parser(
        "validate-site", help="validate a parent/child website MOD project"
    )
    validate_site.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        print(create_mod_template(args.target, args.plugin_id))
        return 0
    if args.command == "create-site":
        hosts = tuple(args.host) or ("replace-with-owned-host.invalid",)
        print(create_site_mod_template(args.target, args.parent_id, hosts=hosts))
        return 0
    if args.command == "validate-site":
        return _print_report(validate_site_mod_project(args.path))
    report = (
        validate_mod_package(args.path)
        if args.path.suffix.lower() == ".modpkg"
        else validate_mod_manifest(args.path)
    )
    return _print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
