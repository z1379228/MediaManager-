# Versioned release folders

> 下列原有 `Version/<major>.<minor>` 路徑描述適用於 5.0 既有產物。分軌版本
> 遷移完成後，新產物使用 `Version/Development`、`Version/Testing` 與
> `Version/Stable`；歷史資料
> 不原地改名，以免破壞已發布雜湊。

## 三軌發布政策

| 通道 | 顯示範例 | 主要用途 | 預設發布內容 |
| --- | --- | --- | --- |
| Development | 開發版 5.0、開發版 6.0 | 新功能、MOD 適配與回饋測試 | `X.0` 完整上傳；`X.1` 至 `X.9` 只提供更新簡介 |
| Testing | 測試版 1.0、測試版 1.1 | 將已驗證開發功能交給使用者測試 | GitHub Pre-release；未簽署並維持 `SAFE_MODE` |
| Stable | 正式版 1.0、正式版 1.1 | 一般使用者與長期支援 | 通過候選評估且取得使用者確認後才包裝及上傳 |

三軌目錄目標：

```text
Version/
├─ Development/
│  └─ 11.0/
├─ Testing/
│  └─ 1.0/
└─ Stable/
   └─ 1.0/
```

`product_version`、`development_generation` 與 `release_channel` 必須分開保存。
更新檢查只能在同一通道內比較版本；UI 與問題回報必須同時顯示通道及版本。

開發版若達到正式版條件，流程只能先輸出候選評估，列出功能範圍、測試、升級
與回退結果、已知問題、簽章狀態及建議正式版號。未取得使用者明確同意前，
不得產生 Stable EXE、簽章或 GitHub Release。

Legacy MediaManager releases remain under `Version/<major>.<minor>`. New builds
live under `Version/Development`, `Version/Testing` or `Version/Stable` according
to their explicit release channel. Release-info schema v3 separates
`core_version` from `release_version`: testing release 1.0.0 may retain core
compatibility version 11.0.0, while its folder remains `Testing/1.0`.

`core/version.py` and `pyproject.toml` must contain the same version. The build
command fails before packaging when they differ or when `--version` attempts to
override that configured value; this prevents `release-info.json` and wheel
metadata from describing different releases.

Development source identity and the UI use the full `X.Y.Z` version. `X.Y.0` is
the first source baseline for that feature line; every subsequent material code
fix increments `Z` (`38.1.0` -> `38.1.1` -> `38.1.2` -> `38.1.3` -> `38.1.4` -> `38.1.5` -> `38.1.6` -> `38.1.7` -> `38.1.8` -> `38.1.9` -> `38.1.10` -> `38.1.11` -> `38.1.12` -> `38.1.13` -> `38.1.14` -> `38.1.15` -> `38.1.16`). Documentation, screenshot,
or evidence-only updates do not increment the correction number.

