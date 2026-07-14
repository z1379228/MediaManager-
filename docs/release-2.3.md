# MediaManager 2.3.0

Version 2.3 adds the first optional local feature MOD, `media-convert`, without
adding noise or background work to the default UI.

## Media Convert MOD

- Ships disabled by default. Its workspace tab is created only after the user
  enables the MOD; no conversion worker exists until a job is submitted.
- Adds fixed, integrity-protected FFmpeg presets for stream-copy remux, timed
  split, same-format join, H.264/AAC conversion, H.265 compression, MP3/FLAC
  extraction and first-track SRT extraction.
- Shows strategy and bounded output-size estimates before confirmation.
- Supports an explicit NVIDIA H.264 attempt with automatic CPU fallback; GPU
  use is never required.
- Refuses symlink/non-file sources, invalid output extensions, source overwrite
  and existing targets. Successful output is linked from a same-folder `.part`
  file without replacement; failure or cancellation removes temporary files.
- Disabling the MOD cancels queued/running owned work and removes the optional
  tab.

## Validation

- Media Convert, feature registry, MOD controls, integrity and staging focus:
  `25 passed, 1 skipped` before the final persistence test was added.
- Ruff and complete source regression: `425 passed, 2 skipped`.
- The real local FFmpeg smoke generated a short WAV and completed an MP3 job;
  all six conversion-service tests passed.
- `Version/2.3` contains matching 2.3.0 EXE and wheel artifacts; all `34/34`
  hashes pass and the historical audit passes for 1.0 through 2.3.
- Copied-folder version, Portable verification and headless smoke all returned
  exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 32 protected files and retained no
  private key.

## Release state

This remains a `SAFE_MODE` development build. Media Convert uses the local
FFmpeg dependency and does not connect to a cloud conversion service.
