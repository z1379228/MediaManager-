# Release signing

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

## 10.0 metadata anchors

Stable 簽章檔案集合由 `stable_signed_files()` 產生，除執行期檔案外也包含版本相符的
wheel、`release-info.json` 與 `SHA256SUMS.txt`。因此公開下載附件的套件、來源／建置
識別及最終 checksum 清單都必須由同一份 Ed25519 manifest 覆蓋；manifest 與簽章本身
則是 stage 後唯一允許新增的配對檔案。

## Current tooling status

`tools.build_version` currently builds and stages in one operation, before an
operator can apply Authenticode to the work-directory EXE. Therefore the old
single-command stable procedure is not approved for release. A tested release
operator or sign-before-stage hook must be completed before Stable 1.0 packaging.

The signing tool refuses a private key that does not match the compiled public
key. Never commit, bundle, log, or transmit the private key through MediaManager.
Unsigned development builds intentionally start in `SAFE_MODE`.
