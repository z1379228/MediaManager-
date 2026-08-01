# GitHub 免安裝自包含 ZIP

本規格定義一般使用者從 GitHub Releases 下載、解壓後直接執行
`MediaManager.exe` 的 Windows x64 附件。ZIP 內的 EXE、資產、內建 MOD 與必要
portable runtime 必須全部來自同一個已稽核 staged release。

目前新候選是 Testing `1.2.2`，由 Development `39.0.39` 的乾淨 source freeze
建立於 `Version/Testing/1.2.2`，並使用唯一 tag `test-v1.2.2`。既有
[Testing `1.2.1` prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
及 `Version/Testing/1.2`、`Version/Testing/1.2.1` 保持不可變。

## 使用者流程

1. 從指定 GitHub prerelease 下載 `.zip` 與同名 `.zip.sha256`。
2. 使用 `Get-FileHash -Algorithm SHA256 <zip>` 比對 sidecar。
3. 將 ZIP 解壓到新的空資料夾。
4. 進入唯一頂層 `MediaManager-Testing-1.2.2/`。
5. 執行 `MediaManager.exe`。

Testing 1.2.2 的最終 SHA-256 只在本輪 sidecar、staged manifest 與 GitHub asset
digest 閉合後記錄；不得沿用 Testing 1.2.1 的雜湊。ZIP 必須完整包含 staged
release，且不得混入 UserData、下載內容、cache、log、Cookie、憑證或私鑰。

## 自包含不等於資料可攜

- EXE 可以單獨啟動，不依賴系統 Python。
- 程式所需的封裝資產與 release runtime 跟隨 ZIP。
- 一般雙擊仍使用標準 Windows 使用者位置：
  - 設定、媒體庫、MOD 與信任資料：`%APPDATA%\MediaManager`
  - cache、暫存與 log：`%LOCALAPPDATA%\MediaManager`
  - 預設下載：`Downloads\MediaManager`

因此本附件不是 `--portable` 資料模式；`--portable` 會在執行根目錄旁建立
`UserData/`。若要支援整個資料狀態搬移，必須另訂資料遷移契約與測試。

## 發行者封裝

封裝工具不會 build、簽署、stage、commit、push 或發布：

```powershell
$sourceRevision = "<已獨立確認的 39.0.39 source-freeze revision>"
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.2 `
  --output-dir .work\release-upload-test-v1.2.2 `
  --expected-source-revision $sourceRevision
```

預設輸出：

```text
MediaManager-Testing-1.2.2.zip
MediaManager-Testing-1.2.2.zip.sha256
```

公開附件不可覆寫。若同版本在公開前需要另一個可追蹤包裝嘗試，可使用新的空輸出
目錄與受限的 `--revision r2`；公開後的 material 修正必須增加 Testing patch。

`--expected-source-revision` 必須由 source-freeze commit、CI immutable revision
或另一個獨立可信來源取得，不能只從 `release-info.json` 自我抄寫。工具會在封裝
前後重新執行版本、runtime 與檔案快照稽核；輸出目錄、路徑逃逸、link-like、
大小寫衝突、UserData、secret marker、私鑰 PEM marker 或既有同名輸出都會 fail closed。

## 驗證 Gate

```powershell
$sourceRevision = "<已獨立確認的 39.0.39 source-freeze revision>"
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_staged_runtime `
  --root Version\Testing\1.2.2
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.2 `
  --output-dir .work\package-check-test-v1.2.2-a `
  --expected-source-revision $sourceRevision
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.2 `
  --output-dir .work\package-check-test-v1.2.2-b `
  --expected-source-revision $sourceRevision
Get-FileHash -Algorithm SHA256 `
  .work\package-check-test-v1.2.2-a\MediaManager-Testing-1.2.2.zip
Get-FileHash -Algorithm SHA256 `
  .work\package-check-test-v1.2.2-b\MediaManager-Testing-1.2.2.zip
```

同一 Python／zlib runtime 下兩次 ZIP 必須相同。另需完成 staged runtime audit、
current／previous／current copied-folder smoke、ZIP 展開驗證、release inventory、
GitHub tag／prerelease／附件數與遠端 digest 回讀。

截圖只能證明可見版面，不能取代真實 Windows 啟動、鍵盤、UIA／讀屏、高對比或
外部網站人工驗證。Testing 1.2.2 維持未簽署 `SAFE_MODE`，不是 Stable；本流程
不會關閉 Windows 安全功能，也不會覆寫 Testing 1.2.1。
