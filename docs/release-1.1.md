# MediaManager 1.1

MediaManager 1.1 is the first UI-stabilization update after the functional 1.0
download milestone.

## User-visible changes

- YouTube discovery MOD switches are grouped into one compact menu while each
  MOD remains independently enabled or disabled.
- The discovery menu reports active and available MOD counts.
- Download, search and local-library pages share one consistent empty state.
- Search result actions stay disabled until a result is selected.
- Download actions follow the selected task state: retry, cancel and recovery
  are offered only when applicable.
- Download-table selection is retained across periodic progress refreshes.
- Custom backgrounds remain visible through high-opacity translucent workspace
  surfaces while preserving text contrast.
- The external MOD entry is named explicitly, and plugin management includes a
  read-only status page for all six bundled MODs with their control locations.
- YouTube search results show bounded 96x54 thumbnails from an HTTPS host
  allowlist and offer an explicit selected-item 30-second audio preview.

## Maintenance changes

- Shared empty-state presentation replaces duplicated panel markup and styling.
- Compatible plugin-package tests use the current core version instead of a
  hard-coded upper bound, reducing future version-bump maintenance.
- UI action-state behavior has a dedicated offscreen Qt regression test.
- Background decoding rejects malformed or excessive-resolution images, and
  scaled backgrounds are cached to avoid repeated work during repainting.
- Search artwork uses a 1 MB response limit and a 40-item memory cache. Audio
  previews use isolated temporary sessions and are removed on replacement or
  panel close.

## Verification

- Full regression: 187 passed, 1 skipped.
- Release checksum manifest: 21 of 21 files verified.
- Packaged `--version`, `--verify-only` and GUI startup smoke checks passed.

The artifact remains a SAFE_MODE development release until the compiled
Ed25519 release key identity is configured and the formal release manifest is
signed.
