# MediaManager 2.1.0

Version 2.1 adds verified public-analysis coverage without treating extractor
presence as proof that every account, region or download format works.

## Multi-site behavior

- Adds stable `UNSUPPORTED`, `LOGIN_REQUIRED`, `REGION_RESTRICTED`,
  `CONTENT_REMOVED`, `RATE_LIMITED`, `TEMPORARY` and `PROVIDER_ERROR` results.
- Records bounded public analysis for YouTube, Vimeo, Dailymotion, SoundCloud,
  TikTok, Twitch, X and Bilibili. Generic site families remain Beta and
  disabled by default.
- Keeps Meta sites and AniGamer outside automated download access.

## Bilibili

- Distinguishes ordinary, multipart and bangumi results and reports bounded
  subtitle language availability.
- Normalizes flat multipart IDs and URLs into unique selectable entries.
- Preserves the existing subtitle, danmaku XML, ASS conversion and optional MKV
  stream-copy workflow; cookie import and restriction bypass remain forbidden.
- Adds a checked-in Bilibili feature matrix protected by built-in hashes and
  release preflight.

## Validation

- Provider, Bilibili and integrity focus suite: `66 passed, 1 skipped`.
- Eight-site public analysis matrix: all cases `PASS` on 2026-07-14.
- Ruff and the complete source regression: `412 passed, 1 skipped`.
- `Version/2.1` contains matching 2.1.0 EXE and wheel artifacts; all `32/32`
  hashes pass and the historical audit passes for 1.0 through 2.1.
- Copied-folder version, Portable verification and headless smoke all returned
  exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 30 protected files and retained no
  private key.

## Release state

This remains a `SAFE_MODE` development build without production Ed25519 or
Authenticode signing. Public analysis PASS does not authorize login, payment,
region, DRM or membership bypass.