For the retired 38.1 integration line, `38.1.14` is
`SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`; `38.1.15` records the
AniGamer removal. `38.1.16` is the final 38.x source-only identity with
`SOURCE VALIDATED / PACKAGING INPUT HARDENED / NO PACKAGE / SAFE_MODE`.
G38-02 is `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`.
G39-01 is complete as `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`.
Development `39.0.5` is the current source identity for G39-07. It retains the
G39-04 localhost-only Gopeed／P2P runtime MODs, optional Speech to Text runtime
dependencies, additive format-workshop presets, and new-profile built-in defaults,
removes the unsupported Gopeed `rawUrl` request field, and adds a minimum-size
scroll contract to prevent the Transfer workspace from collapsing at limited
window heights. It also fixes Stable's independent public identity at `1.0.0`
and provides a receipt-bound build-only／stage-built operator so Authenticode is
validated before staging. It remains
`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`; G40-01 remains
`WAITING / AUTHORIZATION + STAGED VERIFY/HEADLESS SAFE_MODE EVIDENCE REQUIRED`.
G38-01 retains its independent manual-validation blockers.
The 38.1.8 increment records a material catalog-state correction: a
structured failure with no accepted item retains the last usable results,
selection, and episodes, while partial success and a genuinely empty successful
response keep their prior semantics. The 38.1.9 increment records a separate
episode-response ownership correction: after the user changes the selected
series, an older asynchronous success or failure response is discarded instead
of being applied to the new series. The 38.1.10 increment then requires the raw
AniGamer series or episode query to be exactly `sn=<ASCII digits>`, rejecting
extra, duplicate, case-aliased, and percent-encoded forms before provider,
handoff, history, or offline consumers. The 38.1.11 increment adds the shared
canonical item identity invariant: series IDs must equal `ani-{sn}`, episode
IDs must equal `ani-episode-{sn}`; history and offline metadata enforce the same
identity on both write and read; and stale episode row handoffs fail closed while
the workspace is busy or closing. Built-in providers already emit those IDs, and
current-series and direct-episode contexts keep their prior semantics. The
38.1.12 increment is a separate handoff-observability correction. All four
`episode_opened` locale messages receive the exact canonical `{url}`, and both
selected-episode and history-entry handoffs format the same URL that was offered
to the OS. The message says only that the OS accepted the open request; it does
not claim that the official page loaded or playback started. Existing 38.1.11
screenshots do not count as 38.1.12 live evidence because their success message
did not contain that URL. None of these corrections imports
browser state, retries invisibly, changes provider traffic, or bypasses
verification. Reverting 38.1.11 means reverting the identity validator,
consumer wiring, history/offline read checks, busy/closing guards, regressions,
version, and documentation
together; there is no data migration and it never overwrites the immutable Development
38.0 folder.
Reverting 38.1.12 means reverting the four locale strings, `{url}` handoff
wiring, regressions, version, and documentation together. It does not migrate
or delete data, change Cookie or stream handling, add download capability, or
overwrite the immutable Development 38.0 folder. No 38.1.12 stage, commit,
source freeze, build, package, or push has been performed.
The 38.1.13 increment corrects a separate compatibility-dialog observability
defect. The dialog previously used `catalog_opened` for every route, while an OS
rejection or opener `RuntimeError` updated only the main status hidden behind
the dialog. It now uses `episode_opened` for an exact episode route and includes
the exact canonical URL, uses `series_opened` for an exact series route, and
mirrors each success or failure message into dialog-local status. This does not
change provider, network, Cookie, download, or stream behavior. The focused
regression recorded RED `1 failed in 1.27s` and GREEN `1 passed in 0.71s`;
the related focused group passed `3` tests, the expanded non-GUI group passed
`115` with `1` skipped, and the version/documentation group passed `19` tests.
All remaining source gates passed; a 38.1.13 manual screenshot is still pending.
Reverting 38.1.13 means reverting the route-aware dialog messages,
dialog-local status mirroring, regression, version, and documentation together.
It does not migrate or delete data or overwrite the immutable Development 38.0
folder. No 38.1.13 stage, commit, source freeze, build, package, or push has
been performed.
The 38.1.14 increment corrects a Python argument-binding conflict in the
official handoff helper. Its transport positional parameter was named `url`,
while episode calls also supplied a message placeholder as keyword `url=`;
Python therefore raised a multiple-values `TypeError` before the helper body,
OS opener, or dialog-local status could run. Renaming only the transport
parameter and its internal references to `official_url` preserves the message
placeholder and all route, translation, and handoff semantics. This does not
change provider, network, Cookie, download, or stream behavior. The pre-fix
runtime group recorded `1 failed, 162 passed, 1 skipped in 8.99s`; the new
focused regression recorded RED `1 failed in 1.20s`, and the focused handoff
group recorded GREEN `4 passed in 1.08s`. A later related non-UI and version
group recorded `134 passed, 1 skipped, 1 failed in 6.79s` before the documents
were synchronized; that sole failure reported README and docs README still at
38.1.13. After synchronization, the same related non-GUI and version group
passed `135` tests with `1` skipped in `1.87s`; the remaining source gates also
passed. Source validation is complete, while the 38.1.14 manual screenshot
remains pending. Reverting 38.1.14 means reverting
the helper parameter and internal references, regression, version, and
documentation together. It does not migrate or delete data or overwrite the
immutable Development 38.0 folder. No 38.1.14 stage, commit, source freeze,
build, package, or push has been performed.

The 38.1.15 increment records the user-directed removal of the AniGamer MOD,
workspace, and runtime registration from current source. Existing user data,
historical evidence, and the immutable Development 38.0 package remain in
place; retired routes are not rewired to generic Direct HTTP. This source-only
change has no package. Rollback means restoring the complete validated 38.1.14
source and registrations together; it never deletes user data or overwrites a
retained Version folder.

The 38.1.16 increment replaces recursive PyInstaller collection of
`mod/builtin` with the exact integrity-pinned release inventory. This prevents
ignored bytecode and local tool caches from silently entering a new executable.
It does not delete those local files or modify the immutable Development 38.0
package. Rollback restores the helper, spec contract, regression, version, and
documentation together; no package was built for this source-only correction.

Development 39.0.0 is a new feature baseline rather than a 38.1 correction.
It extends the existing disabled-by-default Media Convert workspace with local
PNG, JPEG, and WebP still-image conversion and bounded redacted FFmpeg failure
evidence. Existing conversion IDs and output rules remain compatible. Reverting
39.0.0 removes the three additive presets and diagnostics while leaving user
source files and any already-created outputs untouched.

Development 39.0.1 adds local capability evidence, a 256 MiB conversion disk
reserve, and ffprobe stream validation before committing a temporary output.
It does not add a binary, cloud fallback, or new provider contract. Reverting
39.0.1 restores the 39.0.0 conversion service and UI while leaving source files,
UserData, and already-completed outputs untouched.

Development 39.0.2 adds the localhost-only Gopeed Bridge／P2P Transfer MODs,
marks whisper-cli and the speech model as optional Speech to Text runtime
dependencies, names the trusted conversion workspace `格式工廠`, and adds
WebM／AVI, AAC／Opus／WAV, and BMP／TIFF presets. On a new profile, every built-in
MOD except Automation and Speech to Text starts enabled; saved user choices are
preserved. Reverting 39.0.2 removes those additive registrations and restores
39.0.1 defaults without deleting Gopeed tasks, downloaded data, models,
UserData, source files, or completed conversion outputs.

