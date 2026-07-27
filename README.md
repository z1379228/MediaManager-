# MediaManager v1.0

免費、無廣告、本機優先的媒體整理與模組化下載工作區。核心負責安全邊界、
佇列、媒體庫與可信 UI；網站解析、轉換、轉錄及自動化等重功能由可個別停用的
內建或第三方 MOD 提供。

目前來源版本為開發版 39.0（核心相容版本 39.0.12）。`MediaManager v1.0`
是產品顯示名稱，不表示 Stable 已發布。Testing `1.2.0` 已由 Development
`39.0.11` 建立本機歷史封存，但沒有 GitHub 發布，也不包含 39.0.12 相似音樂
入口。Testing `1.2.1` 已獲授權由 Development `39.0.12` 建立新的
`Version/Testing/1.2.1`、未簽署 EXE、自包含 ZIP 與 tag `test-v1.2.1` 並上傳
GitHub；在完整驗證與遠端查核完成前仍是待完成、未發布狀態。目前可下載的仍是
未簽署、維持 `SAFE_MODE` 的
[Testing 1.1（39.0.10 重整）](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.1.0-r2)
已發布供測試；它不是已簽署的 Stable 正式套件。

## 主要能力

- YouTube 公開搜尋、單一結果的相似音樂候選、Bilibili、MEGA、Direct HTTP
  與網站矩陣明列的獨立工作區。
- 本機媒體庫、原子寫入的下載佇列、歷史、取消、重試與恢復。
- 格式工廠：使用本機 FFmpeg 進行影片、音訊、影像與字幕處理。
- Gopeed Bridge／P2P Transfer：只連接使用者自行啟動的 localhost Gopeed API。
- 選用 Speech to Text 與 Automation；未安裝不影響核心。
- schema v2 第三方 MOD、Ed25519 發布者簽章、最小權限、受控程序與宣告式 UI。

實際能力以 MOD 管理、[依賴檢查](docs/dependency-health.md)與
[網站主機清冊](docs/site-host-inventory.md)為準。外部工具名稱不表示 MediaManager
會自動安裝、捆綁或承諾其全部功能。

## 安裝

### 方法一：目前已發布的 Testing 1.1 免安裝、自包含 ZIP（一般使用者）

Testing `1.2.1` 的預定附件名稱是 `MediaManager-Testing-1.2.1.zip` 與
`MediaManager-Testing-1.2.1.zip.sha256`，但尚未完成上傳驗證，因此目前不要
使用推測的 1.2.1 下載網址。發布完成前請使用下列既有 Testing 1.1 附件。

1. 從 [Testing 1.1 Release](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.1.0-r2)
   下載
   [`MediaManager-Testing-1.1.0-r2.zip`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.1.0-r2/MediaManager-Testing-1.1.0-r2.zip)
   及
   [`MediaManager-Testing-1.1.0-r2.zip.sha256`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.1.0-r2/MediaManager-Testing-1.1.0-r2.zip.sha256)。
2. 將兩個檔案放在同一資料夾，於該資料夾開啟 PowerShell 並核對雜湊：

   ```powershell
   Get-FileHash -Algorithm SHA256 .\MediaManager-Testing-1.1.0-r2.zip
   Get-Content .\MediaManager-Testing-1.1.0-r2.zip.sha256
   ```

   兩者的 SHA-256 必須相同；目前發布值為
   `31a1ab2c61ada07bc07eb8121107e8bbc7a16692347cae54af5fc5edb7dcf912`。
3. 將 ZIP 解壓縮到新的空資料夾，進入含有 `MediaManager.exe` 的資料夾後執行
   `MediaManager.exe`。不需要另外安裝 Python。

