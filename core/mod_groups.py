"""Validated parent/child catalog and locale resources for built-in site MODs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

from core.localization import SUPPORTED_LOCALE_CODES, normalized_core_locale


SITE_MOD_CHILDREN = {
    "youtube": (
        "youtube-search",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
    ),
    "bilibili": ("bilibili-search", "bilibili-danmaku"),
    "ani-gamer": (
        "ani-gamer-search",
        "ani-gamer-episodes",
        "ani-gamer-offline",
    ),
    "instagram": ("instagram-page", "instagram-export"),
    "threads": ("threads-page", "threads-export"),
    "twitter": ("twitter-page", "twitter-export"),
    "facebook": (),
    "mega": (),
}
SITE_MOD_PARENT = {
    child: parent
    for parent, children in SITE_MOD_CHILDREN.items()
    for child in children
}

_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_MODULE_ID = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_WORKSPACE_KEYS = frozenset(
    {
        "title",
        "subtitle",
        "enable",
        "url_label",
        "placeholder",
        "initial_preview",
        "wrong_site",
    }
)


class BuiltinModGroupError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BuiltinModModule:
    module_id: str
    provider_id: str
    display_name: str
    purpose: str
    control_location: str
    parent_provider_id: str


@dataclass(frozen=True, slots=True)
class BuiltinModGroup:
    group_id: str
    site_family: str
    parent_provider_id: str
    display_name: str
    locale: str
    workspace: dict[str, str]
    ui: dict[str, str]
    modules: tuple[BuiltinModModule, ...]


def bundled_builtin_mod_root() -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return (bundle_root / "mod" / "builtin").resolve()


def _read_json(path: Path, *, limit: int = 64_000) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise BuiltinModGroupError(f"built-in MOD group file is missing: {path.name}")
    try:
        if path.stat().st_size > limit:
            raise BuiltinModGroupError(f"built-in MOD group file is too large: {path.name}")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise BuiltinModGroupError(
            f"cannot read built-in MOD group file {path.name}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise BuiltinModGroupError(f"built-in MOD group file is not an object: {path.name}")
    return value


def _bounded_text(value: object, field: str, *, limit: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise BuiltinModGroupError(f"built-in MOD group {field} is invalid")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise BuiltinModGroupError(f"built-in MOD group {field} is invalid")
    return value


def load_builtin_mod_group(
    group_id: str,
    *,
    locale: object = "zh-TW",
    builtin_root: Path | None = None,
) -> BuiltinModGroup:
    """Load one pinned built-in site group using the core-selected locale."""

    if group_id not in SITE_MOD_CHILDREN:
        raise BuiltinModGroupError("unknown built-in MOD group")
    selected_locale = normalized_core_locale(locale)
    root = (builtin_root or bundled_builtin_mod_root()).resolve()
    group_root = (root / group_id).resolve()
    if not group_root.is_relative_to(root) or group_root.is_symlink():
        raise BuiltinModGroupError("unsafe built-in MOD group root")
    manifest = _read_json(group_root / "group.json")
    if set(manifest) != {
        "schema_version",
        "group_id",
        "site_family",
        "parent_provider_id",
        "locales",
        "children",
    }:
        raise BuiltinModGroupError("built-in MOD group manifest fields are invalid")
    if (
        manifest["schema_version"] != 1
        or manifest["group_id"] != group_id
        or manifest["site_family"] != group_id
        or manifest["parent_provider_id"] != group_id
        or set(manifest["locales"] if isinstance(manifest["locales"], list) else ())
        != SUPPORTED_LOCALE_CODES
    ):
        raise BuiltinModGroupError("built-in MOD group identity or locales are invalid")
    raw_children = manifest["children"]
    if not isinstance(raw_children, list) or len(raw_children) > 16:
        raise BuiltinModGroupError("built-in MOD group children are invalid")
    child_by_provider: dict[str, str] = {}
    for child in raw_children:
        if not isinstance(child, dict) or set(child) != {"module_id", "provider_id"}:
            raise BuiltinModGroupError("built-in MOD child fields are invalid")
        module_id = child["module_id"]
        provider_id = child["provider_id"]
        if (
            not isinstance(module_id, str)
            or not _MODULE_ID.fullmatch(module_id)
            or not isinstance(provider_id, str)
            or not _ID.fullmatch(provider_id)
            or provider_id in child_by_provider
        ):
            raise BuiltinModGroupError("built-in MOD child identity is invalid")
        child_by_provider[provider_id] = module_id
    if tuple(child_by_provider) != SITE_MOD_CHILDREN[group_id]:
        raise BuiltinModGroupError("built-in MOD child routing does not match the core")

    translation = _read_json(group_root / "locales" / f"{selected_locale}.json")
    required_translation_fields = {
        "schema_version",
        "locale",
        "group_name",
        "workspace",
        "modules",
    }
    if frozenset(translation) not in {
        frozenset(required_translation_fields),
        frozenset({*required_translation_fields, "ui"}),
    }:
        raise BuiltinModGroupError("built-in MOD locale fields are invalid")
    if translation["schema_version"] != 1 or translation["locale"] != selected_locale:
        raise BuiltinModGroupError("built-in MOD locale identity is invalid")
    workspace = translation["workspace"]
    raw_modules = translation["modules"]
    expected_provider_ids = {group_id, *SITE_MOD_CHILDREN[group_id]}
    if (
        not isinstance(workspace, dict)
        or set(workspace) != _WORKSPACE_KEYS
        or not isinstance(raw_modules, dict)
        or set(raw_modules) != expected_provider_ids
    ):
        raise BuiltinModGroupError("built-in MOD locale coverage is incomplete")
    parsed_workspace = {
        key: _bounded_text(value, f"workspace.{key}", limit=1000)
        for key, value in workspace.items()
    }
    raw_ui = translation.get("ui", {})
    if (
        not isinstance(raw_ui, dict)
        or len(raw_ui) > 96
        or not all(
            isinstance(key, str)
            and re.fullmatch(r"[a-z][a-z0-9_]{1,63}", key)
            for key in raw_ui
        )
    ):
        raise BuiltinModGroupError("built-in MOD localized UI strings are invalid")
    parsed_ui = {
        key: _bounded_text(value, f"ui.{key}", limit=1000)
        for key, value in raw_ui.items()
    }
    modules: list[BuiltinModModule] = []
    for provider_id in (group_id, *SITE_MOD_CHILDREN[group_id]):
        content = raw_modules[provider_id]
        if not isinstance(content, dict) or set(content) != {
            "name",
            "purpose",
            "control_location",
        }:
            raise BuiltinModGroupError("built-in MOD localized module is invalid")
        modules.append(
            BuiltinModModule(
                "download" if provider_id == group_id else child_by_provider[provider_id],
                provider_id,
                _bounded_text(content["name"], f"modules.{provider_id}.name", limit=80),
                _bounded_text(
                    content["purpose"], f"modules.{provider_id}.purpose"
                ),
                _bounded_text(
                    content["control_location"],
                    f"modules.{provider_id}.control_location",
                ),
                "" if provider_id == group_id else group_id,
            )
        )
    return BuiltinModGroup(
        group_id,
        group_id,
        group_id,
        _bounded_text(translation["group_name"], "group_name", limit=80),
        selected_locale,
        parsed_workspace,
        parsed_ui,
        tuple(modules),
    )


def load_builtin_mod_groups(locale: object = "zh-TW") -> tuple[BuiltinModGroup, ...]:
    return tuple(
        load_builtin_mod_group(group_id, locale=locale)
        for group_id in SITE_MOD_CHILDREN
    )
