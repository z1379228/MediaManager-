from core.builtin_mod_catalog import (
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_IDS,
    BUILTIN_MOD_PARENT,
    builtin_default_enabled,
    builtin_mod_ids,
)


def test_builtin_mod_catalog_is_complete_unique_and_typed() -> None:
    assert len(BUILTIN_MOD_CATALOG) == 32
    assert len(BUILTIN_MOD_IDS) == len(BUILTIN_MOD_CATALOG)
    assert builtin_mod_ids("download") == {
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "facebook",
        "mega",
        "direct-http",
    }
    assert len(builtin_mod_ids("discovery")) == 9
    assert len(builtin_mod_ids("feature")) == 17
    assert all(item.purpose and item.control_location for item in BUILTIN_MOD_CATALOG)


def test_catalog_parent_and_default_state_match_runtime_contract() -> None:
    catalog_parents = {
        item.provider_id: item.parent_provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id
    }
    assert catalog_parents == BUILTIN_MOD_PARENT
    assert BUILTIN_MOD_PARENT["media-ad-trim"] == "media-convert"
    assert builtin_default_enabled("youtube")
    assert builtin_default_enabled("youtube-search")
    assert not builtin_default_enabled("facebook")
    assert not builtin_default_enabled("mega")
    assert not builtin_default_enabled("direct-http")
    assert not builtin_default_enabled("instagram")
    assert not builtin_default_enabled("ani-gamer-offline")
    assert not builtin_default_enabled("instagram-page")
    assert not builtin_default_enabled("threads")
    assert not builtin_default_enabled("threads-page")
    assert not builtin_default_enabled("twitter")
    assert not builtin_default_enabled("twitter-page")
    assert not builtin_default_enabled("media-convert")
    assert not builtin_default_enabled("media-ad-trim")


def test_optional_workspaces_are_declared_only_by_catalog() -> None:
    assert {
        item.provider_id: item.optional_workspace
        for item in BUILTIN_MOD_CATALOG
        if item.optional_workspace
    } == {
        "ani-gamer": "ani-gamer",
        "facebook": "facebook",
        "mega": "mega",
        "direct-http": "direct-http",
        "instagram": "instagram",
        "threads": "threads",
        "twitter": "twitter",
        "media-convert": "media-convert",
        "speech-to-text": "speech-to-text",
        "automation": "automation",
    }
