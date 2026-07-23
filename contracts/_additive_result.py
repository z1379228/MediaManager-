"""Bounded additive-field policy for explicitly allowlisted result DTOs."""

from __future__ import annotations

import json
import math
import re
from typing import Any


MAX_RESULT_PAYLOAD_BYTES = 1024 * 1024

_MAX_EXTRA_FIELDS = 8
_MAX_EXTRA_KEY_BYTES = 64
_MAX_EXTRA_VALUE_BYTES = 4 * 1024
_MAX_EXTRA_TOTAL_BYTES = 32 * 1024
_MAX_EXTRA_VALUE_DEPTH = 4
_MAX_EXTRA_VALUE_NODES = 64
_EXTRA_KEY = re.compile(
    rf"[a-z][a-z0-9_]{{0,{_MAX_EXTRA_KEY_BYTES - 1}}}\Z",
    re.ASCII,
)
_RESERVED_EXTRA_FIELDS = frozenset(
    {
        "api_version",
        "contract_version",
        "schema",
        "schema_version",
        "version",
    }
)


class AdditiveResultError(ValueError):
    """Raised when an allowlisted result DTO violates the additive policy."""


def validate_additive_result(
    raw: Any,
    *,
    required_fields: frozenset[str],
    max_payload_bytes: int = MAX_RESULT_PAYLOAD_BYTES,
) -> None:
    """Validate required fields plus bounded, ignored JSON-compatible extras."""

    if not isinstance(raw, dict):
        raise AdditiveResultError("result payload must be an object")
    present_fields = frozenset(raw)
    if not required_fields <= present_fields:
        raise AdditiveResultError("result payload is missing required fields")

    payload = _compact_json_bytes(raw)
    if len(payload) > max_payload_bytes:
        raise AdditiveResultError("result payload exceeds the size limit")

    extra_fields = present_fields - required_fields
    if len(extra_fields) > _MAX_EXTRA_FIELDS:
        raise AdditiveResultError("result payload has too many additive fields")
    required_casefold = {field.casefold() for field in required_fields}
    for field in extra_fields:
        if not isinstance(field, str) or _EXTRA_KEY.fullmatch(field) is None:
            raise AdditiveResultError("additive field name is invalid")
        if (
            field.casefold() in required_casefold
            or field.casefold() in _RESERVED_EXTRA_FIELDS
        ):
            raise AdditiveResultError("additive field name is reserved")

    aggregate_bytes = 0
    for field in sorted(extra_fields):
        value = raw[field]
        node_budget = [0]
        _validate_json_value(value, depth=1, node_budget=node_budget)
        encoded_key = _compact_json_bytes(field)
        encoded_value = _compact_json_bytes(value)
        if len(encoded_value) > _MAX_EXTRA_VALUE_BYTES:
            raise AdditiveResultError("additive field value exceeds the size limit")
        aggregate_bytes += len(encoded_key) + len(encoded_value) + 2
    if aggregate_bytes > _MAX_EXTRA_TOTAL_BYTES:
        raise AdditiveResultError("additive fields exceed the aggregate size limit")


def _validate_json_value(
    value: Any,
    *,
    depth: int,
    node_budget: list[int],
) -> None:
    node_budget[0] += 1
    if depth > _MAX_EXTRA_VALUE_DEPTH:
        raise AdditiveResultError("additive field value is too deeply nested")
    if node_budget[0] > _MAX_EXTRA_VALUE_NODES:
        raise AdditiveResultError("additive field value has too many nodes")

    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AdditiveResultError("additive field number must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(
                item,
                depth=depth + 1,
                node_budget=node_budget,
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            node_budget[0] += 1
            if node_budget[0] > _MAX_EXTRA_VALUE_NODES:
                raise AdditiveResultError(
                    "additive field value has too many nodes"
                )
            if not isinstance(key, str):
                raise AdditiveResultError(
                    "additive field object keys must be strings"
                )
            _validate_json_value(
                item,
                depth=depth + 1,
                node_budget=node_budget,
            )
        return
    raise AdditiveResultError("additive field value is not JSON-compatible")


def _compact_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise AdditiveResultError(
            "result payload is not bounded JSON"
        ) from exc
