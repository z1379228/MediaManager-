from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any, Callable

import pytest

from contracts.discovery_v1 import DiscoveryContractError, DiscoveryItemV1
from contracts.history_v1 import (
    HistoryContractError,
    HistoryEventV1,
    HistoryPreferencesV1,
)
from contracts.provider_failure_v1 import ProviderFailureV1
from contracts.recovery_v1 import (
    RecoveryCandidateV1,
    RecoveryContractError,
    RecoveryPlanV1,
)
from core.downloads.errors import classify_provider_failure


Parser = Callable[[dict[str, Any]], object]
PayloadFactory = Callable[[], dict[str, Any]]


def _discovery_payload() -> dict[str, Any]:
    return {
        "video_id": "abc",
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "Example",
        "artist": "Artist",
        "duration": 120,
        "language": "zh-TW",
        "category": "music",
        "thumbnail_url": "https://example.com/thumb.jpg",
    }


def _history_event_payload() -> dict[str, Any]:
    return {
        "event_type": "search",
        "query": "example",
        "timestamp": "2026-07-19T00:00:00+00:00",
        "item": None,
    }


def _history_preferences_payload() -> dict[str, Any]:
    return {
        "total_searches": 1,
        "total_selections": 1,
        "content_types": {"music": 1},
        "languages": {"zh-TW": 1},
        "artists": {"Artist": 1},
        "categories": {"music": 1},
    }


def _recovery_plan_payload() -> dict[str, Any]:
    return {
        "primary_query": "Example Song",
        "fallback_queries": ["Artist Example Song"],
    }


def _recovery_candidate_payload() -> dict[str, Any]:
    return {
        "item": _discovery_payload(),
        "score": 85,
        "reasons": ["title", "artist"],
    }


def _provider_failure_payload() -> dict[str, Any]:
    return {
        "code": "RATE_LIMITED",
        "message": "Busy",
        "retryable": True,
    }


CONTRACT_CASES = (
    pytest.param(
        DiscoveryItemV1.from_dict,
        _discovery_payload,
        "video_id",
        DiscoveryContractError,
        id="discovery-item",
    ),
    pytest.param(
        HistoryEventV1.from_dict,
        _history_event_payload,
        "event_type",
        HistoryContractError,
        id="history-event",
    ),
    pytest.param(
        HistoryPreferencesV1.from_dict,
        _history_preferences_payload,
        "total_searches",
        HistoryContractError,
        id="history-preferences",
    ),
    pytest.param(
        RecoveryPlanV1.from_dict,
        _recovery_plan_payload,
        "primary_query",
        RecoveryContractError,
        id="recovery-plan",
    ),
    pytest.param(
        RecoveryCandidateV1.from_dict,
        _recovery_candidate_payload,
        "score",
        RecoveryContractError,
        id="recovery-candidate",
    ),
    pytest.param(
        ProviderFailureV1.from_dict,
        _provider_failure_payload,
        "code",
        ValueError,
        id="provider-failure",
    ),
)


@pytest.mark.parametrize(
    ("parser", "payload_factory", "required_key", "error_type"),
    CONTRACT_CASES,
)
def test_result_contract_accepts_and_drops_bounded_additive_field(
    parser: Parser,
    payload_factory: PayloadFactory,
    required_key: str,
    error_type: type[ValueError],
) -> None:
    del required_key, error_type
    payload = payload_factory()
    baseline = parser(deepcopy(payload))
    payload["future_label"] = "supported"

    parsed = parser(payload)

    assert parsed == baseline
    assert "future_label" not in asdict(parsed)


@pytest.mark.parametrize(
    ("parser", "payload_factory", "required_key", "error_type"),
    CONTRACT_CASES,
)
def test_result_contract_still_rejects_missing_required_field(
    parser: Parser,
    payload_factory: PayloadFactory,
    required_key: str,
    error_type: type[ValueError],
) -> None:
    payload = payload_factory()
    payload.pop(required_key)

    with pytest.raises(error_type):
        parser(payload)


