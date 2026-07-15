"""Validated persistent gates for declarative built-in feature MODs."""

from __future__ import annotations

import json
from pathlib import Path
import re


_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_KINDS = frozenset({"site-parent", "site-addon"})


class DeclarativeFeatureGate:
    """A side-effect-free feature flag loaded from a pinned MOD manifest."""

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        kind: str,
        parent_provider_id: str,
    ) -> None:
        self.provider_id = provider_id
        self.display_name = display_name
        self.kind = kind
        self.parent_provider_id = parent_provider_id
        self._enabled = False

    @classmethod
    def from_file(cls, path: Path) -> "DeclarativeFeatureGate":
        resolved = path.resolve()
        if not resolved.is_file() or resolved.is_symlink():
            raise ValueError("declarative feature manifest is missing or unsafe")
        if resolved.stat().st_size > 16_384:
            raise ValueError("declarative feature manifest is too large")
        try:
            document = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise ValueError(
                f"cannot read declarative feature manifest: {error}"
            ) from error
        if not isinstance(document, dict) or set(document) != {
            "schema_version",
            "provider_id",
            "display_name",
            "kind",
            "parent_provider_id",
        }:
            raise ValueError("declarative feature manifest fields are invalid")
        provider_id = document["provider_id"]
        display_name = document["display_name"]
        kind = document["kind"]
        parent_provider_id = document["parent_provider_id"]
        if (
            document["schema_version"] != 1
            or not isinstance(provider_id, str)
            or not _ID.fullmatch(provider_id)
            or not isinstance(display_name, str)
            or not display_name.strip()
            or len(display_name) > 80
            or not isinstance(kind, str)
            or kind not in _KINDS
            or not isinstance(parent_provider_id, str)
            or (
                parent_provider_id
                and not _ID.fullmatch(parent_provider_id)
            )
            or (kind == "site-parent" and parent_provider_id)
            or (kind == "site-addon" and not parent_provider_id)
        ):
            raise ValueError("declarative feature manifest identity is invalid")
        return cls(provider_id, display_name.strip(), kind, parent_provider_id)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def available(self) -> bool:
        return True

    def set_enabled(self, enabled: bool) -> int:
        self._enabled = bool(enabled)
        return 0

    def close(self) -> None:
        self._enabled = False
