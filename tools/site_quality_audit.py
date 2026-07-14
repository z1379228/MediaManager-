"""Run the offline built-in provider quality audit."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from core.downloads.site_quality import audit_builtin_site_quality


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = audit_builtin_site_quality(args.root)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
