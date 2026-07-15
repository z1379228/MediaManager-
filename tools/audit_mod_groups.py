"""Audit built-in website parent/child, locale, and provider boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.localization import SUPPORTED_LOCALE_CODES
from core.builtin_mod_catalog import builtin_mod_descriptor
from core.mod_groups import (
    SITE_MOD_CHILDREN,
    BuiltinModGroupError,
    load_builtin_mod_group,
)


def audit_mod_groups(root: Path) -> tuple[str, ...]:
    builtin_root = (root.resolve() / "mod" / "builtin").resolve()
    errors: list[str] = []
    assigned: set[str] = set()
    for parent_id, child_ids in SITE_MOD_CHILDREN.items():
        try:
            groups = tuple(
                load_builtin_mod_group(
                    parent_id,
                    locale=locale,
                    builtin_root=builtin_root,
                )
                for locale in sorted(SUPPORTED_LOCALE_CODES)
            )
        except BuiltinModGroupError as error:
            errors.append(f"{parent_id}: {error}")
            continue
        expected = {parent_id, *child_ids}
        actual = {module.provider_id for module in groups[0].modules}
        if actual != expected:
            errors.append(f"{parent_id}: provider coverage mismatch")
        overlap = assigned & actual
        if overlap:
            errors.append(
                f"{parent_id}: providers assigned to multiple site groups: "
                + ", ".join(sorted(overlap))
            )
        assigned.update(actual)
        for provider_id in expected:
            manifest_name = (
                "feature.json"
                if builtin_mod_descriptor(provider_id).kind == "feature"
                else "provider.json"
            )
            manifest_path = builtin_root / provider_id / manifest_name
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError) as error:
                errors.append(f"{provider_id}: cannot read {manifest_name}: {error}")
                continue
            if not isinstance(manifest, dict) or manifest.get("provider_id") != provider_id:
                errors.append(f"{provider_id}: provider identity mismatch")
                continue
            permissions = manifest.get("permissions", [])
            network_permissions = {
                value
                for value in permissions
                if isinstance(value, str) and value.startswith("network.")
            }
            expected_network = f"network.{parent_id}"
            if network_permissions and network_permissions != {expected_network}:
                errors.append(
                    f"{provider_id}: cross-site network permissions "
                    + ", ".join(sorted(network_permissions))
                )
            capability = manifest.get("search_capability")
            if isinstance(capability, dict) and capability.get("sites") != [parent_id]:
                errors.append(f"{provider_id}: search site family mismatch")
    return tuple(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = audit_mod_groups(args.root)
    result = {
        "ok": not errors,
        "groups": len(SITE_MOD_CHILDREN),
        "locales": len(SUPPORTED_LOCALE_CODES),
        "errors": list(errors),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif errors:
        print("Built-in MOD group audit: FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print(
            "Built-in MOD group audit: PASS "
            f"({result['groups']} groups, {result['locales']} locales)"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
