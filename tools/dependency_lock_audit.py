"""Verify exact release dependency pins against metadata and the environment."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from importlib import metadata
import json
from pathlib import Path
import re
import tomllib


_PIN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[A-Za-z0-9,._-]+\])?"
    r"==(?P<version>[A-Za-z0-9][A-Za-z0-9.+_-]*)$"
)
_REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass(frozen=True, slots=True)
class DependencyLockReport:
    valid: bool
    checked: int
    errors: tuple[str, ...]


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def audit_dependency_lock(root: Path) -> DependencyLockReport:
    root = root.resolve()
    errors: list[str] = []
    pins: dict[str, tuple[str, str]] = {}
    try:
        lines = (root / "requirements-lock.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        project = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
    except (OSError, KeyError, TypeError, ValueError) as error:
        return DependencyLockReport(False, 0, (str(error),))
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _PIN.fullmatch(line)
        if match is None:
            errors.append(f"lock line {line_number} is not an exact pin")
            continue
        name = match.group("name")
        key = _normalized(name)
        if key in pins:
            errors.append(f"duplicate dependency pin: {name}")
            continue
        pins[key] = (name, match.group("version"))
    declared = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for values in optional.values():
            if isinstance(values, list):
                declared.extend(values)
    for requirement in declared:
        match = _REQUIREMENT_NAME.match(str(requirement))
        if match is None or _normalized(match.group(1)) not in pins:
            errors.append(f"declared dependency is not locked: {requirement}")
    for key, (name, expected) in pins.items():
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            errors.append(f"locked dependency is not installed: {name}")
            continue
        if actual != expected:
            errors.append(
                f"locked dependency version mismatch: {name} {actual} != {expected}"
            )
        if _normalized(name) != key:
            raise AssertionError("normalized dependency key changed")
    return DependencyLockReport(not errors, len(pins), tuple(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = audit_dependency_lock(args.root)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