Development 39.0.3 removes the unsupported `rawUrl` member from Gopeed create
and resolve request bodies so they conform to the official OpenAPI `Request`
schema. Reverting 39.0.3 restores only that request-shape implementation,
regression, version, and documentation; it does not delete external Gopeed
tasks, downloaded data, models, UserData, source files, or conversion outputs.

Development 39.0.4 wraps the trusted Gopeed／P2P workspace in the existing
`workspaceScroll` pattern and applies the content layout's minimum-size contract.
At limited heights the page scrolls vertically instead of collapsing its cards.
Reverting 39.0.4 restores the previous UI shell, regression, version, and
documentation; it does not delete tasks, downloads, UserData, or external Gopeed
configuration.

Development 39.0.5 maps Stable to its independent public identity `1.0.0` and
splits the formal release operator into receipt-bound build-only and stage-built
steps. The handoff binds channel, core/release versions, clean source revision,
and wheel SHA-256; Stable staging additionally requires Authenticode `Valid`.
Reverting 39.0.5 restores the previous identity/operator, regression, version,
and documentation; it does not delete UserData, retained versions, public assets,
or an unissued signing work directory.

Patch releases continue to share the same local minor folder (`4.0.1` stages to
`Version/Development/4.0`) for compatibility with retained releases and offline
update contracts. Only the latest patch selected before the first stage is
packaged for that minor line. Staging fails closed when the folder already
exists; it never overwrites an earlier candidate. A published GitHub tag or
attachment is also immutable: publishing `v4.0.1` must create a new Release and
must never replace the existing `v4.0.0` assets.

Build and stage the current version with:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version
```

Stable uses the split operator and may run only after the corresponding explicit
authorizations and production signing identities are available:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version `
  --channel stable --confirm-stable --build-only
# Apply and independently verify Authenticode on the exact work-directory EXE.
.\.venv\Scripts\python.exe -m tools.build_version `
  --channel stable --confirm-stable --stage-built <receipt-work-directory>
```

`--stage-built` rejects a different release track, source revision, receipt,
wheel digest, or non-`Valid` Authenticode status. These commands do not replace
the final Ed25519 manifest, SBOM/checksum, copied-folder, or preflight gates.

Windows 環境若因 Python／pip `TEMP`、`TMP` 暫存 ACL 出現 `WinError 5`，
可指定使用者可寫入的一次性建置暫存根目錄：

```powershell
.\.venv\Scripts\python.exe -m tools.build_version `
  --temp-root "$env:LOCALAPPDATA\MediaManager\build-temp"
```

The default Windows build requires pinned, verified portable Deno and FFmpeg
runtimes. Fetch them once into the ignored local tool cache with:

```powershell
.\.venv\Scripts\python.exe -m tools.portable_runtime
```

The downloads and extracted executables are checked against fixed SHA-256 values.
Successful builds copy Deno, FFmpeg, ffprobe, and their license notices into
`Version/<channel>/<version>/tools` for new three-channel builds.
Use `--without-portable-runtime` only for a deliberately reduced build.

Temporary PyInstaller and wheel output stays under `.work/<major>.<minor>` and is
removed after a successful build. Use `--keep-work` only when build diagnostics are needed.
Each version folder contains the EXE, wheel, portable tools, built-in MOD files,
`release-info.json`, and `SHA256SUMS.txt`. The transactional staging directory is
used only while creating or recovering the first staged copy; an existing
retained version folder is never replaced. Build caches are not included.

日常只稽核目前版與上一版：

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
```

大版本封版、資安事件或定期維護時，先從 GitHub Releases 還原需要的歷史版本，
再執行完整本機歷史稽核：

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version --full-history
```

The audit validates folder/version alignment, wheel metadata, portable tools,
safe checksum paths, every listed hash, missing files, unlisted files and
interrupted staging residue. A post-stage release manifest and signature are
accepted only when both are present; cryptographic release readiness remains
the responsibility of `tools.release_preflight`.

本機日常只保留 current + previous。更舊版本由 GitHub Releases 保存，公開的
EXE、`SHA256SUMS.txt` 與 `release-info.json` 不得刪除。次版本若依發行政策只
提供簡介，則不要求永久保存其本機大型封裝。

Never run portable GUI or headless smoke tests directly inside a retained
`Version/<channel>/<major>.<minor>` folder. Portable mode writes `UserData` beside the
executable and makes the staged folder fail its checksum inventory. Copy the
complete folder under `.work/smoke-<version>`, test that copy, verify no process
remains and then remove only that smoke directory. `--version` and
`--verify-only` may be used for read-only historical checks, followed by another
`tools.audit_versions` run.

Formal signing and preflight use the staged folder as their root:

```powershell
.\.venv\Scripts\python.exe -m tools.sign_release --root Version\Stable\1.0 --private-key <external-key-path>
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\Stable\1.0
```
