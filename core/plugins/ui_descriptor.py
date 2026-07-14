"""Strict, declarative UI descriptors supplied by installed MODs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.plugins.manager import PluginManager
from core.plugins.registry import PendingAction, PluginRegistry

_ID = re.compile(r"^[a-z][a-z0-9.-]{1,63}$")
_BLOCK_TYPES = frozenset({"heading", "text", "status"})


class PluginUIError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class UIBlock:
    type: str
    text: str


@dataclass(frozen=True, slots=True)
class PluginPage:
    schema_version: int
    page_id: str
    title: str
    blocks: tuple[UIBlock, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PluginPage":
        if set(raw) != {"schema_version", "page_id", "title", "blocks"}:
            raise PluginUIError("UI descriptor fields invalid")
        if raw["schema_version"] != 1 or not _ID.fullmatch(str(raw["page_id"])):
            raise PluginUIError("unsupported UI schema or invalid page id")
        title = raw["title"]
        blocks = raw["blocks"]
        if not isinstance(title, str) or not 1 <= len(title) <= 80:
            raise PluginUIError("UI title is invalid")
        if not isinstance(blocks, list) or len(blocks) > 40:
            raise PluginUIError("UI blocks are invalid")
        parsed: list[UIBlock] = []
        for block in blocks:
            if not isinstance(block, dict) or set(block) != {"type", "text"}:
                raise PluginUIError("UI block fields invalid")
            kind, text = block["type"], block["text"]
            if kind not in _BLOCK_TYPES or not isinstance(text, str):
                raise PluginUIError("UI block type or text is invalid")
            limit = 120 if kind == "heading" else 2000
            if not 1 <= len(text) <= limit or any(ord(char) < 32 and char not in "\n\t" for char in text):
                raise PluginUIError("UI block text is invalid")
            parsed.append(UIBlock(kind, text))
        return cls(1, raw["page_id"], title, tuple(parsed))


class PluginUIService:
    def __init__(self, mod_root: Path, registry: PluginRegistry, plugin_manager: PluginManager) -> None:
        self.mod_root = mod_root.resolve()
        self.registry = registry
        self.plugin_manager = plugin_manager

    def list_pages(self) -> tuple[tuple[str, PluginPage], ...]:
        pages: list[tuple[str, PluginPage]] = []
        for record in self.registry.list_enabled():
            if record.pending_action is not PendingAction.NONE:
                continue
            try:
                page = self.load_page(record.plugin_id)
            except PluginUIError:
                continue
            if page is not None:
                pages.append((record.plugin_id, page))
        return tuple(pages)

    def load_page(self, plugin_id: str) -> PluginPage | None:
        record = self.registry.get(plugin_id)
        if record is None or not record.enabled or record.pending_action is not PendingAction.NONE:
            return None
        errors = self.plugin_manager.verify_directory(root := (self.mod_root / "installed" / plugin_id).resolve(), record)
        if errors:
            raise PluginUIError("installed plugin verification failed: " + "; ".join(errors))
        path = (root / "ui.json").resolve()
        if not root.is_relative_to(self.mod_root) or not path.is_relative_to(root) or path.is_symlink():
            raise PluginUIError("unsafe plugin UI path")
        if not path.is_file():
            return None
        try:
            if path.stat().st_size > 100_000:
                raise PluginUIError("plugin UI descriptor is too large")
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PluginUIError(f"cannot read plugin UI descriptor: {error}") from error
        if not isinstance(raw, dict):
            raise PluginUIError("plugin UI descriptor must be an object")
        return PluginPage.from_dict(raw)

