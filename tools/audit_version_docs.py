"""Audit canonical source versions against current documentation."""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Sequence
import tomllib


CURRENT_DOCUMENTS = (Path("README.md"), Path("docs/README.md"))
_RELEASE_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_CURRENT_VERSION_DECLARATION = re.compile(
    r"^[ \t]*(?:-[ \t]+)?目前來源版本為開發版 "
    r"(?P<generation>[0-9]+\.[0-9]+)"
    r"（核心相容版本 (?P<version>[0-9]+\.[0-9]+\.[0-9]+)）",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class VersionDocumentationReport:
    valid: bool
    checked: int
    core_version: str | None
    project_version: str | None
    development_generation: str | None
    errors: tuple[str, ...]


def _literal_assignments(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = value.value
    return values


def audit_version_docs(root: Path) -> VersionDocumentationReport:
    root = root.resolve()
    errors: list[str] = []
    checked = 0
    core_version: str | None = None
    project_version: str | None = None
    development_generation: str | None = None

    try:
        assignments = _literal_assignments(root / "core/version.py")
        core_version = assignments["CORE_VERSION"]
        development_generation = assignments["DEVELOPMENT_GENERATION"]
        checked += 1
    except (OSError, UnicodeError, SyntaxError, KeyError) as error:
        errors.append(f"core/version.py cannot provide canonical versions: {error}")

    try:
        project = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        project_version = str(project["version"])
        checked += 1
    except (OSError, KeyError, TypeError, ValueError) as error:
        errors.append(f"pyproject.toml cannot provide project.version: {error}")

    if core_version is not None and not _RELEASE_VERSION.fullmatch(core_version):
        errors.append("CORE_VERSION must use major.minor.patch")
    if project_version is not None and project_version != core_version:
        errors.append(
            "canonical version mismatch: "
            f"core/version.py {core_version!r} != pyproject.toml {project_version!r}"
        )
    if core_version is not None and development_generation is not None:
        expected_generation = core_version.rsplit(".", 1)[0]
        if development_generation != expected_generation:
            errors.append(
                "development generation mismatch: "
                f"{development_generation!r} != {expected_generation!r}"
            )

    for relative_path in CURRENT_DOCUMENTS:
        try:
            text = (root / relative_path).read_text(encoding="utf-8")
            checked += 1
        except (OSError, UnicodeError) as error:
            errors.append(f"{relative_path.as_posix()} cannot be read: {error}")
            continue
        declarations = list(_CURRENT_VERSION_DECLARATION.finditer(text))
        if len(declarations) != 1:
            errors.append(
                f"{relative_path.as_posix()} must contain exactly one current source "
                f"version declaration; found {len(declarations)}"
            )
            continue
        declaration = declarations[0]
        documented_generation = declaration.group("generation")
        documented_version = declaration.group("version")
        if documented_generation != development_generation:
            errors.append(
                f"{relative_path.as_posix()} development version mismatch: "
                f"{documented_generation!r} != {development_generation!r}"
            )
        if documented_version != core_version:
            errors.append(
                f"{relative_path.as_posix()} core version mismatch: "
                f"{documented_version!r} != {core_version!r}"
            )

    return VersionDocumentationReport(
        valid=not errors,
        checked=checked,
        core_version=core_version,
        project_version=project_version,
        development_generation=development_generation,
        errors=tuple(errors),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    report = audit_version_docs(args.root)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
