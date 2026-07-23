"""Bounded, atomic per-domain download profiles for the trusted UI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from contracts.media_options_v1 import validate_media_options_v1


PROFILE_SCHEMA = 1
PROFILE_SITES = frozenset({"youtube", "bilibili"})
_MAX_PROFILE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class DomainDownloadProfile:
    format_preset: str = "best"
    container_preset: str = "auto"
    subtitle_mode: str = "none"
    subtitle_languages: tuple[str, ...] = ()
    priority: int = 0
    output_dir: str = ""
    embed_metadata: bool = False
    embed_thumbnail: bool = False
    embed_chapters: bool = False
    network_retry: str = "standard"

    def __post_init__(self) -> None:
        validate_media_options_v1(
            self.format_preset,
            self.subtitle_mode,
            self.subtitle_languages,
            "none",
            self.container_preset,
        )
        if not -10 <= self.priority <= 10:
            raise ValueError("profile priority is invalid")
        if not isinstance(self.output_dir, str) or len(self.output_dir) > 1000:
            raise ValueError("profile output directory is invalid")
        if not all(
            isinstance(value, bool)
            for value in (
                self.embed_metadata,
                self.embed_thumbnail,
                self.embed_chapters,
            )
        ):
            raise ValueError("profile post-processing options are invalid")
        if self.network_retry not in {"standard", "resilient"}:
            raise ValueError("profile network retry mode is invalid")

    @classmethod
    def from_dict(cls, raw: object) -> DomainDownloadProfile:
        if not isinstance(raw, dict):
            raise ValueError("download profile is invalid")
        allowed = {
            "format_preset",
            "container_preset",
            "subtitle_mode",
            "subtitle_languages",
            "priority",
            "output_dir",
            "embed_metadata",
            "embed_thumbnail",
            "embed_chapters",
            "network_retry",
        }
        if set(raw) - allowed:
            raise ValueError("download profile fields are invalid")
        languages = raw.get("subtitle_languages", [])
        if not isinstance(languages, list):
            raise ValueError("download profile subtitle languages are invalid")
        return cls(
            format_preset=str(raw.get("format_preset", "best")),
            container_preset=str(raw.get("container_preset", "auto")),
            subtitle_mode=str(raw.get("subtitle_mode", "none")),
            subtitle_languages=tuple(languages),
            priority=int(raw.get("priority", 0)),
            output_dir=str(raw.get("output_dir", "")),
            embed_metadata=raw.get("embed_metadata", False),
            embed_thumbnail=raw.get("embed_thumbnail", False),
            embed_chapters=raw.get("embed_chapters", False),
            network_retry=str(raw.get("network_retry", "standard")),
        )

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["subtitle_languages"] = list(self.subtitle_languages)
        return value


class DownloadProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, site_family: str) -> DomainDownloadProfile | None:
        self._validate_site(site_family)
        document = self._read_document()
        raw = document["profiles"].get(site_family)
        if raw is None:
            return None
        try:
            return DomainDownloadProfile.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, site_family: str, profile: DomainDownloadProfile) -> None:
        self._validate_site(site_family)
        if not isinstance(profile, DomainDownloadProfile):
            raise TypeError("download profile type is invalid")
        document = self._read_document()
        document["profiles"][site_family] = profile.to_dict()
        payload = json.dumps(document, ensure_ascii=False, indent=2)
        if len(payload.encode("utf-8")) > _MAX_PROFILE_BYTES:
            raise ValueError("download profile file is too large")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _validate_site(site_family: str) -> None:
        if site_family not in PROFILE_SITES:
            raise ValueError("download profile site is invalid")

    def _read_document(self) -> dict[str, object]:
        default: dict[str, object] = {"schema": PROFILE_SCHEMA, "profiles": {}}
        if not self.path.exists():
            return default
        try:
            if self.path.is_symlink() or self.path.stat().st_size > _MAX_PROFILE_BYTES:
                return default
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != PROFILE_SCHEMA
            or not isinstance(raw.get("profiles"), dict)
            or len(raw["profiles"]) > len(PROFILE_SITES)
        ):
            return default
        profiles = {
            key: value
            for key, value in raw["profiles"].items()
            if key in PROFILE_SITES
        }
        return {"schema": PROFILE_SCHEMA, "profiles": profiles}
