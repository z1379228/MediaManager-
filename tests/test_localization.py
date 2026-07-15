from core.localization import (
    CORE_LOCALES,
    SUPPORTED_LOCALE_CODES,
    normalized_core_locale,
)


def test_core_owns_exactly_four_locales_and_maps_chinese_script_tags() -> None:
    assert tuple(locale.code for locale in CORE_LOCALES) == (
        "zh-TW",
        "zh-CN",
        "en",
        "ja",
    )
    assert SUPPORTED_LOCALE_CODES == {"zh-TW", "zh-CN", "en", "ja"}
    assert normalized_core_locale("zh-Hant") == "zh-TW"
    assert normalized_core_locale("zh-Hans") == "zh-CN"
    assert normalized_core_locale("fr") == "zh-TW"
