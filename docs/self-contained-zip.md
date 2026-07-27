# GitHub 免安裝自包含 ZIP

本規格定義一個一般使用者可從 GitHub Releases 下載、解壓後直接雙擊
`MediaManager.exe` 啟動的 Windows x64 發行附件。使用者不需要另外安裝
Python；ZIP 內的 EXE、資產、內建 MOD 與必要 portable runtime 必須來自同一個
已稽核的 staged release。

目前已發布的附件是
[Testing `1.2.1` prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)，
來源為 Development `39.0.12` revision
`05442d7875da5367cd23babc2ce4e2e3e0cb87a2`，staged 目錄為
`Version/Testing/1.2.1`。遠端共有 9 個附件；既有 Testing `1.2.0` 保留於
`Version/Testing/1.2`，不得覆寫或改名。

## 使用者流程

1. 從指定的 GitHub Release 下載 `.zip` 與同名 `.zip.sha256`。
2. 使用 `Get-FileHash -Algorithm SHA256 <zip>` 比對 sidecar 中的雜湊。
3. 將 ZIP 解壓到新的空資料夾。
4. 進入唯一的 `MediaManager-<Track>-<X.Y.Z>/` 頂層資料夾。
5. 雙擊 `MediaManager.exe`。

Testing `1.2.1` ZIP 的已發布 SHA-256 是
`c633586d974fb77ba8041533cf7f7fd5378ab651d2b8f86126ccceb6b070f148`。
ZIP 必須包含且只包含 staged release 的受控檔案；不得只發布單獨 EXE，也不得
混入 `UserData`、快取、Log、下載內容、Cookie、憑證私鑰或其他本機狀態。

## 「自包含」與「資料可攜」的差異

本附件是免安裝、自包含的應用程式 ZIP：

- 雙擊 `MediaManager.exe` 可啟動，不需系統 Python。
- 應用程式所需的封裝資產與 release runtime 跟隨 ZIP。
- 雙擊時仍採標準 Windows 使用者資料位置：
  - 設定、資料、MOD 與信任資料位於 `%APPDATA%\MediaManager`。
  - 快取、暫存與 Log 位於 `%LOCALAPPDATA%\MediaManager`。
  - 下載預設位於使用者的 `Downloads\MediaManager`。

因此不同解壓副本會共用同一個 Windows 使用者 profile。這不等同於 `--portable`
資料模式；`--portable` 才會在 EXE 旁建立 `UserData/`。若未來要讓雙擊直接進入
資料可攜模式，必須另行變更啟動契約、資料遷移與測試，不能只改 ZIP 名稱。

## 發行者打包流程

下列工具只封裝既有 staged release，不會建置 EXE、簽署、stage、commit、push
或發布：

```powershell
$sourceRevision = "05442d7875da5367cd23babc2ce4e2e3e0cb87a2"
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.1 `
  --output-dir .work\release-upload-test-v1.2.1 `
  --expected-source-revision $sourceRevision
```

預設輸出名稱取自 `release-info.json`：

```text
MediaManager-Testing-1.2.1.zip
MediaManager-Testing-1.2.1.zip.sha256
```

若同一公開版本需要新的不可變 revision，使用安全且唯一的名稱；不可覆寫已公開
附件：

```powershell
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.1 `
  --output-dir .work\release-upload-test-v1.2.1-r2 `
  --expected-source-revision $sourceRevision `
  --revision r2
```

軌道與版本一律取自 `release-info.json`；`--revision` 只接受 `r1`、`r2` 等
不可冒用軌道或版本的後綴。`--expected-source-revision` 必須來自已授權
source-freeze、CI 的 immutable revision 或另一個獨立可信來源；不得先讀取
`release-info.json` 再原樣回填。工具會在寫入前後重新快照完整檔案集合並執行
版本完整性檢查，也要求 portable runtime policy 通過。ZIP 使用固定排序、
timestamp、權限與壓縮層級，輸出至同一支援原子 rename／hard link 的檔案系統，
驗證成員、內容與 CRC 後才以 no-overwrite 操作發布。checksum 先發布，ZIP 最後
發布，因此只有工具成功回傳且 ZIP 已出現時才表示附件 pair 完整；正常失敗會
清理該輪暫存與 sidecar。

既有輸出、重疊輸出目錄、link-like 項目、Windows 不相容或大小寫衝突路徑、
路徑逃逸、非一般檔案、使用者資料、已知高風險秘密檔名／格式，以及偵測到
private-key PEM marker 的檔案一律 fail closed。主要完整性邊界仍是 staged release
manifest 與兩次完整快照；檔名掃描只是額外防線。

## 驗證與發布 Gate

至少執行：

```powershell
$sourceRevision = "05442d7875da5367cd23babc2ce4e2e3e0cb87a2"
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_staged_runtime `
  --root Version\Testing\1.2.1
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.1 `
  --output-dir .work\package-check-a `
  --expected-source-revision $sourceRevision
.\.venv\Scripts\python.exe -m tools.package_self_contained_zip `
  --release-root Version\Testing\1.2.1 `
  --output-dir .work\package-check-b `
  --expected-source-revision $sourceRevision
Get-FileHash -Algorithm SHA256 `
  .work\package-check-a\MediaManager-Testing-1.2.1.zip
Get-FileHash -Algorithm SHA256 `
  .work\package-check-b\MediaManager-Testing-1.2.1.zip
```

在相同受控 Python／zlib runtime 下，兩次 ZIP 雜湊必須相同；跨不同壓縮函式庫
版本不宣稱 byte-for-byte 可重現。動態雙擊 GUI 仍需在解壓副本上人工執行並以
截圖記錄；靜態 ZIP 稽核不能代替實際 Windows 啟動、鍵盤、UIA、讀屏或高對比
驗證。

建立 EXE、建立 Testing／Stable staging、簽署、push、建立或修改 GitHub
Release、上傳與發布均是獨立 Gate，必須各自取得明確授權。未上傳的失敗輸出只
能移除該輪唯一 `.work` 目錄；已公開附件不得覆寫，修正時建立新 revision tag。

Testing `1.2.1` 的 source freeze、未簽署 EXE、ZIP／sidecar、tag
`test-v1.2.1` 與 GitHub prerelease 均已完成。遠端查核確認 9 個附件已上傳；
ZIP digest 與 sidecar 均為
`c633586d974fb77ba8041533cf7f7fd5378ab651d2b8f86126ccceb6b070f148`。
此附件維持未簽署 Testing 身分，不是 Stable。
