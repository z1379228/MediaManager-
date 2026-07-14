"""Plugin Host process entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_plugin(
    plugin_id: str, plugin_root: str, entry_point: str, nonce: str
) -> int:
    if len(nonce) < 20:
        return 2
    from plugin_host.runtime import load_plugin

    module = load_plugin(Path(plugin_root), entry_point)
    handler = getattr(module, "handle_request", None)
    if not callable(handler):
        return 3
    print(
        json.dumps(
            {
                "protocol_version": "1.0",
                "plugin_id": plugin_id,
                "runtime_nonce": nonce,
            }
        ),
        flush=True,
    )
    initialized = False
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not initialized:
                if (
                    not isinstance(request, dict)
                    or set(request)
                    != {
                        "type",
                        "protocol_version",
                        "capability_token",
                        "capabilities",
                    }
                    or request["type"] != "runtime.init"
                    or request["protocol_version"] != "1.0"
                    or not isinstance(request["capability_token"], str)
                    or len(request["capability_token"]) < 40
                    or not isinstance(request["capabilities"], list)
                    or not all(
                        isinstance(item, str) for item in request["capabilities"]
                    )
                ):
                    return 4
                initialized = True
                initializer = getattr(module, "initialize", None)
                if callable(initializer):
                    initializer(
                        {
                            "protocol_version": request["protocol_version"],
                            "capability_token": request["capability_token"],
                            "capabilities": tuple(request["capabilities"]),
                        }
                    )
                continue
            print(
                json.dumps(
                    {
                        "request_id": request.get("request_id"),
                        "result": handler(request),
                    }
                ),
                flush=True,
            )
        except Exception as error:
            print(json.dumps({"error": type(error).__name__}), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-id", required=True)
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--entry-point", required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args(argv)
    return run_plugin(
        args.plugin_id,
        args.plugin_root,
        args.entry_point,
        args.nonce,
    )


if __name__ == "__main__":
    raise SystemExit(main())
