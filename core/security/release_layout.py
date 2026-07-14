"""Files that must be present in a complete MediaManager release."""

SOURCE_RELEASE_FILES = (
    "MediaManager.exe",
    "assets/app-icon.ico",
    "trusted_ui/assets/app-icon.png",
    "mod/builtin/automation/feature.json",
    "mod/builtin/automation/policy.json",
    "mod/builtin/media-convert/feature.json",
    "mod/builtin/media-convert/presets.json",
    "mod/builtin/speech-to-text/adapter.json",
    "mod/builtin/speech-to-text/feature.json",
    "mod/builtin/bilibili/danmaku_ass.py",
    "mod/builtin/bilibili/provider.py",
    "mod/builtin/bilibili/provider.json",
    "mod/builtin/bilibili/site-matrix.json",
    "mod/builtin/generic-ytdlp/provider.py",
    "mod/builtin/generic-ytdlp/provider.json",
    "mod/builtin/generic-ytdlp/site-matrix.json",
    "mod/builtin/youtube/provider.py",
    "mod/builtin/youtube/provider.json",
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

PORTABLE_RUNTIME_FILES = (
    "tools/deno.exe",
    "tools/DENO-LICENSE.md",
    "tools/ffmpeg.exe",
    "tools/ffprobe.exe",
    "tools/FFMPEG-LICENSE.txt",
    "tools/FFMPEG-README.txt",
)

DEFAULT_RELEASE_FILES = SOURCE_RELEASE_FILES + PORTABLE_RUNTIME_FILES
