"""Generate a deterministic dependency and licence inventory for a release."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path

from core.version import CORE_VERSION


def build_inventory() -> dict[str, object]:
    components = []
    for name in ("cryptography", "PySide6", "yt-dlp", "yt-dlp-ejs"):
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            components.append({"name": name, "status": "missing"})
            continue
        components.append(
            {
                "name": distribution.metadata.get("Name", name),
                "version": distribution.version,
                "license": distribution.metadata.get("License-Expression")
                or distribution.metadata.get("License")
                or "UNKNOWN",
                "status": "installed",
            }
        )
    return {
        "schema": "mediamanager-release-inventory-v1",
        "core_version": CORE_VERSION,
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_inventory(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
