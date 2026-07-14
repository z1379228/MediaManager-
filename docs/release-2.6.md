# MediaManager 2.6.0

Version 2.6 expands the user-triggered similar-search result set and removes
bright Qt fallback surfaces without adding background recommendation work.

## Similar discovery

- The Similar action now returns a ranked, deduplicated list instead of one
  random item.
- Each related query remains bounded; the combined result is capped at 20 and
  always excludes the source video ID.
- Title, artist, language, category and local history signals remain
  explainable. Candidates returned by a related query are retained as labelled
  low-confidence fallbacks when localized titles share few tokens.
- The previous single-selection provider operation remains available for
  compatibility; no autoplay, infinite scroll or background fetching was
  introduced.

## Dark surface correction

- A global Fusion palette now covers popup lists, combo-box format choices,
  abstract scroll viewports, tables, tree/list views, spin controls, message
  boxes and Qt file dialogs.
- Native file dialogs are disabled when MediaManager creates the application,
  preventing an unstyled bright dialog from appearing beside the dark UI.
- External MOD pages receive named dark scroll and body containers while the
  default workspace remains uncluttered.

## Validation

- Ruff and complete source regression passed with `446 passed, 2 skipped`.
- `Version/2.6` contains matching 2.6.0 EXE and wheel artifacts with all 38
  checksum entries valid; the historical audit passed from 1.0 through 2.6.

## Release state

This remains a `SAFE_MODE` development build. Production Ed25519 and Windows
Authenticode identities are external release requirements; no security check
was weakened for the UI or discovery changes.
