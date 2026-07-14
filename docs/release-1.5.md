# MediaManager 1.5.0

Version 1.5 begins bounded multi-site downloading without expanding the clean
default workspace into one page per website.

## Generic yt-dlp Beta MOD

- Adds a disabled-by-default `generic-ytdlp` provider for explicit Vimeo,
  Dailymotion, SoundCloud, TikTok, Twitch and X/Twitter hosts.
- Uses a checked-in site matrix tied to the installed yt-dlp extractor set.
- Uses the separate `network.generic` permission and rejects URL credentials or
  malformed ports before starting the isolated process.
- Reuses the shared analyze, playlist, format, subtitle, segment, batch import,
  queue and archive contracts.
- YouTube keeps routing to its dedicated provider. Bilibili remains reserved
  for the danmaku-capable provider, while Facebook, Instagram and Threads stay
  separate feasibility candidates.

## UI and resource behavior

- The download workspace is transport-neutral and exposes one small
  **其他網站 Beta** switch beside the existing YouTube switch.
- Disabling a provider cancels only tasks routed to that provider; it no longer
  cancels unrelated site tasks.
- The generic provider starts lazily, performs no background work while
  disabled and contributes no additional default workspace page.

## Release state

This remains a development artifact in `SAFE_MODE` until a release Ed25519
identity, signed release manifest and Authenticode signature are supplied.

## Validation

- Ruff and Python bytecode compilation completed successfully.
- Full regression: `277 passed, 1 skipped`.
- Release checksum: all `26/26` listed files match, with no missing or
  unlisted files.
- Runtime dependencies: `4/4 Ready` (`yt-dlp 2026.7.4`, `yt-dlp-ejs 0.8.0`,
  `FFmpeg 8.1.2` and `Deno 2.9.2`).
- Copied-folder smoke test: portable `--verify-only` and `--headless` both
  returned exit code `0`, with no process left running.
- Release preflight checked all 24 protected files and remains intentionally
  blocked only because the compiled release Ed25519 identity is not valid;
  the executable is also `NotSigned`.
