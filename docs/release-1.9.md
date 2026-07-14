# MediaManager 1.9.0

Version 1.9 completes the daily 1.x download workflow while preserving the
clean default UI, disabled-by-default site MODs and fail-closed release state.

## Queue control

- Adds a persisted `PAUSED` task state and per-task pause/resume control.
- Running work is paused through the provider's normal cancellation path;
  MediaManager does not freeze an operating-system process. Provider `.part`
  files remain available for yt-dlp continuation where the site supports it.
- Adds pause-all/resume-all actions and a persistent 1–4 worker selector.
- A paused task can still be explicitly cancelled, and restored paused tasks
  do not start until the user resumes them.

## Portable IDs

- Exports canonical download archive IDs without exposing original URLs.
- Validates file type, schema, fields, hashes, size and entry limits before an
  archive import; the UI shows new and duplicate counts before merging.
- Exports reviewed playlist entries to versioned JSON and imports them through
  the existing selection dialog before adding any download task.
- Uses atomic replacement for archive and playlist files and never deletes
  existing IDs during import.

## Release and provider diagnostics

- Adds a signing dry run that generates a disposable Ed25519 key in a temporary
  directory, verifies every copied release file, proves tamper detection, then
  destroys the key and copy.
- Adds an opt-in public-content provider matrix for YouTube, Vimeo through the
  generic provider, and Bilibili. Each case records its own PASS/FAIL result so
  one live-site failure does not hide the remaining evidence.
- Live reports stay under `.work` and are not treated as offline contract tests.

## Validation

- Ruff and the complete source suite pass: `389 passed, 1 skipped`.
- `Version/1.9` contains version-matched 1.9.0 EXE and wheel artifacts; all
  `31/31` listed SHA-256 hashes pass.
- Historical release audit passes for 1.0 through 1.9 across ten retained
  version folders.
- Copied-folder `--version`, Portable `--verify-only` and Portable `--headless`
  smoke processes all returned exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 29 protected files, detected the
  intentional tamper and retained no test private key.
- The opt-in public-content matrix passed on 2026-07-14 for YouTube, Vimeo via
  `generic-ytdlp`, and Bilibili; the JSON evidence remains under `.work`.
- Formal release preflight checked all 29 protected files and remains blocked
  only because no production Ed25519 release identity is compiled. Windows
  Authenticode reports `NotSigned`.

## Release state

This remains a usable development artifact in `SAFE_MODE`. No production key
is stored in the repository. A valid externally controlled Ed25519 release
identity and Authenticode signature are still required before a public build is
described as trusted or signed.