Testing 1.1 是未簽署測試版，Windows 可能顯示無法驗證發布者的警告。只應從上述
GitHub Release 下載並在雜湊一致時執行；不要關閉 Windows 安全功能。自包含 ZIP
已包含目前封裝的執行檔、資產與可攜工具，建議優先使用 ZIP，而不是單獨下載
`MediaManager.exe`。發行附件不包含 `UserData`；直接雙擊 EXE 時使用標準 Windows
使用者資料位置，不等同於 `--portable` 資料模式。詳見
[GitHub 免安裝自包含 ZIP](docs/self-contained-zip.md)。

### 方法二：從原始碼安裝

必要條件為 Windows 10／11 x64、Git 與 Python 3.14 以上。在 PowerShell 執行：

```powershell
git clone https://github.com/z1379228/MediaManager-.git
Set-Location .\MediaManager-
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[ui]"
.\.venv\Scripts\python.exe -B .\main.py --verify-only
.\.venv\Scripts\python.exe .\main.py
```

若要執行測試與開發工具，將安裝命令改為
`.\.venv\Scripts\python.exe -m pip install -e ".[ui,dev]"`。`--verify-only`
只驗證核心完整性；啟動 UI 後可從主畫面的核心／選用 MOD 工具狀態按鈕開啟
「執行環境」，再按「重新檢查」確認外部工具。

`main.py` 是唯一正式入口；`desktop.py` 只保留為舊版相容轉接。可攜模式會把
使用者資料放在程式旁的 `UserData/`。更完整的更新、移除與排錯說明見
[INSTALL.md](INSTALL.md)及[依賴檢查](docs/dependency-health.md)。

## 安全邊界

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站存取限制。
- Cookie、Token、私鑰、production 憑證與個人資料不得寫入 Repository 或 Log。
- URL、檔案、MOD manifest、IPC 與外部程序輸出一律視為不可信。
- 新安裝或更新的第三方 MOD 預設停用；發布者信任與使用者啟用是兩個獨立決定。
- 宣告式 MOD UI 不執行外部 HTML、Qt 物件或任意腳本。
- Development、Testing 與 Stable 的身分、雜湊、簽章及發布 Gate 不可互相冒用。

第三方 MOD 作者請從 [MOD-DEVELOPMENT.md](MOD-DEVELOPMENT.md) 開始。安全與
發行細節見 [MOD 套件契約](docs/mod-package-v1.md)及
[簽章流程](docs/release-signing.md)。

## Repository 結構

- `core/`：安全、下載、設定、儲存、媒體庫與 MOD 生命週期。
- `trusted_ui/`：PySide6 可信 UI。
- `contracts/`：核心與 MOD 共用的版本化資料契約。
- `mod/builtin/`：可個別啟用或停用的內建 MOD。
- `plugin_host/`：外部可執行 MOD 的受控程序入口。
- `tests/`、`tools/`：回歸測試、品質、版本與發行工具。
- `docs/`：目前有效的規格、狀態與維護文件。
- `Version/`：不可覆寫的 Development／Testing／Stable 產物。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m tools.quality_audit
.\.venv\Scripts\python.exe -m tools.run_tests
.\.venv\Scripts\python.exe -m tools.audit_mod_groups --root .
.\.venv\Scripts\python.exe -m tools.site_quality_audit --root .
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_version_docs
.\.venv\Scripts\python.exe -B .\main.py --verify-only
git diff --check
```

Repository 測試應透過 `tools.run_tests` 使用 Repository 外的每輪唯一暫存目錄；
不得讓 raw pytest 回退到 Repository 根目錄。

## 文件

- [文件索引](docs/README.md)
- [目前專案狀態](docs/project-status.md)
- [Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)
- [下載工作契約](docs/downloads-v1.md)
- [第三方 MOD 開發指南](docs/mod-developer-guide.md)
- [版本與發布政策](docs/version-layout.md)
- [GitHub 免安裝自包含 ZIP](docs/self-contained-zip.md)

舊 roadmap、過期候選與逐版日誌不再留在目前樹；需要稽核時由 Git 歷史與
GitHub Releases 的不可變附件追查。已公開的 EXE、checksum、release metadata
與 tag 不得刪除或覆寫。

## License

[MIT](LICENSE)
