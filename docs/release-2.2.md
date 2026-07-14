# MediaManager 2.2.0

Version 2.2 turns the lightweight local scan page into a persistent, offline
media library while preserving the clean default workspace.

## Local library

- Adds a SQLite index for scan roots, availability, local titles and artists,
  tags, play counts, last-played time, artwork references and playlists.
- Never rewrites media-file tags. Files on a temporarily unavailable path keep
  their local metadata and are only marked offline.
- Bounds scans to 50,000 supported regular files by default and does not follow
  directory or file symlinks.
- Adds an on-demand duplicate review using size plus bounded first/last-chunk
  fingerprints. It only reports groups and never deletes files.
- Adds bounded local artwork copies with atomic writes and oldest-first cache
  eviction.

## Playlists and file operations

- Adds static and smart local playlists plus bounded M3U/M3U8 and versioned JSON
  import/export. Import previews missing and duplicate entries before applying.
- Adds same-volume move/rename previews, preserves the extension, refuses
  overwrites, revalidates the source and rolls the file back if the database
  update fails.
- Keeps secondary actions inside a compact Manage menu so the default page
  remains scan/search focused.

## Validation

- Library core/UI focus suite: `19 passed, 1 skipped`.
- Ruff and complete source regression: `419 passed, 2 skipped`.
- `Version/2.2` contains matching 2.2.0 EXE and wheel artifacts; all `32/32`
  hashes pass and the historical audit passes for 1.0 through 2.2.
- Copied-folder version, Portable verification and headless smoke all returned
  exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 30 protected files and retained no
  private key.

## Release state

This remains a `SAFE_MODE` development build. The local library requires no
network service and the project still has no production Ed25519 or Authenticode
signing identity.
