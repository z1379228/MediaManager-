# MediaManager

免費、無廣告、本機優先的媒體整理與模組化下載工作區。核心維持精簡；網站整合、
轉檔、轉錄及自動化能力由可個別停用的內建或外部 MOD 提供。

## 目前狀態

- 目前來源版本為開發版 39.0（核心相容版本 39.0.5）；G39-07 狀態為
  `SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。
- 正式版目標：Stable `1.0.0`，目前 `ready: false`；尚未建立、簽署、發布或上傳。
- 最新來源更新：
  - 格式工廠新增固定的影片、音訊、影像與字幕 preset，並加入 FFmpeg 能力、磁碟及
    成品驗證；所有處理只接受使用者選取的本機檔案。
  - Gopeed Bridge／P2P Transfer 只連接使用者自行啟動的 localhost Gopeed REST API；
    不自動啟動 Gopeed、不開放遠端連線、不自動開埠，也不強制刪除下載資料。
  - Speech to Text 的 `whisper-cli` 與語音模型保持選用；未安裝不影響核心功能。
  - Stable 發行操作已拆成 receipt-bound `build-only` 與 Authenticode 驗證後的
    `stage-built`，避免先產生 checksum 再修改 EXE。
- 最新非 UI 驗證：`1019 passed, 6 skipped`；封裝與版本精準回歸
  `45 passed`。Ruff、quality audit、MOD、網站、依賴鎖、版本文件、保留版本、
  Repository 外 compileall、SAFE_MODE verify-only 與 `git diff --check` 均已通過。
- 動畫瘋整合已於 Development 38.1.15 依範圍決定從目前來源及 runtime 註冊移除；
  舊 UserData、工程證據及不可變 Development 38.0 基線仍保留，且不會轉接到通用下載器。

完整 Gate、驗證證據與正式版阻擋請見：

- [`docs/roadmap-development-34.0-40.0.md`](docs/roadmap-development-34.0-40.0.md)
- [`docs/release-39.0-40.0.md`](docs/release-39.0-40.0.md)
- [`docs/release-stable-1.0-candidate.md`](docs/release-stable-1.0-candidate.md)

## 安全與範圍

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站限制。
- 不把 Cookie、Token、私鑰或 production 憑證寫入 Repository、設定索引或 Log。
- 外部 URL、檔案、MOD manifest、IPC 與程序輸出都視為不可信並套用大小、路徑及
  capability 邊界。
- 新安裝與更新後的外部 MOD 預設停用；宣告式 MOD UI 不執行任意 HTML、Qt 物件或腳本。
- 缺少正式 Ed25519／Authenticode 身分時維持 `SAFE_MODE`，不得將 Development 產物改名為
  Testing 或 Stable。

## 主要能力

- YouTube、Bilibili、MEGA、Direct HTTP 與已列入矩陣的官方工作區。
- 本機媒體庫、原子寫入的佇列／歷史／封存與可恢復工作狀態。
- 以 yt-dlp、FFmpeg／ffprobe、Deno 等受控外部工具提供解析、下載與本機媒體處理。
- 格式工廠：影片轉檔、音訊抽取、影像轉換、字幕抽取及使用者指定的本機片段修剪。
- Gopeed／P2P：明確操作、localhost-only、記憶體 Token 與非強制移除工作。
- 選用 Speech to Text 與 Automation；重功能可在 MOD 管理中個別啟用或停用。

實際支援能力以 MOD 管理、依賴檢查與網站矩陣為準；參考軟體或外部工具名稱不代表
MediaManager 自動安裝、捆綁或承諾相同功能。

## 執行

```powershell
.\.venv\Scripts\python.exe .\main.py
.\.venv\Scripts\python.exe .\main.py --portable --headless
.\.venv\Scripts\python.exe .\main.py --portable --verify-only
```

`main.py` 是唯一正式入口；安裝後的 `mediamanager` 指令與 PyInstaller 桌面程式使用相同的
參數解析、Bootstrap 與主視窗啟動流程。`desktop.py` 只保留為舊版相容轉接。

整個版本資料夾可移動執行；不要只移動 EXE，因為同層 MOD、工具、
`release-info.json` 與 checksum 都是版本的一部分。

## 路徑架構

- `main.py`：唯一正式入口。
- `core/`：安全、下載、轉檔、媒體庫、設定、儲存與 MOD 生命週期。
- `trusted_ui/`：PySide6 可信 UI。
- `contracts/`：核心與 MOD 共用的版本化資料契約。
- `mod/builtin/`：可個別啟用或停用的內建 MOD。
- `plugin_host/`：外部可執行 MOD 的受控程序入口。
- `tests/`、`tools/`：回歸測試、品質、版本與發行工具。
- `Version/Development`、`Version/Testing`、`Version/Stable`：彼此獨立且不可覆寫的發行軌。
- `UserData/`：本機使用者資料；不納入版本雜湊或自動清理。

## 驗證

Repository 測試應使用統一 runner，避免 pytest 因不可寫 TEMP／TMP 回退到 Repository：

```powershell
.\.venv\Scripts\python.exe -m tools.quality_audit
.\.venv\Scripts\python.exe -m tools.run_tests
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_version_docs
.\.venv\Scripts\python.exe -B .\main.py --verify-only
git diff --check
```

針對性測試範例：

```powershell
.\.venv\Scripts\python.exe -m tools.run_tests `
  --target tests/test_build_version.py
```

`tools.run_tests` 在 `%LOCALAPPDATA%\MediaManager-TestRuns` 建立每輪唯一暫存目錄；不得以
Repository 根目錄作 pytest basetemp，也不得用 broad `tmp*` ignore 隱藏未知內容。

## 打包與正式版

任何 stage、commit、source freeze、build、EXE、Testing／Stable、簽署、發布、上傳與 push
都必須分別取得明確授權。Stable 的必要順序為：

1. 完成並提交 exact source scope，建立不可變 source-freeze revision。
2. 使用 production Ed25519 public identity 建置 receipt-bound Stable 工作目錄。
3. 在外部安全環境對該工作目錄中的 EXE 套用 Authenticode，並確認狀態為 `Valid`。
4. 將同一 receipt、revision、wheel 與 EXE 交給 `stage-built` 建立不可覆寫候選。
5. 對 staged set 執行 production Ed25519 簽署、checksum、SBOM、preflight、copied-folder
   及 headless `SAFE_MODE`／`NORMAL` 驗證。
6. 所有證據指向同一 digest 後，才可發布 Stable 1.0.0。

操作細節請見 [`docs/release-signing.md`](docs/release-signing.md)；目前沒有正式套件，故不應執行
或散布候選命令的中間產物。

## 更新資訊與歷史保留

本首頁只列目前有效版本、最新更新與操作入口。完整歷史保留於
[`docs/README.md`](docs/README.md) 的唯讀索引及各區間 release／roadmap 文件。

GitHub Releases 上已公開的 EXE、`SHA256SUMS.txt`、`release-info.json` 與 tag 不得刪除、覆寫或
以新版本冒充。日常本機可依既有保留政策只留 current＋previous；需要完整歷史稽核時，先從
GitHub Releases 還原公開附件，再執行 `tools.audit_versions --full-history`。這能讓使用者只看到
最新更新資訊，同時保留可驗證的回退、雜湊及供應鏈證據。
