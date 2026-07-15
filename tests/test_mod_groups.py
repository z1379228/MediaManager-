from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from core.localization import SUPPORTED_LOCALE_CODES
from core.mod_groups import (
    SITE_MOD_CHILDREN,
    BuiltinModGroupError,
    load_builtin_mod_group,
    load_builtin_mod_groups,
)
from tools.audit_mod_groups import audit_mod_groups


ROOT = Path(__file__).resolve().parents[1]
BUILTIN_ROOT = ROOT / "mod" / "builtin"


def test_site_groups_cover_exact_parent_child_and_four_locale_contract() -> None:
    for locale in SUPPORTED_LOCALE_CODES:
        groups = {group.group_id: group for group in load_builtin_mod_groups(locale)}
        assert set(groups) == set(SITE_MOD_CHILDREN)
        for parent_id, child_ids in SITE_MOD_CHILDREN.items():
            group = groups[parent_id]
            assert group.locale == locale
            assert group.parent_provider_id == parent_id
            assert tuple(module.provider_id for module in group.modules) == (
                parent_id,
                *child_ids,
            )
            assert group.workspace["title"]
            assert group.workspace["wrong_site"]


def test_ani_gamer_ui_strings_are_complete_in_all_four_mod_locales() -> None:
    groups = tuple(
        load_builtin_mod_group("ani-gamer", locale=locale)
        for locale in SUPPORTED_LOCALE_CODES
    )
    expected = set(groups[0].ui)

    assert "load_episodes" in expected
    assert "episodes_more" in expected
    assert all(set(group.ui) == expected for group in groups)


def test_site_group_rejects_incomplete_selected_translation(tmp_path: Path) -> None:
    builtin_root = tmp_path / "builtin"
    shutil.copytree(BUILTIN_ROOT / "youtube", builtin_root / "youtube")
    path = builtin_root / "youtube" / "locales" / "en.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["modules"].pop("youtube-player")
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(BuiltinModGroupError, match="coverage"):
        load_builtin_mod_group("youtube", locale="en", builtin_root=builtin_root)


def test_site_group_unknown_locale_falls_back_to_traditional_chinese() -> None:
    group = load_builtin_mod_group("bilibili", locale="fr")

    assert group.locale == "zh-TW"
    assert group.workspace["title"] == "Bilibili 下載工作區"


def test_current_site_provider_manifests_pass_cross_domain_audit() -> None:
    assert audit_mod_groups(ROOT) == ()
