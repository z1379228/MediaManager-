"""Minimal, defensive JSON settings service."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from core.localization import SUPPORTED_LOCALE_CODES, normalized_core_locale

SUPPORTED_UI_LANGUAGES = SUPPORTED_LOCALE_CODES


@dataclass(slots=True)
class Settings:
    theme: str = "system"
    language: str = "zh-TW"
    ui_scale: str = "standard"
    download_workers: int = 2
    portable_mode: bool = False
    log_level: str = "INFO"
    in_app_download_notifications: bool = True
    system_download_notifications: bool = False


def normalized_download_workers(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        return 2
    return max(1, min(value, 4))


def normalized_language(value: object) -> str:
    return normalized_core_locale(value)


class SettingsService:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = {item.name for item in fields(Settings)}
            return Settings(**{key: value for key, value in raw.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
