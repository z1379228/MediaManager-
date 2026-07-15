"""Trusted core locale catalog shared by the shell and declarative MOD UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreLocale:
    code: str
    language_tag: str
    display_name: str


CORE_LOCALES = (
    CoreLocale("zh-TW", "zh-Hant", "繁體中文"),
    CoreLocale("zh-CN", "zh-Hans", "简体中文"),
    CoreLocale("en", "en", "English"),
    CoreLocale("ja", "ja", "日本語"),
)
SUPPORTED_LOCALE_CODES = frozenset(locale.code for locale in CORE_LOCALES)
_LOCALE_ALIASES = {
    locale.language_tag: locale.code
    for locale in CORE_LOCALES
    if locale.language_tag != locale.code
}


def normalized_core_locale(value: object) -> str:
    """Normalize the only four supported core locales to persisted codes."""

    if isinstance(value, str):
        if value in SUPPORTED_LOCALE_CODES:
            return value
        if value in _LOCALE_ALIASES:
            return _LOCALE_ALIASES[value]
    return "zh-TW"
