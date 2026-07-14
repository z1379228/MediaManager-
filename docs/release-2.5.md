# MediaManager 2.5.0

Version 2.5 completes the planned 1.9-to-2.5 run with optional automation that
remains quiet and disconnected by default.

## Automation MOD

- The MOD is disabled by default, and every newly created rule is independently
  disabled. Enabling the MOD alone creates no active rule and no network call.
- Adds bounded HTTPS URL/channel/playlist schedules, local watch folders and
  HTTPS-only clipboard intake. Clipboard access exists only while the optional
  Automation workspace is present and an enabled clipboard rule exists.
- Each rule records an action preset, interval, allowed daily run window, rate
  limit, visible next-run time, last run and last error.
- Scheduled/clipboard URLs can queue ordinary or bounded playlist downloads.
  Watch folders can submit Media Convert or Speech to Text work only when the
  corresponding MOD is also enabled.
- Uses a SQLite candidate ledger with deterministic unique keys. File identity
  includes normalized path, size and modification time; repeated clipboard URLs
  and schedule slots do not create duplicate rows.
- Missed schedule catch-up is capped by the rule rate limit. Interrupted
  `CLAIMED` rows recover to `PENDING`; target download/archive dedupe supplies a
  second idempotency boundary. Failures stay visible and require explicit retry.

## Validation

- Automation schedule/watch/clipboard, recovery, MOD UI, integrity and staging
  focus: `29 passed, 1 skipped`.
- Ruff and complete source regression after the FAT/exFAT-safe commit fix:
  `443 passed, 2 skipped`.
- `Version/2.5` contains matching 2.5.0 EXE and wheel artifacts; all `38/38`
  hashes pass and the historical audit passes for 1.0 through 2.5.
- Copied-folder version, Portable verification and headless smoke all returned
  exit code `0`. A separate offscreen GUI copy remained running without early
  exit; its PyInstaller child process and disposable copy were then removed.
  No staging residue or test process remains.
- The disposable signing drill verified all 36 protected files, detected
  tampering and retained no private key. No speech model is bundled.
- Formal preflight is blocked only by the intentionally absent production
  Ed25519 identity; the EXE is also correctly reported as `NotSigned`.

## Release state

This remains a `SAFE_MODE` development build. Production Ed25519 and Windows
Authenticode identities are still external release requirements; no security
check was weakened to reach 2.5.
