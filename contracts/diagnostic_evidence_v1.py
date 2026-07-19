"""Strict, de-identified metadata contract for manual diagnostic evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any, Literal


DiagnosticComponentV1 = Literal["provider", "runtime", "wer"]

_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "component",
        "observed_at",
        "exit_code",
        "faulting_module",
        "faulting_offset",
        "artifact_sha256",
    }
)
_RUN_ID = re.compile(r"[0-9a-f]{32}")
_UTC_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)
_MODULE = re.compile(r"[a-z0-9][a-z0-9._+-]{0,127}")
_EXIT_CODE = re.compile(r"0x[0-9a-f]{8}")
_OFFSET = re.compile(r"0x[0-9a-f]{1,16}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical_timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and 1 <= len(value) <= 40:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("observed_at must be a valid UTC timestamp") from error
    else:
        raise ValueError("observed_at must be a valid UTC timestamp")
    if parsed.tzinfo is None:
        raise ValueError("observed_at must be a valid UTC timestamp")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_exit_code(value: int | str | None) -> str | None:
    if value is None:
        return None
    if type(value) is int:
        if not -(2**31) <= value <= 0xFFFFFFFF:
            raise ValueError("exit code is outside the 32-bit range")
        normalized = value & 0xFFFFFFFF
    elif isinstance(value, str) and re.fullmatch(r"0[xX][0-9a-fA-F]{1,8}", value):
        normalized = int(value, 16)
    else:
        raise ValueError("exit code must be a 32-bit integer or hexadecimal value")
    return f"0x{normalized:08x}"


def _canonical_offset(value: int | str | None) -> str | None:
    if value is None:
        return None
    if type(value) is int:
        if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("faulting offset is outside the 64-bit range")
        normalized = value
    elif isinstance(value, str) and re.fullmatch(r"0[xX][0-9a-fA-F]{1,16}", value):
        normalized = int(value, 16)
    else:
        raise ValueError("faulting offset must be a hexadecimal value")
    return f"0x{normalized:x}"


def _canonical_module(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("faulting module must be an ASCII basename")
    basename = re.split(r"[\\/]", value.strip())[-1].casefold()
    if not _MODULE.fullmatch(basename) or not basename.isascii():
        raise ValueError("faulting module must be an ASCII basename")
    return basename


@dataclass(frozen=True, slots=True)
class DiagnosticEvidenceV1:
    """Only allow metadata that cannot carry paths, URLs or free-form text."""

    schema_version: int
    run_id: str
    component: DiagnosticComponentV1
    observed_at: str
    exit_code: str | None = None
    faulting_module: str | None = None
    faulting_offset: str | None = None
    artifact_sha256: str | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("diagnostic evidence schema_version must be 1")
        if not isinstance(self.run_id, str) or not _RUN_ID.fullmatch(self.run_id):
            raise ValueError("run_id must be exactly 32 lowercase hexadecimal characters")
        if not isinstance(self.component, str) or self.component not in {
            "provider",
            "runtime",
            "wer",
        }:
            raise ValueError("diagnostic component is invalid")
        if (
            not isinstance(self.observed_at, str)
            or not _UTC_TIMESTAMP.fullmatch(self.observed_at)
        ):
            raise ValueError("observed_at must be a canonical UTC timestamp")
        try:
            datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("observed_at must be a canonical UTC timestamp") from error
        if self.exit_code is not None and (
            not isinstance(self.exit_code, str)
            or not _EXIT_CODE.fullmatch(self.exit_code)
        ):
            raise ValueError("exit code must be canonical unsigned 32-bit hexadecimal")
        if self.faulting_module is not None and (
            not isinstance(self.faulting_module, str)
            or not self.faulting_module.isascii()
            or not _MODULE.fullmatch(self.faulting_module)
        ):
            raise ValueError("faulting module must be an ASCII basename")
        if self.faulting_offset is not None and (
            not isinstance(self.faulting_offset, str)
            or not _OFFSET.fullmatch(self.faulting_offset)
        ):
            raise ValueError("faulting offset must be canonical hexadecimal")
        if self.artifact_sha256 is not None and (
            not isinstance(self.artifact_sha256, str)
            or not _SHA256.fullmatch(self.artifact_sha256)
        ):
            raise ValueError("artifact_sha256 must be lowercase SHA-256")

    @classmethod
    def from_observation(
        cls,
        *,
        run_id: str,
        component: DiagnosticComponentV1,
        observed_at: str | datetime,
        exit_code: int | str | None = None,
        faulting_module: str | None = None,
        faulting_offset: int | str | None = None,
        artifact_sha256: str | None = None,
    ) -> DiagnosticEvidenceV1:
        if artifact_sha256 is not None and not isinstance(artifact_sha256, str):
            raise ValueError("artifact_sha256 must be lowercase SHA-256")
        digest = artifact_sha256.casefold() if artifact_sha256 is not None else None
        return cls(
            1,
            run_id,
            component,
            _canonical_timestamp(observed_at),
            _canonical_exit_code(exit_code),
            _canonical_module(faulting_module),
            _canonical_offset(faulting_offset),
            digest,
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DiagnosticEvidenceV1:
        if not isinstance(value, dict) or set(value) != _FIELDS:
            raise ValueError("diagnostic evidence fields are invalid")
        return cls(
            value["schema_version"],
            value["run_id"],
            value["component"],
            value["observed_at"],
            value["exit_code"],
            value["faulting_module"],
            value["faulting_offset"],
            value["artifact_sha256"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "component": self.component,
            "observed_at": self.observed_at,
            "exit_code": self.exit_code,
            "faulting_module": self.faulting_module,
            "faulting_offset": self.faulting_offset,
            "artifact_sha256": self.artifact_sha256,
        }