@pytest.mark.parametrize(
    ("parser", "payload_factory", "required_key", "error_type"),
    CONTRACT_CASES,
)
def test_result_contract_rejects_too_many_additive_fields(
    parser: Parser,
    payload_factory: PayloadFactory,
    required_key: str,
    error_type: type[ValueError],
) -> None:
    del required_key
    payload = payload_factory()
    payload.update({f"future_{index}": index for index in range(9)})

    with pytest.raises(error_type):
        parser(payload)


@pytest.mark.parametrize(
    ("parser", "payload_factory", "required_key", "error_type"),
    CONTRACT_CASES,
)
def test_result_contract_rejects_unknown_schema_marker(
    parser: Parser,
    payload_factory: PayloadFactory,
    required_key: str,
    error_type: type[ValueError],
) -> None:
    del required_key
    payload = payload_factory()
    payload["schema_version"] = 2

    with pytest.raises(error_type):
        parser(payload)


def test_additive_field_accepts_bounded_json_and_is_not_persisted() -> None:
    payload = _discovery_payload()
    payload["future_metadata"] = {
        "label": "supported",
        "tags": ["catalog", 2, True, None],
    }

    parsed = DiscoveryItemV1.from_dict(payload)

    assert parsed == DiscoveryItemV1.from_dict(_discovery_payload())
    assert "future_metadata" not in asdict(parsed)


@pytest.mark.parametrize(
    "key",
    (
        "_private",
        "FutureField",
        "a" * 65,
        42,
    ),
)
def test_additive_field_rejects_invalid_key(key: object) -> None:
    payload = _discovery_payload()
    payload[key] = "value"

    with pytest.raises(DiscoveryContractError):
        DiscoveryItemV1.from_dict(payload)


@pytest.mark.parametrize(
    "value",
    (
        float("nan"),
        {1: "non-string-key"},
        [[[[["too-deep"]]]]],
        list(range(64)),
        "x" * 4097,
    ),
)
def test_additive_field_rejects_unbounded_or_non_json_value(value: object) -> None:
    payload = _discovery_payload()
    payload["future_value"] = value

    with pytest.raises(DiscoveryContractError):
        DiscoveryItemV1.from_dict(payload)


def test_additive_fields_reject_aggregate_larger_than_32_kib() -> None:
    payload = _discovery_payload()
    payload.update({f"future_{index}": "x" * 4090 for index in range(8)})

    with pytest.raises(DiscoveryContractError):
        DiscoveryItemV1.from_dict(payload)


def test_result_contract_rejects_payload_larger_than_one_mib() -> None:
    payload = _discovery_payload()
    payload["video_id"] = "x" * (1024 * 1024)

    with pytest.raises(DiscoveryContractError):
        DiscoveryItemV1.from_dict(payload)


@pytest.mark.parametrize(
    ("parser", "payload_factory"),
    (
        pytest.param(
            HistoryEventV1.from_dict,
            lambda: {
                "event_type": "selection",
                "query": "example",
                "timestamp": "2026-07-19T00:00:00+00:00",
                "item": {**_discovery_payload(), "future_label": "supported"},
            },
            id="history-selection",
        ),
        pytest.param(
            RecoveryCandidateV1.from_dict,
            lambda: {
                **_recovery_candidate_payload(),
                "item": {**_discovery_payload(), "future_label": "supported"},
            },
            id="recovery-candidate",
        ),
    ),
)
def test_nested_discovery_result_accepts_bounded_additive_field(
    parser: Parser,
    payload_factory: PayloadFactory,
) -> None:
    payload = payload_factory()

    parsed = parser(payload)

    assert parsed.item == DiscoveryItemV1.from_dict(_discovery_payload())


def test_structured_provider_failure_keeps_retry_semantics_with_additive_field(
) -> None:
    payload = _provider_failure_payload()
    payload["retry_after_seconds"] = 30

    failure = classify_provider_failure(payload)

    assert failure.code.value == "RATE_LIMITED"
    assert failure.retryable is True
    assert failure.message == "Busy"
