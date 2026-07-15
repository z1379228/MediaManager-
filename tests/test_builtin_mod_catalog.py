from core.builtin_mod_catalog import (
    BUILTIN_MOD_CATALOG,
    BUILTIN_MOD_IDS,
    builtin_default_enabled,
    builtin_mod_ids,
)
from core.mod_groups import SITE_MOD_PARENT


def test_builtin_mod_catalog_is_complete_unique_and_typed() -> None:
    assert len(BUILTIN_MOD_CATALOG) == 19
    assert len(BUILTIN_MOD_IDS) == len(BUILTIN_MOD_CATALOG)
    assert builtin_mod_ids("download") == {
        "youtube",
        "generic-ytdlp",
        "bilibili",
        "facebook",
        "mega",
    }
    assert len(builtin_mod_ids("discovery")) == 9
    assert len(builtin_mod_ids("feature")) == 5
    assert all(item.purpose and item.control_location for item in BUILTIN_MOD_CATALOG)


def test_catalog_parent_and_default_state_match_runtime_contract() -> None:
    catalog_parents = {
        item.provider_id: item.parent_provider_id
        for item in BUILTIN_MOD_CATALOG
        if item.parent_provider_id
    }
    assert catalog_parents == SITE_MOD_PARENT
    assert builtin_default_enabled("youtube")
    assert builtin_default_enabled("youtube-search")
    assert not builtin_default_enabled("facebook")
    assert not builtin_default_enabled("mega")
    assert not builtin_default_enabled("media-convert")


def test_optional_workspaces_are_declared_only_by_catalog() -> None:
    assert {
        item.provider_id: item.optional_workspace
        for item in BUILTIN_MOD_CATALOG
        if item.optional_workspace
    } == {
        "ani-gamer": "ani-gamer",
        "facebook": "facebook",
        "mega": "mega",
        "media-convert": "media-convert",
        "speech-to-text": "speech-to-text",
        "automation": "automation",
    }
