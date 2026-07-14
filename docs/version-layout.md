# Versioned release folders

> 下列原有 `Version/<major>.<minor>` 路徑描述適用於 5.0 既有產物。雙軌版本
> 遷移完成後，新產物使用 `Version/Development` 與 `Version/Stable`；歷史資料
> 不原地改名，以免破壞已發布雜湊。

## 雙軌發布政策

| 通道 | 顯示範例 | 主要用途 | 預設發布內容 |
| --- | --- | --- | --- |
| Development | 開發版 5.0、開發版 6.0 | 新功能、MOD 適配與回饋測試 | `X.0` 完整上傳；`X.1` 至 `X.9` 只提供更新簡介 |
| Stable | 正式版 1.0、正式版 1.1 | 一般使用者與長期支援 | 通過候選評估且取得使用者確認後才包裝及上傳 |

雙軌目錄目標：

```text
Version/
├─ Development/
│  ├─ 5.0/
│  └─ 6.0/
└─ Stable/
   ├─ 1.0/
   └─ 1.1/
```

`product_version`、`development_generation` 與 `release_channel` 必須分開保存。
更新檢查只能在同一通道內比較版本；UI 與問題回報必須同時顯示通道及版本。

開發版若達到正式版條件，流程只能先輸出候選評估，列出功能範圍、測試、升級
與回退結果、已知問題、簽章狀態及建議正式版號。未取得使用者明確同意前，
不得產生 Stable EXE、簽章或 GitHub Release。

Legacy MediaManager releases remain under `Version/<major>.<minor>`. New builds
live under `Version/Development/<major>.<minor>` or
`Version/Stable/<major>.<minor>` according to their explicit release channel.
The folder name is derived from `CORE_VERSION`: `1.0.0` becomes `1.0`,
`1.1.0` becomes `1.1`, and so on.

`core/version.py` and `pyproject.toml` must contain the same version. The build
command fails before packaging when they differ or when `--version` attempts to
override that configured value; this prevents `release-info.json` and wheel
metadata from describing different releases.

Patch releases share the same local folder (`4.0.1` still stages to
`Version/4.0`) because local storage keeps only the current patch for that minor
line. A published GitHub tag or attachment is immutable: publishing `v4.0.1`
must create a new Release and must never replace the existing `v4.0.0` assets.

Build and stage the current version with:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version
```

The default Windows build requires pinned, verified portable Deno and FFmpeg
runtimes. Fetch them once into the ignored local tool cache with:

```powershell
.\.venv\Scripts\python.exe -m tools.portable_runtime
```

The downloads and extracted executables are checked against fixed SHA-256 values.
Successful builds copy Deno, FFmpeg, ffprobe, and their license notices into
`Version/<version>/tools`.
Use `--without-portable-runtime` only for a deliberately reduced build.

Temporary PyInstaller and wheel output stays under `.work/<major>.<minor>` and is
removed after a successful build. Use `--keep-work` only when build diagnostics are needed.
Each version folder contains the EXE, wheel, portable tools, built-in MOD files,
`release-info.json`, and `SHA256SUMS.txt`. Re-staging the same version uses a
transactional staging directory and removes stale files from the older staged
copy. Build caches are not included.

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
`Version/<major>.<minor>` folder. Portable mode writes `UserData` beside the
executable and makes the staged folder fail its checksum inventory. Copy the
complete folder under `.work/smoke-<version>`, test that copy, verify no process
remains and then remove only that smoke directory. `--version` and
`--verify-only` may be used for read-only historical checks, followed by another
`tools.audit_versions` run.

Formal signing and preflight use the staged folder as their root:

```powershell
.\.venv\Scripts\python.exe -m tools.sign_release --root Version\1.0 --private-key <external-key-path>
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\1.0
```
