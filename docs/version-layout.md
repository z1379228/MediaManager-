# 版本資料夾與三軌政策

Development、Testing 與 Stable 是互相獨立的發行軌道，不可用數字大小跨軌比較。

## 目錄

- `Version/Development/<major>.<minor>/`
- `Version/Testing/<major>.<minor>/`
- `Version/Stable/<major>.<minor>/`
- `Version/Testing/<major>.<minor>.<patch>/`
- `Version/Stable/<major>.<minor>.<patch>/`

5.0 以前的歷史產物可能位於 `Version/<major>.<minor>/`；它們是保留證據，
不為統一目錄而搬移或改寫。Testing／Stable 基線可以保留 `X.Y` 目錄，基線後的
material 修正版必須使用完整 `X.Y.Z`。Testing `1.2.0` 保留於
`Version/Testing/1.2`；公開的 Testing `1.2.1` 保留於
`Version/Testing/1.2.1`；本次新候選使用 `Version/Testing/1.2.2`。

每個候選資料夾包含 EXE、wheel、portable tools、內建 MOD、
`release-info.json`、`SHA256SUMS.txt`、dependency inventory 與 SBOM。
版本稽核會拒絕缺檔、checksum 不符、路徑逃逸、link-like 內容及 staging residue。

## 版本身分

- Development 使用完整 `X.Y.Z`；material 程式修正增加 `Z`。
- 純文件或未改變執行行為的證據更新不增加核心修正號。
- Testing 與 Stable 各自維護公開身分，不跟隨 Development 數字。
- Testing／Stable 基線後的 material 修正增加 patch，並同步目錄、tag、ZIP、
  sidecar 與 release metadata。
- UI 的產品名稱使用 `MediaManager v1.0`；真正信任狀態以 channel、checksum、
  簽章與 release metadata 為準。

## 不可變與保留

- 已公開的版本資料夾、tag、EXE、`SHA256SUMS.txt`、`release-info.json` 與附件
  不得覆寫、刪除或重新命名。
- 新候選綁定唯一 source revision；修正公開候選必須增加版本。
- 日常本機只保留 current＋previous；清理必須使用受控 dry-run，不刪除
  UserData、link-like 內容或無可驗證 manifest 的未知路徑。
- 完整歷史稽核先由 GitHub Releases 還原公開附件，再使用 `--full-history`。

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version --full-history
```

## 免安裝自包含 ZIP

一般使用者附件從通過版本與 runtime 稽核的 staged release 建立。ZIP 只有一個
頂層資料夾；解壓後可以直接執行 `MediaManager.exe`，不需要系統 Python，也不包含
UserData、下載內容、cache、log、Cookie、憑證或私鑰。

```powershell
$sourceRevision = "<已獨立確認的 39.0.39 source-freeze revision>"
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.2 `
  --output-dir .work\release-upload-test-v1.2.2 `
  --expected-source-revision $sourceRevision
```

工具只封裝已 staged folder，不會自行 build、簽署、stage、commit、push 或發布。
deterministic ZIP 與 GitHub revision gate 詳見
[GitHub 免安裝自包含 ZIP](self-contained-zip.md)。

## 建置與發布 Gate

stage、commit、source freeze、build、EXE、Testing／Stable、簽署、stage-built、
push、tag、Release 與附件上傳都是獨立受控操作。授權其中一項不自動授權其他項。

Testing `1.2.1` 是不可變的已公開歷史版本。Testing `1.2.2` 已獲授權由
Development `39.0.39` 的乾淨 source freeze 建立為未簽署 GitHub prerelease；
它不是 Stable。Stable 仍必須通過正式身分、簽章與人工驗證 Gate。

## 複製資料夾驗證

不要直接在 staged release 執行會寫入 UserData 的 GUI 或 headless smoke。
`tools.copied_folder_smoke` 會把 current 與 previous 複製到安全的 Repository 外
暫存根，執行 fail-closed 啟動與 rollback smoke，再只清理本次擁有的複本。
