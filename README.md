# MediaManager v1.0

MediaManager 是免費、無廣告、Windows 優先且本機運作的模組化媒體管理工具，
整合 YouTube、YouTube Music、Bilibili、MEGA、Direct HTTP 與本機媒體庫。
核心負責下載佇列、媒體整理、安全邊界與可信 UI；網站解析、格式轉換、語音
轉文字及自動化等功能由可個別停用的內建或第三方 MOD 提供。

MediaManager 只處理使用者有權存取的公開內容，不繞過 DRM、登入、Cookie、
Cloudflare、廣告、付費、地區或其他網站限制。

## 目前狀態

- 目前來源版本為開發版 39.0（核心相容版本 39.0.96）。
- 最新公開下載是未簽署的
  [Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)，
  對應 Development `39.0.39`。
- Development `39.0.40`～`39.0.96` 的修改尚未包含在公開 Testing ZIP。
- Testing `1.2.3` 目前只是本機候選，未上傳或發布。
- 尚未發布已簽署的 Stable 套件；`MediaManager v1.0` 是產品顯示名稱，不代表
  Stable 已發布。

### 最近來源變更

- `39.0.96`：移除第三方 MOD 驗證訊息中的硬編碼 `core 3.0`，並讓 GitHub
  Quality workflow 統一使用具 60 秒逾時及隔離暫存目錄的專案測試 runner。
- `39.0.95`：啟動時直接顯示主畫面，不再自動彈出首次 MOD 設定或依賴環境
  視窗；相關功能仍可由主畫面的按鈕手動開啟。
- `39.0.94`：強化 H.265 Main10 NVENC／Opus Passthru MKV preset 的輸出契約
  驗證與失敗清理。
- `39.0.90`～`39.0.93`：新增影像浮水印、YouTube Music 搜尋路徑與下載後
  本機轉換 preset。
- `39.0.13`～`39.0.89`：改善多來源搜尋、分頁、去重、Unicode 比對、相似音樂
  排序、失敗隔離及第三方 Search v2 MOD 契約。

完整技術紀錄請見
[Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)。

## 快速下載與啟動

1. 從 [Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
   下載
   [`MediaManager-Testing-1.2.2.zip`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip)
   與
   [`MediaManager-Testing-1.2.2.zip.sha256`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip.sha256)。
2. 將兩個檔案放在同一資料夾，使用 PowerShell 核對 SHA-256：

   ```powershell
   Get-FileHash -Algorithm SHA256 .\MediaManager-Testing-1.2.2.zip
   Get-Content .\MediaManager-Testing-1.2.2.zip.sha256
   ```

3. 確認兩者雜湊相同後，將 ZIP 解壓縮至新的空資料夾。
4. 進入含有 `MediaManager.exe` 的資料夾並雙擊啟動，不需要另外安裝 Python。

Testing 1.2.2 是未簽署測試版，Windows 可能顯示無法驗證發布者的警告。請只從
上述 GitHub Release 下載並核對雜湊，不要關閉 Windows 安全功能。建議下載完整
ZIP，不要單獨下載 EXE；ZIP 不包含任何使用者資料。

一般雙擊啟動會使用 `%APPDATA%\MediaManager`、`%LOCALAPPDATA%\MediaManager`
與 `Downloads\MediaManager`，不等同於 `--portable` 資料模式。詳見
[免安裝自包含 ZIP 說明](docs/self-contained-zip.md)。

## 主要能力

- YouTube／YouTube Music 公開搜尋、批次工作與相似音樂候選。
- Bilibili、MEGA、Direct HTTP 及網站矩陣中明列的獨立工作區。
- 本機媒體庫、原子寫入下載佇列、歷史、取消、重試與恢復。
- 格式工廠：使用本機 FFmpeg 處理影片、音訊、影像、字幕、切割、串接、壓縮、
  固定位置影像浮水印及 H.265 Main10 NVENC／Opus Passthru MKV。
- Gopeed Bridge／P2P Transfer：只連接使用者自行啟動的 localhost Gopeed API。
- 選用 Speech to Text 與 Automation；未安裝不影響核心功能。
- schema v2 第三方 MOD、Ed25519 發布者簽章、最小權限、受控程序及宣告式 UI。

實際可用能力以程式內的 MOD 管理、
[依賴檢查](docs/dependency-health.md)與
[網站主機清冊](docs/site-host-inventory.md)為準。外部工具名稱不表示
MediaManager 會自動安裝、捆綁或承諾其全部功能。

## 從原始碼執行

必要條件：

- Windows 10／11 x64。
- Python 3.14 以上。
- Git。

在 PowerShell 執行：

```powershell
git clone https://github.com/z1379228/MediaManager-.git
Set-Location .\MediaManager-
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[ui]"
.\.venv\Scripts\python.exe -B .\main.py --verify-only
.\.venv\Scripts\python.exe .\main.py
```

開發者若需要測試工具，將安裝命令改為：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,dev]"
```

`main.py` 是正式入口；`desktop.py` 僅為舊版相容轉接。`--verify-only` 只驗證
核心完整性。啟動 UI 後，可點擊主畫面的核心／選用 MOD 工具狀態按鈕開啟
「執行環境」，再按「重新檢查」確認 yt-dlp、FFmpeg、JavaScript runtime 等
外部工具。程式只顯示缺少項目，不會未經確認自動安裝。

完整的更新、移除及排錯流程請見 [INSTALL.md](INSTALL.md)。

## 安全與資料界線

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站存取限制。
- Cookie、Token、私鑰、production 憑證及個人資料不得寫入 Repository 或 Log。
- URL、檔案、MOD manifest、IPC 與外部程序輸出一律視為不可信。
- 新安裝或更新的第三方 MOD 預設停用；信任發布者與啟用 MOD 是兩個獨立決定。
- 宣告式 MOD UI 不執行外部 HTML、Qt 物件或任意腳本。
- Development、Testing 與 Stable 的身分、雜湊、簽章及發布 Gate 不可互相冒用。

第三方 MOD 作者請從 [MOD-DEVELOPMENT.md](MOD-DEVELOPMENT.md) 開始，並參考
[第三方 MOD 開發指南](docs/mod-developer-guide.md)、
[MOD 套件契約](docs/mod-package-v1.md)與
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

Repository 測試應使用 `tools.run_tests` 的 Repository 外隔離暫存目錄；不得讓
raw pytest 回退到 Repository 根目錄。

## 文件

- [文件索引](docs/README.md)
- [安裝與啟動](INSTALL.md)
- [目前專案狀態](docs/project-status.md)
- [Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)
- [下載工作契約](docs/downloads-v1.md)
- [第三方 MOD 開發指南](docs/mod-developer-guide.md)
- [版本與發布政策](docs/version-layout.md)
- [免安裝自包含 ZIP](docs/self-contained-zip.md)

舊 roadmap、過期候選與逐版重複日誌不保留在目前文件索引；需要稽核時，應由
Git 歷史及 GitHub Releases 的不可變附件追查。已公開的 EXE、checksum、release
metadata 與 tag 不得刪除或覆寫。

## License

[MIT](LICENSE)
