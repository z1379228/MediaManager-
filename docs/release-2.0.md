# MediaManager 2.0.0

Version 2.0 establishes the trusted modular update foundation without claiming
that a Windows Job Object is a complete security sandbox.

## MOD trust boundary

- Adds strict manifest v2 runtime, protocol and optional UI descriptor fields.
- Keeps schema-v1 data-only packages compatible; legacy executable packages
  can remain installed but cannot be enabled until repackaged.
- Binds approved capability tokens to the MOD identity, host PID, expiry and
  nonce before runtime initialization.
- Revalidates installed signatures, hashes, publisher trust, declared files and
  approved capability subsets whenever a MOD is enabled.
- The application Bootstrap disables all third-party Python execution until a
  genuine OS-level isolation implementation exists. Data-only packages do not
  start a process.

## Offline updates

- Adds `.mmupdate` packages signed with the external release Ed25519 identity.
- Validates source-version range, target version folder, archive structure,
  signature, every file SHA-256 and decompression limits before extraction.
- Installs into `Version/<major>.<minor>` with staging and rollback; the running
  version is never replaced in place.
- The UI disables the install action when the development build has no compiled
  production release key.

## Validation

- MOD lifecycle, capability, update and UI focus suite: `56 passed`.
- Ruff and the complete source regression: `401 passed, 1 skipped`.
- `Version/2.0` contains matching 2.0.0 EXE and wheel artifacts; all `31/31`
  listed hashes pass, and the historical audit passes for 1.0 through 2.0.
- Copied-folder `--version`, Portable `--verify-only` and Portable `--headless`
  all returned exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 29 protected files, detected the
  intentional tamper and retained no private key.

## Release state

This is a `SAFE_MODE` development build. No production private key is present,
and external executable MODs remain disabled. Public trusted distribution still
requires externally managed Ed25519 release signing and Windows Authenticode.
