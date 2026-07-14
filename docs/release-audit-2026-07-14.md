# Historical release audit — 2026-07-14

## Scope and result

The retained `Version/1.0` through `Version/1.8` folders were checked for
release metadata, folder/version alignment, wheel metadata, portable tools,
SHA-256 inventory coverage, file tampering, historical executable version
output, integrity-only startup and Authenticode state.

| Folder | Core | Verified hashes | EXE version | Verify-only | Authenticode |
| --- | --- | ---: | --- | --- | --- |
| 1.0 | 1.0.0 | 21 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.1 | 1.1.0 | 21 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.2 | 1.2.2 | 23 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.3 | 1.3.3 | 23 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.4 | 1.4.3 | 23 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.5 | 1.5.0 | 26 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.6 | 1.6.0 | 28 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.7 | 1.7.4 | 29 | Pass | SAFE_MODE, exit 0 | NotSigned |
| 1.8 | 1.8.1 | 29 | Pass | SAFE_MODE, exit 0 | NotSigned |

All nine folders pass the final batch audit. There are 223 verified manifest
entries in total, no mismatches, no missing files, no unlisted files and no
remaining MediaManager process.

After selected download-task diagnostics were added, the complete source
regression passed with `366 passed, 1 skipped`. The copied 1.8.1 folder
also passed `--version`, portable `--verify-only` and portable `--headless`
with exit code 0 and no remaining process.

## Corrected defect

`Version/1.0`, `Version/1.1` and `Version/1.2` contained unlisted `UserData`
trees. Their timestamps matched the original smoke runs and their only files
were two SAFE_MODE/plugin-start audit records, an empty application log and the
newly initialized empty MOD registry/WAL files. Downloads, settings and cache
were empty and no plugin was enabled.

The three test-only trees were removed after an allowlist check. The cause was
running an early portable headless smoke test directly from the retained
version folder. Later copied-folder tests did not have this defect.

## Preventive changes

- `python -m tools.audit_versions --root Version` now performs the complete
  read-only history audit in one command and returns a failing exit code for
  drift, tampering, unsafe paths or interrupted staging residue.
- Unit tests cover clean history, tampering, unlisted files, metadata drift,
  path traversal, interrupted staging and incomplete signing output.
- Version-layout documentation now requires portable GUI/headless smoke tests
  to run only from a disposable copied folder.
- A release manifest and signature are accepted as post-stage files only when
  both are present; `release_preflight` remains the cryptographic authority.

## Remaining risks and optimization order

### 2.5 continuation audit

The same read-only audit was rerun after every retained minor line through
`Version/2.5`. The final run passed all 16 folders from 1.0 through 2.5;
`Version/2.5` verified 38 checksum entries, copied-folder `--version`, Portable
`--verify-only` and Portable `--headless` all returned exit code 0, and there
was no staging/backup residue. The disposable signing drill covered all 36
required release files, detected tampering and retained no private key.

The final 2.5 source regression, including the FAT/exFAT-safe no-overwrite
commit helper, passed with `443 passed, 2 skipped`. Formal preflight remains blocked
only by the missing production Ed25519 identity, and Authenticode remains
`NotSigned`. These are release-identity requirements, not runtime regressions.

### 2.6 and 2.7 completion audit

The 2.6 discovery/UI correction passed Ruff and `446 passed, 2 skipped`, then
staged 38 verified files in `Version/2.6`. The 2.7 performance/accessibility
baseline passed Ruff and `452 passed, 2 skipped`, then staged 38 verified files
in `Version/2.7`. The final history audit passed all 18 folders from 1.0 through
2.7 with no staging or backup residue.

The final 2.7 copied-folder smoke returned exit code 0 for `--version`, Portable
`--verify-only` and Portable `--headless`; the GUI remained alive after five
seconds. Its one-file parent/child processes were stopped and the disposable
copy was removed. The signing drill verified 36 files, detected tampering and
retained no private key. Formal preflight remains blocked only by the absent
production Ed25519 identity; the EXE remains intentionally unsigned.

1. **Release identity:** every retained EXE is a development artifact. A valid
   compiled Ed25519 identity, signed release manifest and Authenticode signing
   remain required before any public release.
2. **Source history:** the repository is still on `master` with no commit and
   all project files untracked. Establishing an intentional baseline commit is
   the highest maintenance priority once the user authorizes Git publication.
3. **Live site support:** generic sites and Bilibili have offline contract tests
   but still require repeatable public-content live smoke matrices before Beta
   labels can be removed.
4. **Optional sites:** policy or authorization feasibility must precede adding
   any extractor to a download provider. An extractor existing in yt-dlp is not
   sufficient evidence by itself.
5. **Documentation:** 1.0 has no standalone historical release note. The staged
   artifact is internally consistent, so this is a documentation gap rather
   than a runtime defect.
