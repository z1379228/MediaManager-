"""Capability names and matching rules."""

from __future__ import annotations

import re

_CAPABILITY = re.compile(r"^[a-z][a-z0-9_.-]*(?::[a-zA-Z0-9*_.-]+)?$")

DENIED_CAPABILITIES = frozenset({
    "core.modify", "security.disable", "database.raw_access", "storage.anywhere",
    "token.all_accounts", "process.unrestricted", "network.unrestricted",
    "updater.modify", "trust_store.modify",
})


def is_valid_capability(value: str) -> bool:
    return bool(_CAPABILITY.fullmatch(value)) and value not in DENIED_CAPABILITIES


def permits(grant: str, request: str) -> bool:
    if grant == request:
        return True
    return grant.endswith(":*") and request.startswith(grant[:-1])

