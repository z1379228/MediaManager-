"""Files that must be present in a complete MediaManager release."""

from core.downloads.builtin_integrity import BUILTIN_PROVIDER_HASHES

SOURCE_RELEASE_FILES = (
    "MediaManager.exe",
    "LICENSE",
    "安裝必備軟體.bat",
    "requirements-lock.txt",
    "assets/app-icon.ico",
    "trusted_ui/assets/app-icon.png",
    "mod/builtin/automation/feature.json",
    "mod/builtin/automation/policy.json",
    "mod/builtin/media-convert/feature.json",
    "mod/builtin/media-convert/presets.json",
    "mod/builtin/speech-to-text/adapter.json",
    "mod/builtin/speech-to-text/feature.json",
    "mod/builtin/bilibili/danmaku_ass.py",
    "mod/builtin/bilibili/group.json",
    "mod/builtin/bilibili/locales/en.json",
    "mod/builtin/bilibili/locales/ja.json",
    "mod/builtin/bilibili/locales/zh-CN.json",
    "mod/builtin/bilibili/locales/zh-TW.json",
    "mod/builtin/bilibili/provider.py",
    "mod/builtin/bilibili/provider.json",
    "mod/builtin/bilibili/site-matrix.json",
    "mod/builtin/bilibili-search/provider.py",
    "mod/builtin/bilibili-search/provider.json",
    "mod/builtin/bilibili-danmaku/feature.json",
    "mod/builtin/ani-gamer/feature.json",
    "mod/builtin/ani-gamer/group.json",
    "mod/builtin/ani-gamer/locales/en.json",
    "mod/builtin/ani-gamer/locales/ja.json",
    "mod/builtin/ani-gamer/locales/zh-CN.json",
    "mod/builtin/ani-gamer/locales/zh-TW.json",
    "mod/builtin/ani-gamer-search/provider.py",
    "mod/builtin/ani-gamer-search/provider.json",
    "mod/builtin/ani-gamer-episodes/provider.py",
    "mod/builtin/ani-gamer-episodes/provider.json",
    "mod/builtin/generic-ytdlp/provider.py",
    "mod/builtin/generic-ytdlp/provider.json",
    "mod/builtin/generic-ytdlp/site-matrix.json",
    "mod/builtin/facebook/provider.py",
    "mod/builtin/facebook/provider.json",
    "mod/builtin/facebook/group.json",
    "mod/builtin/facebook/locales/en.json",
    "mod/builtin/facebook/locales/ja.json",
    "mod/builtin/facebook/locales/zh-CN.json",
    "mod/builtin/facebook/locales/zh-TW.json",
    "mod/builtin/mega/provider.py",
    "mod/builtin/mega/provider.json",
    "mod/builtin/mega/group.json",
    "mod/builtin/mega/locales/en.json",
    "mod/builtin/mega/locales/ja.json",
    "mod/builtin/mega/locales/zh-CN.json",
    "mod/builtin/mega/locales/zh-TW.json",
    "mod/builtin/youtube/provider.py",
    "mod/builtin/youtube/provider.json",
    "mod/builtin/youtube/site-matrix.json",
    "mod/builtin/youtube/group.json",
    "mod/builtin/youtube/locales/en.json",
    "mod/builtin/youtube/locales/ja.json",
    "mod/builtin/youtube/locales/zh-CN.json",
    "mod/builtin/youtube/locales/zh-TW.json",
    "mod/builtin/youtube-search/provider.py",
    "mod/builtin/youtube-search/provider.json",
    "mod/builtin/youtube-player/provider.py",
    "mod/builtin/youtube-player/provider.json",
    "mod/builtin/youtube-history/provider.py",
    "mod/builtin/youtube-history/provider.json",
    "mod/builtin/youtube-recovery/provider.py",
    "mod/builtin/youtube-recovery/provider.json",
    "mod/builtin/youtube-similar/provider.py",
    "mod/builtin/youtube-similar/provider.json",
    "mod/builtin/youtube-auto-split/provider.py",
    "mod/builtin/youtube-auto-split/provider.json",
)

# The integrity pins are the authoritative list of built-in MOD payloads. Keep
# the historical explicit entries above stable, then append every newer pinned
# file automatically so packaging cannot silently omit a newly registered MOD.
PINNED_BUILTIN_RELEASE_FILES = tuple(
    f"mod/builtin/{provider_id}/{relative_path}"
    for provider_id, files in BUILTIN_PROVIDER_HASHES.items()
    for relative_path in files
)
SOURCE_RELEASE_FILES += tuple(
    path for path in PINNED_BUILTIN_RELEASE_FILES if path not in SOURCE_RELEASE_FILES
)

GENERATED_RELEASE_FILES = (
    "dependency-inventory.json",
    "sbom.cdx.json",
)

PORTABLE_RUNTIME_FILES = (
    "tools/deno.exe",
    "tools/DENO-LICENSE.md",
    "tools/ffmpeg.exe",
    "tools/ffprobe.exe",
    "tools/FFMPEG-LICENSE.txt",
    "tools/FFMPEG-README.txt",
)

DEFAULT_RELEASE_FILES = (
    SOURCE_RELEASE_FILES + PORTABLE_RUNTIME_FILES + GENERATED_RELEASE_FILES
)


def stable_signed_files(version: str) -> tuple[str, ...]:
    """Anchor metadata, wheel and checksum manifest in a Stable signature."""

    return DEFAULT_RELEASE_FILES + (
        f"mediamanager-{version}-py3-none-any.whl",
        "release-info.json",
        "SHA256SUMS.txt",
    )
