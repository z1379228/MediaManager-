# MediaManager v1.0

免費、無廣告、本機優先的媒體整理與模組化下載工作區。核心負責安全邊界、
佇列、媒體庫與可信 UI；網站解析、轉換、轉錄及自動化等重功能由可個別停用的
內建或第三方 MOD 提供。

目前來源版本為開發版 39.0（核心相容版本 39.0.10）。`MediaManager v1.0`
是產品顯示名稱，不表示 Stable 已發布。Repository 目前沒有可供一般使用者下載的
已簽署正式套件；本輪只授權由固定的 39.0.10 來源建立本機、未簽署且維持
`SAFE_MODE` 的 Testing 1.1，不包含簽署、push 或發布。

## 主要能力

- YouTube、Bilibili、MEGA、Direct HTTP 與網站矩陣明列的獨立工作區。
- 本機媒體庫、原子寫入的下載佇列、歷史、取消、重試與恢復。
- 格式工廠：使用本機 FFmpeg 進行影片、音訊、影像與字幕處理。
- Gopeed Bridge／P2P Transfer：只連接使用者自行啟動的 localhost Gopeed API。
- 選用 Speech to Text 與 Automation；未安裝不影響核心。
- schema v2 第三方 MOD、Ed25519 發布者簽章、最小權限、受控程序與宣告式 UI。

實際能力以 MOD 管理、[依賴檢查](docs/dependency-health.md)與
[網站主機清冊](docs/site-host-inventory.md)為準。外部工具名稱不表示 MediaManager
會自動安裝、捆綁或承諾其全部功能。

## 從原始碼執行

目前只提供原始碼工作流程。完整步驟見 [INSTALL.md](INSTALL.md)；最短啟動方式：

```powershell
.\.venv\Scripts\python.exe .\main.py
```

`main.py` 是唯一正式入口；`desktop.py` 只保留為舊版相容轉接。可攜模式會把
使用者資料放在程式旁的 `UserData/`，請勿在保留版 `Version/` 目錄內直接執行
會寫入資料的 smoke test。

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
- [最新來源更新](docs/latest-update.md)
- [下載工作契約](docs/downloads-v1.md)
- [第三方 MOD 開發指南](docs/mod-developer-guide.md)
- [版本與發布政策](docs/version-layout.md)

舊 roadmap、過期候選與逐版日誌不再留在目前樹；需要稽核時由 Git 歷史與
GitHub Releases 的不可變附件追查。已公開的 EXE、checksum、release metadata
與 tag 不得刪除或覆寫。

## License

[MIT](LICENSE)
