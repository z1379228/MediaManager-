"""Explicit plugin loading performed only inside Plugin Host."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from plugin_host.restrictions import confined_path


def load_plugin(root: Path, entry_point: str) -> ModuleType:
    entry = confined_path(root, entry_point)
    spec = importlib.util.spec_from_file_location("mediamanager_plugin", entry)
    if spec is None or spec.loader is None:
        raise ImportError("cannot create plugin module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

