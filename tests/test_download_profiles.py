from pathlib import Path

from trusted_ui.download_profiles import (
    DomainDownloadProfile,
    DownloadProfileStore,
)


def test_profile_store_round_trips_domain_options_atomically(tmp_path: Path) -> None:
    store = DownloadProfileStore(tmp_path / "settings" / "download-profiles.json")
    profile = DomainDownloadProfile(
        format_preset="video-1080",
        container_preset="mp4",
        subtitle_mode="selected",
        subtitle_languages=("zh-TW", "en"),
        priority=5,
        output_dir=str(tmp_path / "downloads"),
        embed_metadata=True,
        embed_thumbnail=True,
        embed_chapters=True,
        network_retry="resilient",
    )

    store.save("youtube", profile)

    assert store.load("youtube") == profile
    assert store.load("bilibili") is None
    assert not store.path.with_suffix(".tmp").exists()


def test_profile_store_fails_closed_for_invalid_or_foreign_documents(
    tmp_path: Path,
) -> None:
    path = tmp_path / "download-profiles.json"
    path.write_text(
        '{"schema": 1, "profiles": {"youtube": {"format_preset": "bad"}}}',
        encoding="utf-8",
    )
    store = DownloadProfileStore(path)

    assert store.load("youtube") is None

    path.write_text(
        '{"schema": 1, "profiles": {"foreign": {}}}', encoding="utf-8"
    )
    assert store.load("youtube") is None
