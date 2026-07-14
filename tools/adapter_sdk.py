"""Create and offline-validate Search/Download adapter projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.adapters.developer import (
    create_adapter_template,
    validate_adapter_catalog,
    validate_adapter_project,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="MediaManager Adapter SDK")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("adapter_type", choices=("search", "download"))
    create.add_argument("adapter_id")
    create.add_argument("target", type=Path)
    validate = commands.add_parser("validate")
    validate.add_argument("target", type=Path)
    validate.add_argument("--json", action="store_true")
    catalog = commands.add_parser("catalog")
    catalog.add_argument("target", type=Path)
    catalog.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        print(create_adapter_template(args.target, args.adapter_id, args.adapter_type))
        return 0
    report = (
        validate_adapter_catalog(args.target)
        if args.command == "catalog"
        else validate_adapter_project(args.target)
    )
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        if args.command == "catalog":
            print(
                f"{'PASS' if report.valid else 'FAIL'} "
                f"{report.compatible}/{report.checked} compatible"
            )
            for item in report.reports:
                print(
                    f"  {'PASS' if item.valid else 'FAIL'} "
                    f"{item.adapter_id or '(invalid manifest)'}"
                )
        else:
            print(
                f"{'PASS' if report.valid else 'FAIL'} "
                f"{report.adapter_id}".rstrip()
            )
            for warning in report.warnings:
                print(f"WARNING: {warning}")
        for error in report.errors:
            print(f"ERROR: {error}")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
