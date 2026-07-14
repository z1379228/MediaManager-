# MediaManager 2.7.0

Version 2.7 closes the requested production run with bounded UI performance and
an accessibility baseline. No new background or advertisement surface is added.

## Performance bounds

- The download table computes a compact visible-state signature. An unchanged
  queue now returns without rebuilding rows or re-reading selected-task detail.
- Queue UI polling is reduced from 350 ms to 750 ms while changed task progress
  still refreshes automatically.
- Thumbnail loading remains capped at 1 MiB per response, 16 million decoded
  source pixels, 40 cached thumbnails and 32 concurrent pending URLs. Decode
  dimensions remain bounded at 384 x 216 before 96 x 54 display scaling.
- A clean bootstrap test confirms that registered website/discovery providers
  own no subprocess until the user submits an operation. Convert, transcription
  and automation MODs remain disabled by default.

## Accessibility and minimum layout

- Search input, result limit/type, search result table, URL input, format and
  subtitle selectors, download queue, external MOD selector and MOD content
  receive stable accessible names or descriptions.
- `Ctrl+F` focuses YouTube search; existing workspace and MOD shortcuts remain.
- The application palette text/base contrast exceeds 7:1, and core panels are
  exercised at the 940 x 620 window's 916-pixel content width without a
  horizontal download-workspace scrollbar.
- External MOD scroll surfaces are explicitly tested against the dark palette.

## Validation

- Ruff and the complete source regression pass with `452 passed, 2 skipped`;
  the skips are Windows symlink privilege cases.
- `Version/2.7` contains matching 2.7.0 EXE and wheel artifacts; all 38 checksum
  entries pass and the historical audit passes from 1.0 through 2.7.
- A copied-folder smoke test returns exit code `0` for version, Portable verify
  and Portable headless modes. The GUI remains alive after five seconds, all
  test processes are then stopped, and the disposable copy is removed.
- The disposable Ed25519 drill verifies 36 protected files, detects tampering
  and retains no key. Formal preflight is blocked only by the intentionally
  absent production Ed25519 identity; Authenticode remains external.

## Release state

This remains a `SAFE_MODE` development build. Production Ed25519 and Windows
Authenticode identities are external release requirements. Development stops at
2.7 as requested; later roadmap stages are not started.
