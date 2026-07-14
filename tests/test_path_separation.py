from __future__ import annotations

from pathlib import Path

from core.storage.paths import AppPaths


def test_legacy_mod_state_is_copied_without_builtins(tmp_path: Path) -> None:
    legacy = tmp_path / "mod"
    (legacy / "builtin" / "youtube").mkdir(parents=True)
    (legacy / "builtin" / "youtube" / "provider.py").write_text(
        "builtin", encoding="utf-8"
    )
    (legacy / "installed" / "example").mkdir(parents=True)
    (legacy / "installed" / "example" / "provider.py").write_text(
        "plugin", encoding="utf-8"
    )
    (legacy / "registry.sqlite3").write_bytes(b"registry")

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    migrated = paths.migrate_legacy_mod_state()

    assert migrated == ("registry.sqlite3", "installed")
    assert (paths.installed_plugins / "example" / "provider.py").is_file()
    assert paths.plugin_registry.read_bytes() == b"registry"
    assert not (paths.mod / "builtin").exists()


def test_legacy_portable_user_data_migrates_without_release_files(
    tmp_path: Path,
) -> None:
    for name in ("Data", "Downloads", "Settings"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "value.txt").write_text(name, encoding="utf-8")
    legacy_security = tmp_path / "Security"
    legacy_security.mkdir()
    (legacy_security / "trust-store.json").write_text("{}", encoding="utf-8")
    (legacy_security / "release-manifest.json").write_text(
        "must-not-migrate", encoding="utf-8"
    )

    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    migrated = paths.migrate_legacy_user_data()

    assert migrated == (
        "Data",
        "Downloads",
        "Settings",
        "Security/trust-store.json",
    )
    assert (paths.data / "value.txt").read_text("utf-8") == "Data"
    assert (paths.downloads / "value.txt").read_text("utf-8") == "Downloads"
    assert (paths.settings / "value.txt").read_text("utf-8") == "Settings"
    assert (paths.security / "trust-store.json").read_text("utf-8") == "{}"
    assert not (paths.security / "release-manifest.json").exists()


def test_legacy_migration_never_overwrites_new_state(tmp_path: Path) -> None:
    legacy = tmp_path / "mod"
    legacy.mkdir()
    (legacy / "provider-state.json").write_text("old", encoding="utf-8")
    paths = AppPaths.discover(portable=True, app_root=tmp_path)
    paths.mod.mkdir(parents=True)
    (paths.mod / "provider-state.json").write_text("new", encoding="utf-8")

    assert paths.migrate_legacy_mod_state() == ()
    assert (paths.mod / "provider-state.json").read_text("utf-8") == "new"
