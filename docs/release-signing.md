# Release signing

## Distribution policy

Development builds are local engineering artifacts. Their complete files stay
in the local `Version/Development/<version>` folder and are not uploaded to
GitHub Releases. Public uploads are limited to verified `Testing/<version>`
artifacts and their release notes. A Development build may be packaged for
local validation, but it must not be presented as a downloadable release.

MediaManager enters `NORMAL` only when `security/release-manifest.json` has a
valid Ed25519 signature in `security/release-manifest.sig`, the manifest key id
matches the identity compiled into `core/security/release_key.py`, and every
listed SHA-256 digest matches.

## Required order

1. Generate and retain an Ed25519 private key outside the repository and build
   workspace.
2. Put only its Base64 raw public key and stable key id in `release_key.py`.
   A key change requires a new build.
3. Build `MediaManager.exe` in an isolated work directory.
4. Apply Windows Authenticode to that work-directory EXE and verify its status is
   `Valid`.
5. Stage the already Authenticode-signed EXE, wheel, portable runtimes and release
   files. Generate the final `release-info.json`, SBOM and `SHA256SUMS.txt` there.
6. Run `tools.sign_release` against the final staged directory so the Ed25519
   manifest records the final EXE bytes.
7. Run release preflight, version audit, copied-folder smoke and candidate evidence
   validation. Every gate must refer to the same staged artifact.
8. Distribute the staged directory without modifying any signed or hashed file.

Authenticode changes PE bytes. Applying it after `SHA256SUMS.txt` or the Ed25519
manifest has been generated invalidates those records and is forbidden.

## How to provide the production identity safely

Only the following public values may be supplied to Codex or committed to this
repository:

```text
key_id: <stable identifier>
public_key_base64: <Base64 encoding of the raw 32-byte Ed25519 public key>
```

The key id must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. The public value must
decode to exactly 32 bytes. These values are not secrets, but changing either
one changes the compiled trust identity and therefore requires a new source
revision, validation and source freeze.

Keep the Ed25519 private key in an operator-controlled path outside the
repository, `.work`, `Version`, build directories and synced chat attachments.
Do not paste the private key, its raw seed, a certificate private key, password,
PIN, token or recovery material into a Codex task, command history, log or
versioned file. When the final staged directory exists, the operator supplies
that local path directly to `tools.sign_release`:

```powershell
.\.venv\Scripts\python.exe -m tools.sign_release `
  --root Version\Stable\1.0 `
  --private-key <absolute-private-key-path-outside-repository>
```

Authenticode credentials are handled separately. After `build-only`, sign the
exact `.work\Stable\1.0-attempt-*\MediaManager.exe` with the organization-approved
external signing tool or service. Do not give Codex the certificate private key,
PIN or service token. Return only the work-directory path and non-secret status
evidence; MediaManager independently requires this command to report `Valid`:

```powershell
Get-AuthenticodeSignature -LiteralPath `
  <receipt-work-directory>\MediaManager.exe | Select-Object Status, StatusMessage
```

If no production Ed25519 identity or trusted Authenticode signing identity exists,
stop before `build-only`. A disposable key, self-signed certificate, copied
signature or relaxed preflight cannot be used for Stable.

## Metadata anchors

Stable 簽章檔案集合由 `stable_signed_files()` 產生，除執行期檔案外也包含版本相符的
wheel、`release-info.json` 與 `SHA256SUMS.txt`。因此公開下載附件的套件、來源／建置
識別及最終 checksum 清單都必須由同一份 Ed25519 manifest 覆蓋；manifest 與簽章本身
則是 stage 後唯一允許新增的配對檔案。

## Current tooling status

Development 39.0.6 provides the tested split-phase Stable operator. The old
single-command Stable procedure remains prohibited. After stage／commit／source
freeze and build authorization, create only the receipt-bound handoff:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version `
  --channel stable --confirm-stable --build-only
```

The returned `.work/Stable/1.0-attempt-*` directory contains the exact EXE,
wheel and `build-receipt.json`. Apply Authenticode to that EXE with the external
production identity and independently verify `Valid`. Only then stage it:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version `
  --channel stable --confirm-stable `
  --stage-built <receipt-work-directory>
```

Stage-built rejects a different release track, invalid attempt directory,
mismatched clean source revision, changed receipt/wheel, or Authenticode status
other than `Valid`. The receipt is an operator handoff, not a production trust
anchor; the final staged set still requires production Ed25519 signing, checksum,
SBOM, copied-folder verification and `release_preflight ready=true`.

The signing tool refuses a private key that does not match the compiled public
key. Never commit, bundle, log, or transmit the private key through MediaManager.
Unsigned development builds intentionally start in `SAFE_MODE`.
