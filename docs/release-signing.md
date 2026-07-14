# Release signing

MediaManager enters `NORMAL` only when `security/release-manifest.json` has a
valid Ed25519 signature in `security/release-manifest.sig`, the manifest key id
matches the identity compiled into `core/security/release_key.py`, and every
listed SHA-256 digest matches.

Release procedure:

1. Generate and retain an Ed25519 private key outside the repository and build
   system workspace.
2. Put only its Base64 raw public key and stable key id in `release_key.py`.
3. Run `python -m tools.build_version --channel stable --version 1.0.0 --confirm-stable`.
   A key change therefore requires a new build.
4. Run `python -m tools.sign_release --root Version/Stable/1.0 --private-key <external-key-path>`.
5. Apply Windows Authenticode to `Version/Stable/1.0/MediaManager.exe` with the
   production code-signing identity.
6. Run `python -m tools.release_preflight --root Version/Stable/1.0`. It must print `READY`.
7. Distribute the EXE, `mod/builtin` files, and `security` manifest/signature
   together.

The signing tool refuses a private key that does not match the compiled public
key. Never commit, bundle, log, or transmit the private key through MediaManager.
Unsigned development builds intentionally start in `SAFE_MODE`.
