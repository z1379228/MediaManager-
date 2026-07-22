from core.builtin_mod_catalog import (
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_IDS,
    BUILTIN_MOD_PARENT,
    builtin_default_enabled,
    builtin_mod_ids,
)


def test_builtin_mod_catalog_is_complete_unique_and_typed() -> None:
    assert len(BUILTIN_MOD_CATALOG) == 29
    assert len(BUILTIN_MOD_IDS) == len(BUILTIN_MOD_CATALOG)
    assert not {provider_id for provider_id in BUILTIN_MOD_IDS if provider_id.startswith("ani-gamer")}
    assert builtin_mod_ids("download") == {
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "facebook",
        "mega",
        "direct-http",
    }
    assert len(builtin_mod_ids("discovery")) == 7
    assert len(builtin_mod_ids("feature")) == 16
    assert all(item.purpose and item.control_location for item in BUILTIN_MOD_CATALOG)


def test_catalog_parent_and_default_state_match_runtime_contract() -> None:
    catalog_parents = {
        item.provider_id: item.parent_provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id
    }
    assert catalog_parents == BUILTIN_MOD_PARENT
    assert BUILTIN_MOD_PARENT["media-ad-trim"] == "media-convert"
    assert BUILTIN_MOD_PARENT["p2p-transfer"] == "gopeed-transfer"
    assert builtin_default_enabled("youtube")
    assert builtin_default_enabled("youtube-search")
    assert builtin_default_enabled("facebook")
    assert builtin_default_enabled("mega")
    assert builtin_default_enabled("direct-http")
    assert builtin_default_enabled("instagram")
    assert builtin_default_enabled("instagram-page")
    assert builtin_default_enabled("threads")
    assert builtin_default_enabled("threads-page")
    assert builtin_default_enabled("twitter")
    assert builtin_default_enabled("twitter-page")
    assert builtin_default_enabled("media-convert")
    assert builtin_default_enabled("media-ad-trim")
    assert builtin_default_enabled("gopeed-transfer")
    assert builtin_default_enabled("p2p-transfer")
    assert not builtin_default_enabled("speech-to-text")
    assert not builtin_default_enabled("automation")


def test_optional_workspaces_are_declared_only_by_catalog() -> None:
    assert {
        item.provider_id: item.optional_workspace
        for item in BUILTIN_MOD_CATALOG
        if item.optional_workspace
    } == {
        "facebook": "facebook",
        "mega": "mega",
        "direct-http": "direct-http",
        "instagram": "instagram",
        "threads": "threads",
        "twitter": "twitter",
        "media-convert": "media-convert",
        "gopeed-transfer": "gopeed-transfer",
        "speech-to-text": "speech-to-text",
        "automation": "automation",
    }
